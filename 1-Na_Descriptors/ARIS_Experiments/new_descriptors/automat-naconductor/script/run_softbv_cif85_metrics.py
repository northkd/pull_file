#!/usr/bin/env python3
"""Batch softBV/BVPA metrics for CIF files.

The script intentionally keeps every structure in its own working directory
because BVPA writes several fixed-name files such as BVPA_summary.txt.
"""

from __future__ import annotations

import argparse
import csv
import filecmp
import fnmatch
import hashlib
import math
import re
import shutil
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FLOAT_RE = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"

DEFAULT_OXIDATION_STATES = {
    "Na": 1,
    "Li": 1,
    "K": 1,
    "Mg": 2,
    "Ca": 2,
    "Sr": 2,
    "Zn": 2,
    "B": 3,
    "Al": 3,
    "Ga": 3,
    "In": 3,
    "Y": 3,
    "Er": 3,
    "As": 5,
    "Cr": 3,
    "Fe": 3,
    "Si": 4,
    "P": 5,
    "S": -2,
    "F": -1,
    "Cl": -1,
    "Br": -1,
    "I": -1,
    "Sc": 3,
    "Ti": 4,
    "Mn": 4,
    "Nb": 5,
    "Se": -2,
    "Ge": 4,
    "Zr": 4,
    "Hf": 4,
    "Ta": 5,
    "Sn": 4,
    "Sb": 5,
    "V": 3,
    "W": 6,
    "Yb": 3,
    "O": -2,
}

HYDRIDE_PATTERNS = (
    "Na3AlH6",
    "NaAlH4",
    "NaBH4",
)

AMIDE_PATTERNS = (
    "NaNH2",
    "NaH2N",
)

CLUSTER_BOROHYDRIDE_PATTERNS = (
    "NaCB9H10",
    "NaB9H10C",
    "NaCB11H12",
    "NaB11H12C",
    "Na2B10H10",
    "Na2B12H12",
    "Na(BH)5",
    "Na(BH)6",
)


CSV_COLUMNS = [
    "structure",
    "cif_path",
    "status",
    "softBV网格分辨率_A",
    "softBV通道维度",
    "softBV连通能量阈值_eV",
    "softBV_1D连通能量阈值_eV",
    "softBV_2D连通能量阈值_eV",
    "softBV_3D连通能量阈值_eV",
    "softBV迁移瓶颈_eV",
    "softBV可迁移体积分数",
    "activation_1D_eV",
    "activation_2D_eV",
    "activation_3D_eV",
    "cube_global_min_eV",
    "cube_grid_points",
    "workdir",
    "error",
]


@dataclass(frozen=True)
class Config:
    cif_dir: Path
    bin_dir: Path
    output_dir: Path
    ion: str
    oxidation_state: int
    screening_factor: float
    resolution: float
    ignore_conducting_ion: str
    periodic: str
    bvpa_max_energy: float
    jobs: int
    force: bool
    only: tuple[str, ...]
    timeout: int


def parse_args() -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Generate softBV cube files and extract channel dimension, "
            "percolation threshold, migration bottleneck, and accessible "
            "volume fraction for a directory of CIF files."
        )
    )
    parser.add_argument("--cif-dir", type=Path, default=Path("CIF_91"))
    parser.add_argument("--bin-dir", type=Path, default=Path("bin"))
    parser.add_argument("--output-dir", type=Path, default=Path("softBV_CIF_91_results"))
    parser.add_argument("--ion", default="Na", help="Conducting ion type, default: Na")
    parser.add_argument("--oxidation-state", type=int, default=1)
    parser.add_argument(
        "--screening-factor",
        type=float,
        default=0.0,
        help="<=0 lets softBV estimate it automatically.",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=0.1,
        help="Preferred cube voxel spacing in Angstrom.",
    )
    parser.add_argument(
        "--ignore-conducting-ion",
        choices=("t", "f"),
        default="t",
        help="softBV --gen-cube ignore_conducting flag.",
    )
    parser.add_argument(
        "--periodic",
        choices=("t", "f"),
        default="t",
        help="Treat generated cube as periodic.",
    )
    parser.add_argument(
        "--bvpa-max-energy",
        type=float,
        default=5.0,
        help="Maximum BVPA energy window above the global minimum in eV.",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--force", action="store_true", help="Recompute existing workdirs.")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Only process CIFs whose file name or stem matches this shell-style pattern. Repeatable.",
    )
    parser.add_argument("--timeout", type=int, default=7200, help="Seconds per external command.")
    args = parser.parse_args()

    return Config(
        cif_dir=args.cif_dir.resolve(),
        bin_dir=args.bin_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        ion=args.ion,
        oxidation_state=args.oxidation_state,
        screening_factor=args.screening_factor,
        resolution=args.resolution,
        ignore_conducting_ion=args.ignore_conducting_ion,
        periodic=args.periodic,
        bvpa_max_energy=args.bvpa_max_energy,
        jobs=max(1, args.jobs),
        force=args.force,
        only=tuple(args.only),
        timeout=args.timeout,
    )


