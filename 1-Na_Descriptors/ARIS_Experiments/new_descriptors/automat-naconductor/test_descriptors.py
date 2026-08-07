"""Compatibility entry point for a strict structural descriptor audit.

This compatibility-named command audits one explicit descriptor against the
frozen raw CIF dataset and writes only an Agent-track audit CSV.  It does not
read or write Pipeline results.
"""
from __future__ import annotations

import sys
from typing import Any

from automat_utils import format_agent_metrics, prepare_structural_evaluation, write_structural_audit
from train import parse_agent_args


def parse_audit_args(argv: list[str] | None = None):
    """Use the same explicit descriptor/CIF contract as ``train.py``."""
    return parse_agent_args(argv)


def run_structural_audit(args: Any) -> tuple[dict[str, Any], str]:
    """Return metrics and write the reproducible descriptor-value audit."""
    frame, metrics = prepare_structural_evaluation(args)
    audit_path = write_structural_audit(
        frame,
        descriptor_name=args.descriptor_name,
        audit_file=args.audit_file,
        metrics=metrics,
    )
    return metrics, str(audit_path)


def main(argv: list[str] | None = None) -> None:
    args = parse_audit_args(argv)
    try:
        metrics, audit_path = run_structural_audit(args)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None

    print("Structural audit (not a held-out test split)")
    for line in format_agent_metrics(metrics):
        print(line)
    print(f"structural_audit_file:      {audit_path}")
    print("track_isolation:             agent writes results/agent only; no pipeline output read")


if __name__ == "__main__":
    main()
