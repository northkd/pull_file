"""Stopping decision for the isolated structural Agent track."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from automat_utils import (
    AgentContractError,
    FrozenInputIdentity,
    resolve_frozen_input_identity,
    validate_agent_output_path,
    validate_agent_result_frame_identity,
)
from run_config import DEFAULT_RUN_INFO, config_get, load_run_info


REQUIRED_AGENT_RESULT_COLUMNS = {
    "descriptor_name",
    "rank_corr_of_linear_residuals",
    "status",
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
}
METRIC_STATUSES = {"evaluated", "keep", "discard"}


def resolve_results_file(config: dict[str, Any]) -> Path:
    """Resolve the only results file the Agent status command may inspect."""
    return validate_agent_output_path(config_get(config, "tracks.agent.results_file"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect structural Agent results and apply its deconfounded-Spearman "
            "stopping policy. Pipeline outputs are never read."
        )
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=DEFAULT_RUN_INFO,
        help="YAML file containing tracks.agent.status settings.",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        default=None,
        help="Optional Agent TSV override under results/agent/.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only STOP or CONTINUE.",
    )
    args = parser.parse_args(argv)
    if args.results_file is not None:
        try:
            args.results_file = validate_agent_output_path(args.results_file)
        except AgentContractError as exc:
            parser.error(str(exc))
    return args


def parse_metric(value: str | None) -> float:
    if value is None:
        return float("nan")
    try:
        return float(value.strip())
    except (AttributeError, ValueError):
        return float("nan")


def read_results(
    path: Path, identity: FrozenInputIdentity
) -> list[dict[str, str]]:
    if not path.exists():
        return []
    frame = pd.read_csv(path, sep="\t")
    missing = REQUIRED_AGENT_RESULT_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(
            f"Agent results file {path} is missing required columns: {sorted(missing)}"
        )
    validate_agent_result_frame_identity(frame, identity, source=path)
    return frame.fillna("").astype(str).to_dict(orient="records")


def count_since_last_improvement(
    rows: list[dict[str, str]], metric_name: str
) -> tuple[int, float, int]:
    """Count finite completed evaluations since a strict metric improvement."""
    best_value = -float("inf")
    since_improvement = 0
    metric_observations = 0
    for row in rows:
        if row.get("status", "").strip().lower() not in METRIC_STATUSES:
            continue
        value = parse_metric(row.get(metric_name))
        if not np.isfinite(value):
            continue
        metric_observations += 1
        if value > best_value:
            best_value = value
            since_improvement = 0
        else:
            since_improvement += 1
    return since_improvement, best_value, metric_observations


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_run_info(args.run_info)
    results_file = args.results_file or resolve_results_file(config)
    identity = resolve_frozen_input_identity(config, args.run_info)
    status_config = config_get(config, "tracks.agent.status")
    max_iterations = int(status_config["max_iterations"])
    patience = int(status_config["patience"])
    metric_name = str(status_config["primary_metric"])
    if metric_name != "rank_corr_of_linear_residuals":
        raise ValueError(
            "tracks.agent.status.primary_metric must be rank_corr_of_linear_residuals; "
            "Agent stopping is not based on raw correlation or prediction error."
        )

    rows = read_results(results_file, identity)
    iterations = len(rows)
    since_improvement, best_value, metric_observations = count_since_last_improvement(
        rows, metric_name
    )
    max_iterations_reached = max_iterations > 0 and iterations >= max_iterations
    patience_reached = patience > 0 and since_improvement >= patience
    decision = "STOP" if max_iterations_reached or patience_reached else "CONTINUE"

    if not args.quiet:
        best_display = "nan" if not np.isfinite(best_value) else f"{best_value:.6f}"
        print(f"results_file: {results_file}")
        print("track: agent (pipeline results are intentionally excluded)")
        print(f"iterations_recorded: {iterations}")
        print(f"metric_observations: {metric_observations}")
        print(f"primary_metric: {metric_name}")
        print(f"best_rank_corr_of_linear_residuals: {best_display}")
        print(f"finite_evaluations_since_last_improvement: {since_improvement}")
        print(f"max_iterations: {max_iterations}")
        print(f"patience: {patience}")
        print(f"max_iterations_reached: {str(max_iterations_reached).lower()}")
        print(f"patience_reached: {str(patience_reached).lower()}")
    print(decision)


if __name__ == "__main__":
    main()
