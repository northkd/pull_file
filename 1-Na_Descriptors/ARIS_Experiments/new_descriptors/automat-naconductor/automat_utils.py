"""Shared utilities for the independent structural Agent track.

The Agent track evaluates one explicitly named, registered structural
descriptor at a time.  It uses the frozen raw CIF dataset and never accesses
Pipeline result files.  Both tracks may use the same frozen raw CSV and
descriptor registry, but each writes only to its own results directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import descriptors as descriptor_module
import numpy as np
import pandas as pd

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    SEARCHABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.featurizer import load_structure_from_cif, resolve_cif_path
from run_config import config_get


AGENT_RESULTS_ROOT = Path("results") / "agent"
FROZEN_IDENTITY_COLUMNS = (
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
)

AGENT_RESULT_COLUMNS = [
    "run_id",
    "descriptor_name",
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
    "source_rows",
    "target_rows",
    "finite_structural_values",
    "analysis_rows",
    "descriptor_failure_count",
    "raw_spearman",
    "rank_corr_of_linear_residuals",
    "status",
]


class AgentContractError(ValueError):
    """Raised when the Agent track would violate its isolated contract."""


@dataclass(frozen=True)
class FrozenInputIdentity:
    """Canonical identity of the raw data and registry used by both tracks."""

    raw_file: Path
    descriptor_registry: Path
    registry_revision: str


def _resolve_run_info_relative_path(value: str | Path, run_info: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (run_info.resolve().parent / path).resolve()


def resolve_frozen_input_identity(
    config: dict[str, Any], run_info: Path
) -> FrozenInputIdentity:
    """Validate and canonicalize the single input batch shared by both tracks."""
    if config_get(config, "shared_input.frozen") is not True:
        raise AgentContractError("shared_input.frozen must be true")

    declared_raw = _resolve_run_info_relative_path(
        config_get(config, "data.raw_file"), run_info
    )
    frozen_raw = _resolve_run_info_relative_path(
        config_get(config, "shared_input.raw_file"), run_info
    )
    if declared_raw != frozen_raw:
        raise AgentContractError(
            "data.raw_file and shared_input.raw_file must resolve to the same frozen CSV"
        )

    registry_value = str(config_get(config, "shared_input.descriptor_registry")).strip()
    registry_revision = str(config_get(config, "shared_input.registry_revision")).strip()
    if not registry_value or not registry_revision:
        raise AgentContractError(
            "shared_input.descriptor_registry and shared_input.registry_revision are required"
        )
    configured_registry = _resolve_run_info_relative_path(registry_value, run_info)
    if not configured_registry.exists():
        raise AgentContractError(
            f"shared_input.descriptor_registry does not exist: {configured_registry}"
        )
    actual_registry = Path(descriptor_module.__file__).resolve()
    if configured_registry != actual_registry:
        raise AgentContractError(
            "shared_input.descriptor_registry must resolve to the active "
            f"descriptors module ({actual_registry}), got {configured_registry}"
        )
    return FrozenInputIdentity(
        raw_file=frozen_raw,
        descriptor_registry=actual_registry,
        registry_revision=registry_revision,
    )


def _identity_from_mapping(metrics: dict[str, Any]) -> FrozenInputIdentity:
    missing = [
        column
        for column in FROZEN_IDENTITY_COLUMNS
        if pd.isna(metrics.get(column)) or not str(metrics.get(column, "")).strip()
    ]
    if missing:
        raise AgentContractError(
            f"Agent metrics are missing frozen batch identity values: {missing}"
        )
    return FrozenInputIdentity(
        raw_file=Path(str(metrics["shared_raw_file"])).resolve(),
        descriptor_registry=Path(str(metrics["descriptor_registry"])).resolve(),
        registry_revision=str(metrics["registry_revision"]).strip(),
    )


def validate_agent_result_frame_identity(
    frame: pd.DataFrame,
    identity: FrozenInputIdentity,
    *,
    source: str | Path,
) -> None:
    """Reject a TSV containing missing, mixed, or foreign frozen identities."""
    missing_columns = set(FROZEN_IDENTITY_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise AgentContractError(
            f"{source} is missing frozen batch identity columns: {sorted(missing_columns)}"
        )
    if frame.empty:
        return

    expected = {
        "shared_raw_file": str(identity.raw_file),
        "descriptor_registry": str(identity.descriptor_registry),
        "registry_revision": identity.registry_revision,
    }
    for column, expected_value in expected.items():
        raw_values = frame[column]
        normalized = raw_values.map(
            lambda value: None
            if pd.isna(value) or not str(value).strip()
            else str(value).strip()
        )
        if normalized.isna().any():
            raise AgentContractError(
                f"{source} has missing frozen batch identity values in {column}"
            )
        values = set(normalized.tolist())
        if len(values) != 1 or values != {expected_value}:
            raise AgentContractError(
                f"{source} frozen batch identity mismatch for {column}: "
                f"expected {expected_value!r}, found {sorted(values)!r}"
            )


def validate_agent_artifact_batch(
    metrics: dict[str, Any], artifact_file: str | Path
) -> Path:
    """Validate any existing Agent artifact before it can be overwritten."""
    path = validate_agent_output_path(artifact_file)
    identity = _identity_from_mapping(metrics)
    if path.exists():
        separator = "\t" if path.suffix.lower() == ".tsv" else ","
        existing = pd.read_csv(path, sep=separator)
        validate_agent_result_frame_identity(existing, identity, source=path)
    return path


def validate_agent_result_batch(
    metrics: dict[str, Any], results_file: str | Path
) -> Path:
    """Validate the Agent results TSV before any Agent artifact is written."""
    return validate_agent_artifact_batch(metrics, results_file)


def validate_agent_audit_batch(
    metrics: dict[str, Any], audit_file: str | Path
) -> Path:
    """Validate the Agent audit CSV before it can overwrite another batch."""
    return validate_agent_artifact_batch(metrics, audit_file)


def validate_agent_output_path(value: str | Path) -> Path:
    """Return a relative ``results/agent`` path or reject cross-track output.

    Restricting paths at the boundary prevents an Agent command from writing
    into ``results/pipeline`` (or an arbitrary external path) by accident.
    """
    path = Path(value)
    expected_prefix = AGENT_RESULTS_ROOT.parts
    if (
        path.is_absolute()
        or path.parts[: len(expected_prefix)] != expected_prefix
        or ".." in path.parts
    ):
        raise AgentContractError(
            "Agent artifacts must be relative paths under results/agent/; "
            f"got {path}"
        )
    return path


def _validate_structural_descriptor_name(descriptor_name: str) -> None:
    if descriptor_name not in AVAILABLE_STRUCTURE_DESCRIPTORS:
        available = ", ".join(sorted(SEARCHABLE_STRUCTURE_DESCRIPTORS))
        raise KeyError(
            f"Unknown structural descriptor '{descriptor_name}'. "
            f"Active descriptors: {available}"
        )
    if descriptor_name not in SEARCHABLE_STRUCTURE_DESCRIPTORS:
        alias_of = STRUCTURE_DESCRIPTOR_METADATA.get(descriptor_name, {}).get("alias_of")
        detail = f"; use {alias_of} instead" if alias_of else ""
        raise ValueError(
            f"Structural descriptor '{descriptor_name}' is inactive for Agent search{detail}."
        )


def validate_structural_columns(
    frame: pd.DataFrame,
    *,
    target_column: str,
    structure_column: str,
    system_column: str,
    anion_column: str,
) -> None:
    """Fail before featurization if the raw structural contract is incomplete."""
    required = {
        "target": target_column,
        "structure": structure_column,
        "system": system_column,
        "anion": anion_column,
    }
    missing = [f"{role}={column}" for role, column in required.items() if column not in frame]
    if missing:
        raise ValueError("Raw structural CSV is missing required columns: " + ", ".join(missing))


def load_and_featurize_structural_frame(
    raw_file: str | Path,
    *,
    descriptor_name: str,
    target_column: str,
    structure_column: str,
    system_column: str,
    anion_column: str,
) -> pd.DataFrame:
    """Load raw data, strictly preflight CIFs, and compute one descriptor.

    All paths are resolved relative to the raw CSV.  Every CIF must both exist
    and parse before any Agent output is created.  Individual descriptor
    failures are retained as missing values for audit, but an all-missing
    descriptor is rejected later by :func:`evaluate_structural_frame`.
    """
    _validate_structural_descriptor_name(descriptor_name)
    raw_path = Path(raw_file)
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw structural CSV: {raw_path}")

    frame = pd.read_csv(raw_path)
    validate_structural_columns(
        frame,
        target_column=target_column,
        structure_column=structure_column,
        system_column=system_column,
        anion_column=anion_column,
    )

    csv_dir = raw_path.resolve().parent
    resolved_paths: list[Path | None] = []
    missing: list[tuple[object, Path | None]] = []
    for index, value in frame[structure_column].items():
        if pd.isna(value):
            resolved_paths.append(None)
            missing.append((index, None))
            continue
        resolved = resolve_cif_path(str(value), csv_dir)
        resolved_paths.append(resolved)
        if not resolved.exists():
            missing.append((index, resolved))

    if missing:
        preview = ", ".join(
            f"row {index}: {path if path is not None else '<empty>'}"
            for index, path in missing[:3]
        )
        suffix = f", ... and {len(missing) - 3} more" if len(missing) > 3 else ""
        raise FileNotFoundError(
            f"CIF preflight failed: {len(missing)} missing path(s); {preview}{suffix}"
        )

    structures = []
    parse_failures: list[tuple[object, Path, str]] = []
    for index, path in zip(frame.index, resolved_paths):
        assert path is not None
        try:
            structures.append(load_structure_from_cif(path))
        except ValueError as exc:
            parse_failures.append((index, path, str(exc)))

    if parse_failures:
        preview = "; ".join(
            f"row {index}: {path} ({message})"
            for index, path, message in parse_failures[:2]
        )
        suffix = f"; ... and {len(parse_failures) - 2} more" if len(parse_failures) > 2 else ""
        raise ValueError(
            f"CIF structural preflight failed: {len(parse_failures)} unparsable file(s); "
            f"{preview}{suffix}"
        )

    descriptor_fn, _family, _high_risk = AVAILABLE_STRUCTURE_DESCRIPTORS[descriptor_name]
    values: list[float] = []
    descriptor_failures: list[tuple[object, str]] = []
    for index, structure in zip(frame.index, structures):
        try:
            value = float(descriptor_fn(structure))
            values.append(value if np.isfinite(value) else float("nan"))
        except Exception as exc:  # Descriptor implementations are audited below.
            values.append(float("nan"))
            descriptor_failures.append((index, str(exc)))

    result = frame.copy()
    result[descriptor_name] = values
    result["_resolved_cif_path"] = [str(path) for path in resolved_paths]
    result.attrs["descriptor_failures"] = descriptor_failures
    return result


def evaluate_structural_frame(
    frame: pd.DataFrame,
    *,
    descriptor_name: str,
    target_column: str,
    system_column: str,
    anion_column: str,
    ridge_alpha: float,
) -> dict[str, Any]:
    """Evaluate one structural descriptor with shared deconfounding."""
    _validate_structural_descriptor_name(descriptor_name)
    validate_structural_columns(
        frame,
        target_column=target_column,
        structure_column="_resolved_cif_path" if "_resolved_cif_path" in frame else "cif_path",
        system_column=system_column,
        anion_column=anion_column,
    )
    if descriptor_name not in frame:
        raise ValueError(f"Missing computed structural descriptor column: {descriptor_name}")

    y_full = pd.to_numeric(frame[target_column], errors="coerce").to_numpy(dtype=float)
    x_full = pd.to_numeric(frame[descriptor_name], errors="coerce").to_numpy(dtype=float)
    target_mask = np.isfinite(y_full)
    finite_structural_mask = np.isfinite(x_full)
    analysis_mask = target_mask & finite_structural_mask
    if int(target_mask.sum()) < 5:
        raise ValueError("At least five finite target values are required for structural evaluation.")
    if int(finite_structural_mask.sum()) < 5:
        raise ValueError(
            "No valid structural descriptor values are available for reliable evaluation; "
            "the descriptor is all-NaN or has fewer than five finite values."
        )
    if int(analysis_mask.sum()) < 5:
        raise ValueError(
            "Fewer than five rows contain both target and structural descriptor values."
        )

    system_labels = frame[system_column].astype(str).tolist()
    anion_labels = frame[anion_column].astype(str).tolist()
    feature_df = frame[[descriptor_name]].copy()
    deconfound = DeconfoundAnalyzer(alpha=ridge_alpha).analyze_all(
        feature_df, y_full, system_labels, anion_labels
    )
    if deconfound.empty:
        raise ValueError(
            f"Deconfounding produced no valid result for structural descriptor '{descriptor_name}'."
        )
    deconf_row = deconfound.iloc[0].to_dict()

    failures = frame.attrs.get("descriptor_failures", [])
    return {
        "descriptor_name": descriptor_name,
        "source_rows": int(len(frame)),
        "target_rows": int(target_mask.sum()),
        "finite_structural_values": int(finite_structural_mask.sum()),
        "analysis_rows": int(analysis_mask.sum()),
        "descriptor_failure_count": int(len(failures)),
        "raw_spearman": float(deconf_row["raw_spearman"]),
        "rank_corr_of_linear_residuals": float(deconf_row["rank_corr_of_linear_residuals"]),
    }


def prepare_structural_evaluation(args: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Execute strict raw-CIF loading followed by one-descriptor evaluation."""
    frame = load_and_featurize_structural_frame(
        args.raw_file,
        descriptor_name=args.descriptor_name,
        target_column=args.target_column,
        structure_column=args.structure_column,
        system_column=args.system_column,
        anion_column=args.anion_column,
    )
    metrics = evaluate_structural_frame(
        frame,
        descriptor_name=args.descriptor_name,
        target_column=args.target_column,
        system_column=args.system_column,
        anion_column=args.anion_column,
        ridge_alpha=float(args.ridge_alpha),
    )
    # Persist the frozen batch identity with both emitted Agent artifacts.
    frame = frame.copy()
    frame["shared_raw_file"] = str(args.raw_file)
    frame["descriptor_registry"] = str(args.descriptor_registry)
    frame["registry_revision"] = str(args.registry_revision)
    metrics.update(
        {
            "shared_raw_file": str(args.raw_file),
            "descriptor_registry": str(args.descriptor_registry),
            "registry_revision": str(args.registry_revision),
        }
    )
    return frame, metrics