def make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_if_needed(src: Path, dst: Path) -> None:
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return
    shutil.copy2(src, dst)


def prepare_runtime_bin(config: Config) -> tuple[Path, Path]:
    softbv_src = config.bin_dir / "softBV.x"
    bvpa_src = config.bin_dir / "BVPA.x"
    if not softbv_src.exists():
        raise FileNotFoundError(f"softBV executable not found: {softbv_src}")
    if not bvpa_src.exists():
        raise FileNotFoundError(f"BVPA executable not found: {bvpa_src}")

    runtime = config.output_dir / "_runtime_bin"
    runtime.mkdir(parents=True, exist_ok=True)
    softbv = runtime / "softBV.x"
    bvpa = runtime / "BVPA.x"
    copy_if_needed(softbv_src, softbv)
    copy_if_needed(bvpa_src, bvpa)
    for db in config.bin_dir.glob("database_*.dat"):
        copy_if_needed(db, runtime / db.name)
    make_executable(softbv)
    make_executable(bvpa)
    return softbv, bvpa


def prepare_workdir(config: Config, cif: Path) -> Path:
    digest = hashlib.sha1(str(cif).encode("utf-8")).hexdigest()[:8]
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", cif.stem)[:120]
    workdir = config.output_dir / "work" / f"{safe_stem}__{digest}"
    workdir.mkdir(parents=True, exist_ok=True)
    for db in config.bin_dir.glob("database_*.dat"):
        dst = workdir / db.name
        if dst.is_symlink() or not dst.exists():
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            shutil.copy2(db, dst)
    return workdir


def ion_label(element: str, oxidation_state: int) -> str:
    sign = "+" if oxidation_state > 0 else "-"
    return f"{element}{abs(oxidation_state)}{sign}"


def split_cif_tokens(line: str) -> list[str]:
    # The pymatgen CIF files used here have simple whitespace-separated rows.
    return line.split()


def cif_text_contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    compact = re.sub(r"\s+", "", text)
    return any(pattern in compact for pattern in patterns)


def oxidation_states_for_cif(input_cif: Path, lines: list[str]) -> dict[str, int]:
    """Return oxidation-state defaults for one CIF.

    Most inorganic CIFs can use the project default table. Hydrogen-bearing
    salts need structure-level handling because H is -1 in hydrides/borohydrides
    but +1 in amides; cluster borohydrides do not have a clean atom-wise formal
    valence assignment suitable for this automatic softBV preprocessing.
    """

    states = dict(DEFAULT_OXIDATION_STATES)
    text = "\n".join(lines)
    name_and_formula = input_cif.name + "\n" + text

    if cif_text_contains_any(name_and_formula, CLUSTER_BOROHYDRIDE_PATTERNS):
        raise ValueError(
            "cluster/carborane borohydride has no unambiguous atom-wise H/B/C "
            f"formal valence for automatic softBV preprocessing: {input_cif}"
        )

    if cif_text_contains_any(name_and_formula, HYDRIDE_PATTERNS):
        states["H"] = -1
    elif cif_text_contains_any(name_and_formula, AMIDE_PATTERNS):
        states["H"] = 1
        states["N"] = -3

    return states


def cif_loop_data_end(lines: list[str], start: int) -> int:
    """Return the index after a CIF loop data block."""

    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            break
        if stripped == "loop_" or stripped.startswith("_") or stripped.startswith("data_"):
            break
        i += 1
    return i


