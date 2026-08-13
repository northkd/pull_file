#!/usr/bin/env python
"""Plot the isolated Agent track's structural evaluation history."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-cache"))

import matplotlib.pyplot as plt
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
from run_status import resolve_results_file


REQUIRED_AGENT_PLOT_COLUMNS = {
    "descriptor_name",
    "raw_spearman",
    "rank_corr_of_linear_residuals",
    "status",
    "shared_raw_file",
    "descriptor_registry",
    "registry_revision",
}
STATUS_COLORS = {
    "evaluated": "#64748B",
    "keep": "#15803D",
    "discard": "#DC2626",
    "crash": "#111827",
}


def _optional_config_get(config: dict, dotted_path: str, default: str) -> str:
    try:
        return str(config_get(config, dotted_path))
    except KeyError:
        return default


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot Agent structural metrics from results/agent only; pipeline "
            "outputs are not accepted as inputs."
        )
    )
    parser.add_argument("--run-info", type=Path, default=DEFAULT_RUN_INFO)
    parser.add_argument("--results-file", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    config = load_run_info(args.run_info)
    default_output = _optional_config_get(
        config, "tracks.agent.figure_file", "results/agent/figures/metric_history.png"
    )
    try:
        args.frozen_identity = resolve_frozen_input_identity(config, args.run_info)
        args.results_file = validate_agent_output_path(
            args.results_file or resolve_results_file(config)
        )
        args.output = validate_agent_output_path(args.output or default_output)
    except AgentContractError as exc:
        parser.error(str(exc))
    return args


def read_agent_results(path: Path, identity: FrozenInputIdentity) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing Agent results file: {path}")
    frame = pd.read_csv(path, sep="\t")
    missing = REQUIRED_AGENT_PLOT_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing Agent metric columns: {sorted(missing)}")
    validate_agent_result_frame_identity(frame, identity, source=path)
    frame = frame.copy()
    frame["raw_spearman"] = pd.to_numeric(frame["raw_spearman"], errors="coerce")
    frame["rank_corr_of_linear_residuals"] = pd.to_numeric(
        frame["rank_corr_of_linear_residuals"], errors="coerce"
    )
    frame["status"] = frame["status"].astype(str).str.strip().str.lower()
    frame["iteration"] = np.arange(1, len(frame) + 1)
    finite_abs = frame["rank_corr_of_linear_residuals"].abs()
    frame["best_abs_rank_corr_of_linear_residuals"] = finite_abs.cummax()
    return frame


def plot_metric_history(ax: plt.Axes, results: pd.DataFrame) -> None:
    ax.plot(
        results["iteration"],
        results["raw_spearman"],
        color="#94A3B8",
        linewidth=1.4,
        marker="o",
        markersize=4,
        label="raw Spearman",
        zorder=1,
    )
    ax.plot(
        results["iteration"],
        results["rank_corr_of_linear_residuals"],
        color="#2563EB",
        linewidth=2.1,
        marker="o",
        markersize=4.5,
        label="rank corr of linear residuals",
        zorder=2,
    )
    ax.step(
        results["iteration"],
        results["best_abs_rank_corr_of_linear_residuals"],
        color="#7C3AED",
        linewidth=1.5,
        linestyle="--",
        where="post",
        label="best |rank corr of linear residuals|",
        zorder=1,
    )
    for status, rows in results.groupby("status", sort=False):
        ax.scatter(
            rows["iteration"],
            rows["rank_corr_of_linear_residuals"],
            color=STATUS_COLORS.get(status, "#475569"),
            s=45,
            edgecolors="white",
            linewidths=0.8,
            label=f"status: {status}",
            zorder=3,
        )
    ax.axhline(0.0, color="#CBD5E1", linewidth=0.8, zorder=0)
    ax.set_xlabel("Agent evaluation iteration")
    ax.set_ylabel("Spearman rho")
    ax.set_title("Structural descriptor evidence (Agent track only)")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, ncols=2)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    results = read_agent_results(args.results_file, args.frozen_identity)
    if results.empty:
        raise ValueError("Agent results file has no evaluated rows to plot.")

    fig, ax = plt.subplots(figsize=(10.5, 5.8), constrained_layout=True)
    plot_metric_history(ax, results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=250)
    plt.close(fig)
    print(f"Saved Agent-only structural metric history to {args.output}")


if __name__ == "__main__":
    main()
