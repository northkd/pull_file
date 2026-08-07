#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch-download crystal structures from AFLOW and save them as CIF files.

Default query:
    - contains Na
    - catalog = ICSD
    - relaxed structure
    - maximum 1000 records

The script:
    1. Searches AFLOW through the AFLUX API.
    2. Reads the per-entry file list.
    3. Downloads an existing CIF when available.
    4. Otherwise downloads CONTCAR.relax and converts it to CIF with pymatgen.
    5. Writes manifest.csv and errors.jsonl for provenance and recovery.

AFLOW data usage is subject to the terms displayed by the AFLOW repository.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import logging
import re
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


AFLOW_SEARCH_API = "https://aflow.org/API/aflux/"
DEFAULT_FIELDS = [
    "auid",
    "aurl",
    "compound",
    "catalog",
    "species",
    "nspecies",
    "natoms",
    "spacegroup_orig",
    "spacegroup_relax",
    "Pearson_symbol_orig",
    "Pearson_symbol_relax",
    "aflow_prototype_label_orig",
    "aflow_prototype_label_relax",
    "Egap",
    "enthalpy_formation_atom",
    "files",
    "aflowlib_date",
    "aflowlib_version",
]
USER_AGENT = "aflow-cif-downloader/1.0 (academic materials research)"


