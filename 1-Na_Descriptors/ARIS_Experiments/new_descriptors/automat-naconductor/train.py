"""Evaluate one explicit CIF-derived descriptor in the independent Agent track.

This is intentionally not a train/validation/test-split runner.  It reads the
frozen raw structural CSV, performs strict CIF preflight, and evaluates one
registered descriptor using the shared fold-local Ridge CV and rank-aware
deconfounding implementations.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from automat_utils import (
    AgentContractError,
    format_agent_metrics,
    prepare_structural_evaluation,
    resolve_frozen_input_identity,
    validate_agent_output_path,
    validate_agent_audit_batch,
    validate_agent_result_batch,
    write_agent_result,
    write_structural_audit,
)
from run_config import DEFAULT_RUN_INFO, config_get, load_run_info


def parse_agent_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the explicit structural Agent contract without legacy defaults."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one registered CIF-derived descriptor in the isolated "
            "Agent track (results/agent only)."
        )
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=DEFAULT_RUN_INFO,
        help="YAML file with frozen shared inputs and Agent-track settings.",
    )
    parser.add_argument(
        "--descriptor-name",
        required=True,
        help="Explicit key from descriptors.AVAILABLE_STRUCTURE_DESCRIPTORS.",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        default=None,
        help="Agent result TSV under results/agent/.",
    )
    parser.add_argument(
        "--audit-file",
        type=Path,
        default=None,
        help="Agent structural audit CSV under results/agent/.",
    )
    parser.add_argument(
        "--run-id",
        default="manual",
        help="Opaque Agent iteration identifier recorded in results.tsv.",
    )
    parser.add_argument(
        "--status",
        choices=("evaluated", "keep", "discard", "crash"),
        default="evaluated",
        help="Human-reviewed iteration status; defaults to evaluated.",
    )
    args = parser.parse_args(argv)

    config = load_run_info(args.run_info)
    args.run_config = config
    try:
        args.frozen_identity = resolve_frozen_input_identity(config, args.run_info)
        args.raw_file = args.frozen_identity.raw_file
        args.descriptor_registry = args.frozen_identity.descriptor_registry
        args.registry_revision = args.frozen_identity.registry_revision
        args.structure_column = config_get(config, "data.structure_column")
        args.target_column = config_get(config, "data.target_column")
        args.system_column = config_get(config, "data.system_column")
        args.anion_column = config_get(config, "data.anion_type_column")
        args.ridge_alpha = float(config_get(config, "evaluation.model.alpha"))
        args.results_file = validate_agent_output_path(
            args.results_file or config_get(config, "tracks.agent.results_file")
        )
        args.audit_file = validate_agent_output_path(
            args.audit_file or config_get(config, "tracks.agent.feature_cache_file")
        )
    except (AgentContractError, KeyError, ValueError) as exc:
        parser.error(str(exc))
    return args


def evaluate_descriptor(args: argparse.Namespace) -> dict[str, Any]:
    """Compatibility-named entry point for the structural Agent evaluator."""
    _frame, metrics = prepare_structural_evaluation(args)
    return metrics


def main(argv: list[str] | None = None) -> None:
    args = parse_agent_args(argv)
    try:
        frame, metrics = prepare_structural_evaluation(args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

    try:
        # This preflight must precede the audit write; a conflicting TSV must
        # never overwrite the current batch's audit artifact.
        validate_agent_result_batch(metrics, args.results_file)
        validate_agent_audit_batch(metrics, args.audit_file)
        audit_path = write_structural_audit(
            frame,
            descriptor_name=args.descriptor_name,
            audit_file=args.audit_file,
            metrics=metrics,
        )
        results_path = write_agent_result(
            metrics,
            results_file=args.results_file,
            run_id=str(args.run_id),
            status=str(args.status),
        )
    except AgentContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    for line in format_agent_metrics(metrics):
        print(line)
    print(f"structural_audit_file:      {audit_path}")
    print(f"agent_results_file:         {results_path}")
    print("track_isolation:             agent writes results/agent only; no pipeline output read")


if __name__ == "__main__":
    main()