def make_softbv_cif(
    input_cif: Path,
    output_cif: Path,
    exclude_site_elements: set[str] | None = None,
) -> Path:
    """Write a CIF with explicit oxidation labels required by softBV 1.2.

    softBV expects _atom_type_oxidation_number and atom site type symbols like
    Na1+ or S2-. Pymatgen CIFs in CIF_85 only carry bare element symbols, and
    this softBV build segfaults on those files instead of reporting a clean
    input error.
    """

    lines = input_cif.read_text(encoding="utf-8", errors="replace").splitlines()
    oxidation_states = oxidation_states_for_cif(input_cif, lines)
    exclude_site_elements = exclude_site_elements or set()
    output: list[str] = []
    site_elements: set[str] = set()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() != "loop_":
            output.append(line)
            i += 1
            continue

        header_start = i + 1
        header_end = header_start
        headers: list[str] = []
        while header_end < len(lines) and lines[header_end].lstrip().startswith("_"):
            headers.append(lines[header_end].strip())
            header_end += 1

        if any(header.startswith("_atom_site_aniso_") for header in headers):
            i = cif_loop_data_end(lines, header_end)
            continue

        if "_atom_type_symbol" in headers and "_atom_type_oxidation_number" in headers:
            i = cif_loop_data_end(lines, header_end)
            continue

        if "_atom_site_type_symbol" not in headers:
            output.extend(lines[i:header_end])
            i = header_end
            continue

        required_headers = [
            "_atom_site_label",
            "_atom_site_type_symbol",
            "_atom_site_fract_x",
            "_atom_site_fract_y",
            "_atom_site_fract_z",
        ]
        missing_headers = [header for header in required_headers if header not in headers]
        if missing_headers:
            raise ValueError(f"missing required atom_site columns {missing_headers} in {input_cif}")

        label_index = headers.index("_atom_site_label")
        type_index = headers.index("_atom_site_type_symbol")
        x_index = headers.index("_atom_site_fract_x")
        y_index = headers.index("_atom_site_fract_y")
        z_index = headers.index("_atom_site_fract_z")
        occ_index = headers.index("_atom_site_occupancy") if "_atom_site_occupancy" in headers else None
        output.extend(
            [
                "loop_",
                "_atom_site_label",
                "_atom_site_type_symbol",
                "_atom_site_fract_x",
                "_atom_site_fract_y",
                "_atom_site_fract_z",
                "_atom_site_occupancy",
            ]
        )
        data_end = header_end
        expected_fields = len(headers)
        while data_end < len(lines):
            stripped = lines[data_end].strip()
            if not stripped:
                output.append(lines[data_end])
                data_end += 1
                break
            if stripped == "loop_" or stripped.startswith("_") or stripped.startswith("data_"):
                break

            tokens: list[str] = []
            while data_end < len(lines) and len(tokens) < expected_fields:
                row_text = lines[data_end].strip()
                if not row_text:
                    break
                if row_text == "loop_" or row_text.startswith("_") or row_text.startswith("data_"):
                    break
                tokens.extend(split_cif_tokens(lines[data_end]))
                data_end += 1

            if len(tokens) > type_index:
                element_match = re.match(r"([A-Z][a-z]?)", tokens[type_index])
                if element_match:
                    element = element_match.group(1)
                    if element in exclude_site_elements:
                        continue
                    if element not in oxidation_states:
                        raise ValueError(
                            f"no default oxidation state for element {element} in {input_cif}"
                        )
                    site_elements.add(element)
                    output.append(
                        "  "
                        + "  ".join(
                            [
                                tokens[label_index],
                                ion_label(element, oxidation_states[element]),
                                tokens[x_index],
                                tokens[y_index],
                                tokens[z_index],
                                tokens[occ_index] if occ_index is not None and len(tokens) > occ_index else "1.0000",
                            ]
                        )
                    )
                else:
                    output.append(
                        "  "
                        + "  ".join(
                            [
                                tokens[label_index],
                                tokens[type_index],
                                tokens[x_index],
                                tokens[y_index],
                                tokens[z_index],
                                tokens[occ_index] if occ_index is not None and len(tokens) > occ_index else "1.0000",
                            ]
                        )
                    )
            else:
                output.append("  " + "  ".join(tokens))

        i = data_end

    if not site_elements:
        raise ValueError(f"no atom site loop found in {input_cif}")

    text = "\n".join(output) + "\n"
    if "_atom_type_oxidation_number" not in text:
        type_lines = ["loop_", " _atom_type_symbol", " _atom_type_oxidation_number"]
        for element in sorted(site_elements):
            oxidation_state = oxidation_states[element]
            type_lines.append(f"  {ion_label(element, oxidation_state)}  {oxidation_state}")
        insert_block = "\n".join(type_lines) + "\n"

        match = re.search(r"(?m)^loop_\s*$", text)
        if match:
            text = text[: match.start()] + insert_block + text[match.start() :]
        else:
            text += insert_block

    output_cif.write_text(text, encoding="utf-8")
    return output_cif