@dataclass
class DownloadResult:
    auid: str
    compound: str
    status: str
    output_file: str = ""
    source_file: str = ""
    source_url: str = ""
    aurl: str = ""
    catalog: str = ""
    species: str = ""
    nspecies: str = ""
    natoms: str = ""
    spacegroup_orig: str = ""
    spacegroup_relax: str = ""
    pearson_orig: str = ""
    pearson_relax: str = ""
    prototype_orig: str = ""
    prototype_relax: str = ""
    band_gap_eV: str = ""
    formation_enthalpy_eV_atom: str = ""
    aflowlib_date: str = ""
    aflowlib_version: str = ""
    error: str = ""


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search AFLOW and batch-download matching crystal structures as CIF."
    )
    parser.add_argument(
        "--element",
        default="Na",
        help="Required element. Default: Na",
    )
    parser.add_argument(
        "--catalog",
        default="ICSD",
        help="AFLOW catalog, e.g. ICSD. Use ALL to omit the catalog filter. Default: ICSD",
    )
    parser.add_argument(
        "--structure",
        choices=("relaxed", "original"),
        default="relaxed",
        help="Prefer relaxed or original structure. Default: relaxed",
    )
    parser.add_argument(
        "--any-elements",
        default="",
        help=(
            "Client-side filter: retain entries containing at least one listed element. "
            "Comma-separated, e.g. O,S,Se,F,Cl,Br,I"
        ),
    )
    parser.add_argument(
        "--exclude-elements",
        default="",
        help="Client-side exclusion list, comma-separated.",
    )
    parser.add_argument(
        "--min-egap",
        type=float,
        default=None,
        help="Optional minimum AFLOW band gap in eV. Missing values are excluded.",
    )
    parser.add_argument(
        "--aflux-filter",
        action="append",
        default=[],
        help=(
            "Additional raw AFLUX predicate. Repeat as needed, e.g. "
            "--aflux-filter 'nspecies(2*,*5)'"
        ),
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="AFLUX records per page. Default: 100",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=1000,
        help="Maximum accepted records. Use 0 for unlimited. Default: 1000",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent downloads. Default: 4",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds. Default: 60",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("aflow_cif"),
        help="Output directory. Default: ./aflow_cif",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CIF files.",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Keep downloaded POSCAR/CONTCAR source files used for conversion.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate each final CIF with pymatgen.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Search and write metadata without downloading structures.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Optional delay after each entry download, in seconds.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    args = parser.parse_args()

    if args.page_size < 1:
        parser.error("--page-size must be >= 1")
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    if args.max_records < 0:
        parser.error("--max-records must be >= 0")
    return args


def split_elements(value: str) -> set[str]:
    return {x.strip() for x in value.split(",") if x.strip()}


def normalize_species(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value]
    if isinstance(value, tuple):
        return [str(x).strip() for x in value]
    text = str(value).strip().strip("[]")
    text = text.replace("'", "").replace('"', "")
    return [x.strip() for x in text.split(",") if x.strip()]


def normalize_files(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items: list[str] = []
        for part in value:
            items.extend(normalize_files(part))
        return items
    text = str(value).strip().strip("[]")
    text = text.replace("'", "").replace('"', "")
    return [x.strip() for x in text.split(",") if x.strip()]


def extract_entries(payload: Any) -> list[dict[str, Any]]:
    """Accept both AFLUX array output and keyed-object output."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict) and x.get("auid")]

    if isinstance(payload, dict):
        if payload.get("auid"):
            return [payload]
        entries = []
        for value in payload.values():
            if isinstance(value, dict) and value.get("auid"):
                entries.append(value)
        return entries

    raise ValueError(f"Unexpected AFLUX JSON type: {type(payload).__name__}")


def build_query(args: argparse.Namespace, page: int) -> str:
    components = [f"species({args.element})"]

    if args.catalog.upper() != "ALL":
        components.append(f"catalog({args.catalog})")

    components.extend(args.aflux_filter)
    components.extend(DEFAULT_FIELDS)
    components.append("format(json)")
    # The muted paging directive requests a plain JSON array.
    components.append(f"$paging({page},{args.page_size})")
    return ",".join(components)


def search_page(
    session: requests.Session,
    args: argparse.Namespace,
    page: int,
) -> tuple[list[dict[str, Any]], str]:
    query = build_query(args, page)
    url = AFLOW_SEARCH_API + "?" + query
    logging.debug("AFLUX query URL: %s", url)

    response = session.get(url, timeout=args.timeout)
    response.raise_for_status()

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        preview = response.text[:500].replace("\n", " ")
        raise RuntimeError(f"AFLUX returned non-JSON content: {preview}") from exc

    return extract_entries(payload), url


def entry_passes_filters(entry: dict[str, Any], args: argparse.Namespace) -> bool:
    species = set(normalize_species(entry.get("species")))
    any_elements = split_elements(args.any_elements)
    excluded = split_elements(args.exclude_elements)

    if any_elements and not species.intersection(any_elements):
        return False
    if excluded and species.intersection(excluded):
        return False

    if args.min_egap is not None:
        try:
            gap = float(entry["Egap"])
        except (KeyError, TypeError, ValueError):
            return False
        if gap < args.min_egap:
            return False

    return True


def aurl_to_base_url(aurl: str) -> str:
    text = aurl.strip()
    if not text:
        raise ValueError("Missing aurl")

    if text.startswith(("http://", "https://")):
        return text.rstrip("/") + "/"

    # AFLOW commonly returns:
    # aflowlib.duke.edu:AFLOWDATA/ICSD_WEB/...
    if ":" in text:
        host, path = text.split(":", 1)
        return f"https://{host}/{path.lstrip('/')}/"

    return f"https://{text.strip('/')}/"


def choose_source_file(files: Iterable[str], structure: str) -> tuple[str, str]:
    """
    Return (filename, mode), where mode is direct_cif or convert_poscar.
    """
    names = [x for x in files if x]

    cif_files = [x for x in names if x.lower().endswith((".cif", ".cif.gz"))]
    contcars = [x for x in names if Path(x).name.upper().startswith("CONTCAR")]
    poscars = [x for x in names if Path(x).name.upper().startswith("POSCAR")]

    if structure == "relaxed":
        # AFLOW's entry-level CIF is generally the most convenient relaxed structure.
        if cif_files:
            preferred = sorted(
                cif_files,
                key=lambda x: (
                    "orig" in x.lower(),
                    "relax" not in x.lower(),
                    len(x),
                    x,
                ),
            )
            return preferred[0], "direct_cif"

        ranked_contcars = sorted(
            contcars,
            key=lambda x: (
                Path(x).name != "CONTCAR.relax",
                "relax" not in x.lower(),
                x,
            ),
        )
        if ranked_contcars:
            return ranked_contcars[0], "convert_poscar"

        if poscars:
            return sorted(poscars)[0], "convert_poscar"

    else:
        original_cifs = [x for x in cif_files if "orig" in x.lower()]
        if original_cifs:
            return sorted(original_cifs)[0], "direct_cif"

        ranked_poscars = sorted(
            poscars,
            key=lambda x: (
                Path(x).name not in {"POSCAR.orig", "POSCAR"},
                "orig" not in x.lower(),
                x,
            ),
        )
        if ranked_poscars:
            return ranked_poscars[0], "convert_poscar"

        # Last-resort fallback if the entry does not expose an original file.
        if cif_files:
            return sorted(cif_files)[0], "direct_cif"

    raise FileNotFoundError(
        f"No usable CIF/POSCAR/CONTCAR found. Available files: {', '.join(names[:30])}"
    )


def safe_name(value: Any, fallback: str = "unknown") -> str:
    text = str(value or fallback).strip()
    text = re.sub(r"[^A-Za-z0-9._+-]+", "_", text)
    return text.strip("._") or fallback


def auid_token(auid: str) -> str:
    token = auid.split(":", 1)[-1]
    return safe_name(token, "no_auid")


def is_probably_html(data: bytes) -> bool:
    head = data[:300].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def download_bytes(url: str, timeout: float) -> bytes:
    session = build_session()
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.content
    if not data:
        raise RuntimeError("Downloaded file is empty")
    if is_probably_html(data):
        raise RuntimeError("Server returned HTML instead of a structure file")
    return data


def import_pymatgen() -> tuple[Any, Any]:
    try:
        from pymatgen.core import Structure
        from pymatgen.io.cif import CifWriter
    except ImportError as exc:
        raise RuntimeError(
            "pymatgen is required to convert POSCAR/CONTCAR to CIF. "
            "Install it with: python -m pip install pymatgen"
        ) from exc
    return Structure, CifWriter


def convert_poscar_bytes_to_cif(data: bytes, output_path: Path) -> None:
    Structure, CifWriter = import_pymatgen()
    text = data.decode("utf-8", errors="replace")
    structure = Structure.from_str(text, fmt="poscar")
    writer = CifWriter(structure, symprec=None)
    writer.write_file(str(output_path))


def validate_cif(path: Path) -> None:
    Structure, _ = import_pymatgen()
    structure = Structure.from_file(str(path))
    if len(structure) == 0:
        raise RuntimeError("Parsed CIF contains zero sites")


def direct_cif_bytes(data: bytes, source_file: str) -> bytes:
    if source_file.lower().endswith(".gz"):
        try:
            return gzip.decompress(data)
        except OSError as exc:
            raise RuntimeError("Failed to decompress .cif.gz file") from exc
    return data


def result_from_entry(entry: dict[str, Any], status: str, **kwargs: Any) -> DownloadResult:
    species = ",".join(normalize_species(entry.get("species")))
    return DownloadResult(
        auid=str(entry.get("auid", "")),
        compound=str(entry.get("compound", "")),
        status=status,
        aurl=str(entry.get("aurl", "")),
        catalog=str(entry.get("catalog", "")),
        species=species,
        nspecies=str(entry.get("nspecies", "")),
        natoms=str(entry.get("natoms", "")),
        spacegroup_orig=str(entry.get("spacegroup_orig", "")),
        spacegroup_relax=str(entry.get("spacegroup_relax", "")),
        pearson_orig=str(entry.get("Pearson_symbol_orig", "")),
        pearson_relax=str(entry.get("Pearson_symbol_relax", "")),
        prototype_orig=str(entry.get("aflow_prototype_label_orig", "")),
        prototype_relax=str(entry.get("aflow_prototype_label_relax", "")),
        band_gap_eV=str(entry.get("Egap", "")),
        formation_enthalpy_eV_atom=str(entry.get("enthalpy_formation_atom", "")),
        aflowlib_date=str(entry.get("aflowlib_date", "")),
        aflowlib_version=str(entry.get("aflowlib_version", "")),
        **kwargs,
    )


def process_entry(entry: dict[str, Any], args: argparse.Namespace) -> DownloadResult:
    auid = str(entry.get("auid", "")).strip()
    compound = safe_name(entry.get("compound"), "unknown")
    token = auid_token(auid)
    output_name = f"{compound}__{token}.cif"
    output_path = args.output / "cif" / output_name

    if args.metadata_only:
        return result_from_entry(entry, "metadata_only")

    if output_path.exists() and output_path.stat().st_size > 0 and not args.force:
        return result_from_entry(
            entry,
            "skipped_existing",
            output_file=str(output_path),
        )

    try:
        files = normalize_files(entry.get("files"))
        source_file, mode = choose_source_file(files, args.structure)
        base_url = aurl_to_base_url(str(entry.get("aurl", "")))
        source_url = base_url + quote(source_file, safe="/._+-")
        data = download_bytes(source_url, args.timeout)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=output_path.stem + "_",
            suffix=".cif.part",
            dir=output_path.parent,
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            if mode == "direct_cif":
                cif_data = direct_cif_bytes(data, source_file)
                tmp_path.write_bytes(cif_data)
            else:
                convert_poscar_bytes_to_cif(data, tmp_path)

            if args.validate:
                validate_cif(tmp_path)

            tmp_path.replace(output_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        if args.keep_source and mode == "convert_poscar":
            source_dir = args.output / "source_structures"
            source_dir.mkdir(parents=True, exist_ok=True)
            source_output = source_dir / f"{compound}__{token}__{safe_name(source_file)}"
            source_output.write_bytes(data)

        if args.sleep > 0:
            time.sleep(args.sleep)

        return result_from_entry(
            entry,
            "downloaded",
            output_file=str(output_path),
            source_file=source_file,
            source_url=source_url,
        )

    except Exception as exc:
        return result_from_entry(
            entry,
            "failed",
            error=f"{type(exc).__name__}: {exc}",
        )


def manifest_fields() -> list[str]:
    return list(DownloadResult.__dataclass_fields__.keys())


def load_existing_results(path: Path) -> dict[str, DownloadResult]:
    if not path.exists():
        return {}

    results: dict[str, DownloadResult] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("auid"):
                continue
            clean = {key: row.get(key, "") for key in manifest_fields()}
            results[row["auid"]] = DownloadResult(**clean)
    return results


def write_manifest(path: Path, results: dict[str, DownloadResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields())
        writer.writeheader()
        for auid in sorted(results):
            writer.writerow(asdict(results[auid]))
    temp_path.replace(path)


def write_errors(path: Path, results: dict[str, DownloadResult]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        for auid in sorted(results):
            result = results[auid]
            if result.status == "failed":
                handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
    temp_path.replace(path)


def write_query_log(path: Path, records: list[dict[str, Any]]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args.output = args.output.expanduser().resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest_path = args.output / "manifest.csv"
    errors_path = args.output / "errors.jsonl"
    query_log_path = args.output / "query_log.json"

    all_results = load_existing_results(manifest_path)
    query_log: list[dict[str, Any]] = []
    session = build_session()

    accepted = 0
    page = 1
    stop = False

    logging.info("Output directory: %s", args.output)
    logging.info(
        "Searching AFLOW: required element=%s, catalog=%s, structure=%s",
        args.element,
        args.catalog,
        args.structure,
    )

    while not stop:
        try:
            entries, query_url = search_page(session, args, page)
        except Exception as exc:
            logging.error("Search failed on page %d: %s", page, exc)
            return 2

        query_log.append(
            {
                "page": page,
                "url": query_url,
                "returned_records": len(entries),
                "timestamp_unix": time.time(),
            }
        )
        write_query_log(query_log_path, query_log)

        if not entries:
            logging.info("No records returned on page %d; search complete.", page)
            break

        selected: list[dict[str, Any]] = []
        for entry in entries:
            if not entry_passes_filters(entry, args):
                continue
            if args.max_records and accepted >= args.max_records:
                stop = True
                break
            selected.append(entry)
            accepted += 1

        logging.info(
            "Page %d: returned=%d, accepted_this_page=%d, accepted_total=%d",
            page,
            len(entries),
            len(selected),
            accepted,
        )

        if selected:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(process_entry, entry, args): entry
                    for entry in selected
                }
                for future in as_completed(futures):
                    result = future.result()
                    all_results[result.auid] = result
                    if result.status == "failed":
                        logging.warning(
                            "Failed: %s %s | %s",
                            result.compound,
                            result.auid,
                            result.error,
                        )
                    else:
                        logging.info(
                            "%s: %s %s",
                            result.status,
                            result.compound,
                            result.auid,
                        )

            write_manifest(manifest_path, all_results)
            write_errors(errors_path, all_results)

        if len(entries) < args.page_size:
            logging.info("Last AFLUX page reached.")
            break

        page += 1

    write_manifest(manifest_path, all_results)
    write_errors(errors_path, all_results)
    write_query_log(query_log_path, query_log)

    counts: dict[str, int] = {}
    for result in all_results.values():
        counts[result.status] = counts.get(result.status, 0) + 1

    logging.info("Finished. Status counts: %s", counts)
    logging.info("Manifest: %s", manifest_path)
    logging.info("Errors: %s", errors_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