def evaluate_structural_descriptor(args: Any) -> dict[str, Any]:
    """Public evaluator used by the Agent CLI and regression tests."""
    _frame, metrics = prepare_structural_evaluation(args)
    return metrics


def write_agent_result(
    metrics: dict[str, Any],
    *,
    results_file: str | Path,
    run_id: str,
    status: str,
) -> Path:
    """Append one evaluated descriptor row inside ``results/agent`` only."""
    row = {column: metrics.get(column, float("nan")) for column in AGENT_RESULT_COLUMNS}
    row["run_id"] = run_id
    row["status"] = status
    path = validate_agent_result_batch(row, results_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row], columns=AGENT_RESULT_COLUMNS).to_csv(
        path,
        sep="\t",
        index=False,
        mode="a" if path.exists() else "w",
        header=not path.exists(),
    )
    return path


def write_structural_audit(
    frame: pd.DataFrame,
    *,
    descriptor_name: str,
    audit_file: str | Path,
    metrics: dict[str, Any],
) -> Path:
    """Write only the structural inputs and computed value for reproducibility."""
    path = validate_agent_audit_batch(metrics, audit_file)
    preferred_columns = [
        "material_id",
        "cif_path",
        "_resolved_cif_path",
        "shared_raw_file",
        "descriptor_registry",
        "registry_revision",
        "system",
        "anion_type",
        "log_sigma",
        descriptor_name,
    ]
    columns = [column for column in preferred_columns if column in frame.columns]
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.loc[:, columns].to_csv(path, index=False)
    return path


def format_agent_metrics(metrics: dict[str, Any]) -> list[str]:
    """Return concise, explicit structural metrics for both Agent entry points."""
    return [
        f"descriptor_name:             {metrics['descriptor_name']}",
        f"source_rows:                 {metrics['source_rows']}",
        f"finite_structural_values:    {metrics['finite_structural_values']}",
        f"analysis_rows:               {metrics['analysis_rows']}",
        f"raw_spearman:                {metrics['raw_spearman']:.6f}",
        f"rank_corr_of_linear_residuals: {metrics['rank_corr_of_linear_residuals']:.6f}",
    ]