def run_command(
    command: list[str],
    cwd: Path,
    log_path: Path,
    timeout: int,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    log_path.write_text(
        "$ " + " ".join(command) + "\n\n" + proc.stdout,
        encoding="utf-8",
        errors="replace",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed with code {proc.returncode}: {' '.join(command)}")
    return proc


def collect_bvpa_text(workdir: Path, bvpa_stdout: str) -> str:
    chunks = [bvpa_stdout]
    for pattern in ("BVPA*.txt", "BVPA*.csv", "BVPA*.log"):
        for path in sorted(workdir.glob(pattern)):
            try:
                chunks.append(f"\n\n# {path.name}\n")
                chunks.append(path.read_text(encoding="utf-8", errors="replace")[:2_000_000])
            except OSError:
                pass
    return "\n".join(chunks)


def parse_float(text: str) -> float | None:
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_bvpa_metrics(text: str) -> dict[str, object]:
    metrics: dict[str, object] = {}

    activations: dict[int, float] = {}
    for dim, value in re.findall(rf"\b([123])D\s+activation energy:\s*({FLOAT_RE})\s*eV", text, re.I):
        parsed = parse_float(value)
        if parsed is not None:
            activations[int(dim)] = parsed

    dimension_candidates: list[int] = []
    dimension_patterns = [
        r"Pathway dimension:\s*([123])D",
        r">>\s*Dimension:\s*([123])\b",
        r"Percolating\s*\(([123])D\)",
        r"Print cluster,\s*dimension:\s*([123])\b",
    ]
    for pattern in dimension_patterns:
        dimension_candidates.extend(int(x) for x in re.findall(pattern, text, re.I))

    if dimension_candidates:
        channel_dim = max(dimension_candidates)
    elif activations:
        channel_dim = max(activations)
    else:
        channel_dim = None

    threshold_candidates: list[float] = []
    threshold_patterns = [
        rf"Threshold energy:\s*({FLOAT_RE})\s*eV",
        rf"Max threshold\s*({FLOAT_RE})",
        rf"Current maximum energy threshold is\s*({FLOAT_RE})\s*eV",
        rf"Maximum energy threshold is now changed to\s*({FLOAT_RE})\s*eV",
    ]
    for pattern in threshold_patterns:
        for value in re.findall(pattern, text, re.I):
            parsed = parse_float(value)
            if parsed is not None:
                threshold_candidates.append(parsed)

    cluster_min = [parse_float(x) for x in re.findall(rf"Cluster energy minimum\s*:\s*({FLOAT_RE})", text, re.I)]
    cluster_max = [parse_float(x) for x in re.findall(rf"Cluster energy maximum\s*:\s*({FLOAT_RE})", text, re.I)]
    cluster_min = [x for x in cluster_min if x is not None]
    cluster_max = [x for x in cluster_max if x is not None]

    selected_activation = activations.get(channel_dim) if channel_dim is not None else None
    if selected_activation is None and activations:
        selected_activation = activations[max(activations)]

    if selected_activation is not None:
        bottleneck = selected_activation
    elif cluster_min and cluster_max:
        bottleneck = max(cluster_max) - min(cluster_min)
    else:
        bottleneck = None

    if selected_activation is not None:
        threshold = selected_activation
    elif threshold_candidates:
        nonnegative_thresholds = [x for x in threshold_candidates if x >= 0]
        threshold = min(nonnegative_thresholds) if nonnegative_thresholds else None
    elif bottleneck is not None:
        threshold = bottleneck
    else:
        threshold = None

    metrics["channel_dim"] = channel_dim
    metrics["percolation_threshold_eV"] = threshold
    metrics["migration_bottleneck_eV"] = bottleneck
    metrics["activation_1D_eV"] = activations.get(1)
    metrics["activation_2D_eV"] = activations.get(2)
    metrics["activation_3D_eV"] = activations.get(3)
    return metrics


def cube_header(path: Path) -> tuple[int, int]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        handle.readline()
        handle.readline()
        atom_line = handle.readline().split()
        if not atom_line:
            raise ValueError(f"invalid cube header: {path}")
        natoms = int(float(atom_line[0]))
        grid_counts = []
        for _ in range(3):
            parts = handle.readline().split()
            if not parts:
                raise ValueError(f"invalid cube grid header: {path}")
            grid_counts.append(abs(int(float(parts[0]))))
    total_points = grid_counts[0] * grid_counts[1] * grid_counts[2]
    return abs(natoms), total_points


def iter_cube_values(path: Path) -> Iterable[float]:
    natoms, total_points = cube_header(path)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for _ in range(6 + natoms):
            handle.readline()
        yielded = 0
        for line in handle:
            for token in line.split():
                try:
                    yield float(token)
                    yielded += 1
                except ValueError:
                    continue
                if yielded >= total_points:
                    return


def cube_min_and_count(path: Path) -> tuple[float | None, int]:
    minimum: float | None = None
    count = 0
    for value in iter_cube_values(path):
        count += 1
        if minimum is None or value < minimum:
            minimum = value
    return minimum, count


def cube_accessible_fraction(path: Path, threshold_eV: float | None, cube_min_eV: float | None) -> float | None:
    if threshold_eV is None or cube_min_eV is None:
        return None
    accessible = 0
    total = 0
    limit = cube_min_eV + threshold_eV
    for value in iter_cube_values(path):
        total += 1
        if value <= limit:
            accessible += 1
    if total == 0:
        return None
    return accessible / total


def format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def fill_derived_columns(row: dict[str, str]) -> dict[str, str]:
    filled = dict(row)
    aliases = {
        "softBV_1D连通能量阈值_eV": "activation_1D_eV",
        "softBV_2D连通能量阈值_eV": "activation_2D_eV",
        "softBV_3D连通能量阈值_eV": "activation_3D_eV",
    }
    for alias, source in aliases.items():
        if not filled.get(alias) and filled.get(source):
            filled[alias] = filled[source]
    return filled


def process_one(cif: Path, config: Config, softbv: Path, bvpa: Path) -> dict[str, str]:
    print(f"[start] {cif.name}", flush=True)
    workdir = prepare_workdir(config, cif)
    softbv_cif = workdir / "softbv_input.cif"
    cube = workdir / f"{cif.stem}.cube"
    row: dict[str, object] = {
        "structure": cif.stem,
        "cif_path": str(cif),
        "status": "failed",
        "softBV网格分辨率_A": config.resolution,
        "workdir": str(workdir),
        "error": "",
    }

    try:
        exclude_site_elements = {config.ion} if config.ignore_conducting_ion == "t" else set()
        make_softbv_cif(cif, softbv_cif, exclude_site_elements=exclude_site_elements)

        if config.force and cube.exists():
            cube.unlink()

        if not cube.exists():
            softbv_cmd = [
                str(softbv),
                "--gen-cube",
                str(softbv_cif),
                config.ion,
                str(config.oxidation_state),
                str(config.screening_factor),
                str(config.resolution),
                config.ignore_conducting_ion,
                config.periodic,
                str(cube),
            ]
            run_command(softbv_cmd, workdir, workdir / "softbv_gen_cube.log", config.timeout)

        bvpa_cmd = [
            str(bvpa),
            "--cif",
            str(softbv_cif),
            "--cube",
            str(cube),
            "--max",
            str(config.bvpa_max_energy),
            "--path",
            "--hk",
            "--summary",
            "--print-act",
            "--print-perc",
        ]
        bvpa_proc = run_command(bvpa_cmd, workdir, workdir / "bvpa.log", config.timeout, check=False)
        bvpa_text = collect_bvpa_text(workdir, bvpa_proc.stdout)
        (workdir / "bvpa_all_text_for_parsing.txt").write_text(
            bvpa_text,
            encoding="utf-8",
            errors="replace",
        )
        if bvpa_proc.returncode != 0:
            raise RuntimeError(f"BVPA failed with code {bvpa_proc.returncode}")

        parsed = parse_bvpa_metrics(bvpa_text)
        cube_min_eV, cube_count = cube_min_and_count(cube)
        volume_fraction = cube_accessible_fraction(
            cube,
            parsed.get("percolation_threshold_eV"),  # type: ignore[arg-type]
            cube_min_eV,
        )

        row.update(
            {
                "status": "ok",
                "softBV通道维度": parsed.get("channel_dim"),
                "softBV连通能量阈值_eV": parsed.get("percolation_threshold_eV"),
                "softBV_1D连通能量阈值_eV": parsed.get("activation_1D_eV"),
                "softBV_2D连通能量阈值_eV": parsed.get("activation_2D_eV"),
                "softBV_3D连通能量阈值_eV": parsed.get("activation_3D_eV"),
                "softBV迁移瓶颈_eV": parsed.get("migration_bottleneck_eV"),
                "softBV可迁移体积分数": volume_fraction,
                "activation_1D_eV": parsed.get("activation_1D_eV"),
                "activation_2D_eV": parsed.get("activation_2D_eV"),
                "activation_3D_eV": parsed.get("activation_3D_eV"),
                "cube_global_min_eV": cube_min_eV,
                "cube_grid_points": cube_count,
            }
        )
    except Exception as exc:  # noqa: BLE001
        row["error"] = str(exc)

    return {key: format_value(row.get(key)) for key in CSV_COLUMNS}


def write_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with tmp_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(fill_derived_columns(row) for row in rows)
    tmp_path.replace(csv_path)


def read_existing_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def replace_row(rows: list[dict[str, str]], new_row: dict[str, str]) -> list[dict[str, str]]:
    replaced = False
    updated: list[dict[str, str]] = []
    for row in rows:
        if row.get("structure") == new_row.get("structure"):
            updated.append(new_row)
            replaced = True
        else:
            updated.append(row)
    if not replaced:
        updated.append(new_row)
    updated.sort(key=lambda row: row["structure"])
    return updated


def matches_only(cif: Path, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return True
    return any(
        fnmatch.fnmatch(cif.name, pattern) or fnmatch.fnmatch(cif.stem, pattern)
        for pattern in patterns
    )


def main() -> int:
    config = parse_args()
    if not config.cif_dir.exists():
        print(f"CIF directory not found: {config.cif_dir}", file=sys.stderr)
        return 2

    cifs = sorted(cif for cif in config.cif_dir.glob("*.cif") if matches_only(cif, config.only))
    if not cifs:
        print(f"No matching CIF files found in: {config.cif_dir}", file=sys.stderr)
        return 2

    config.output_dir.mkdir(parents=True, exist_ok=True)
    softbv, bvpa = prepare_runtime_bin(config)
    csv_path = config.output_dir / "softbv_cif_metrics.csv"

    rows: list[dict[str, str]] = read_existing_rows(csv_path) if config.only else []
    if config.jobs == 1:
        for index, cif in enumerate(cifs, start=1):
            print(f"[{index}/{len(cifs)}] {cif.name}", flush=True)
            rows = replace_row(rows, process_one(cif, config, softbv, bvpa))
            write_rows(csv_path, rows)
    else:
        with ThreadPoolExecutor(max_workers=config.jobs) as executor:
            futures = {
                executor.submit(process_one, cif, config, softbv, bvpa): cif
                for cif in cifs
            }
            completed = 0
            for future in as_completed(futures):
                completed += 1
                cif = futures[future]
                print(f"[{completed}/{len(cifs)}] {cif.name}", flush=True)
                rows = replace_row(rows, future.result())
                write_rows(csv_path, rows)

    print(f"Result CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
