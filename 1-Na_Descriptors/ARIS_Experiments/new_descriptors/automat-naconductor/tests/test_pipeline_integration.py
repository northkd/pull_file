"""End-to-end regressions for the in-memory Stage 1--4 Pipeline contract.

The checked-in raw dataset deliberately cannot be used here: its CIF paths are
absent, and the production CLI must fail before it writes results.  This test
therefore constructs the *post-Stage-0* numeric contract in memory and confines
all Stage 1--4 artifacts to pytest's temporary ``results/pipeline`` directory.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import descriptors
from descriptors.stability import PhysicalGrouper
from run_pipeline import runStage1, runStage2, runStage3, runStage4


def _synthetic_stage0_contract() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, list[str], list[str]]:
    """Return raw metadata and raw-valued structural features for integration.

    All eight physical families are represented.  Two independent A-family
    features are intentionally stable, so a three-descriptor Pipeline run must
    retain both and can construct the plan-approved A/A/B triple even when
    every family has a primary representative.
    """
    rng = np.random.RandomState(914)
    n_samples = 120
    descriptor_names = [
        "a2_max_dist",          # A
        "mean_bond_length",     # A
        "avg_na_neighbors",     # B
        "na_concentration",     # C
        "interstitial_count",   # D_prime
        "framework_bond_rigidity",  # E
        "nana_nana_angle_mean", # F
        "na_x_en_diff",         # G
        "wyckoff_diversity",    # H
    ]
    components = rng.normal(size=(n_samples, len(descriptor_names)))
    y = components @ np.array([1.30, 1.25, 1.20, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90])
    y += 0.02 * rng.normal(size=n_samples)

    systems = np.repeat(["NASICON", "sulfide", "halide"], 40).tolist()
    # One iodide intentionally makes anion-stratified CV infeasible.  LOSO and
    # repeated system-stratified subsampling remain feasible and must survive.
    anions = ["oxide"] * 40 + ["sulfide"] * 40 + ["chloride"] * 39 + ["iodide"]
    raw_df = pd.DataFrame(
        {
            "material_id": [f"synthetic-{index:03d}" for index in range(n_samples)],
            "system": systems,
            "anion_type": anions,
            "log_sigma": y,
            **{
                name: components[:, index] + 10.0
                for index, name in enumerate(descriptor_names)
            },
        }
    )
    feature_df = raw_df[descriptor_names].copy()
    feature_df["noise_000"] = rng.normal(size=n_samples)
    feature_df["noise_001"] = rng.normal(size=n_samples)
    return raw_df, feature_df, y, systems, anions


def test_in_memory_stages_preserve_triple_provenance_and_explicit_cv_skips(tmp_path) -> None:
    """Run Stages 1--4, including CSV round trips, without any CIF dependency."""
    raw_df, feature_df, y, systems, anions = _synthetic_stage0_contract()
    output_dir = tmp_path / "results" / "pipeline"
    output_dir.mkdir(parents=True)

    full_deconfound, filtered_deconfound = runStage1(
        feature_df, y, systems, anions, alpha=1.0, output_dir=output_dir
    )
    assert len(full_deconfound) == 9
    assert len(filtered_deconfound) == 9
    assert raw_df["log_sigma"].tolist() == list(y)

    representatives = runStage2(
        feature_df,
        y,
        filtered_deconfound,
        alpha=0.01,
        seed=31,
        output_dir=output_dir,
        max_descriptors=3,
    )
    selected = representatives.loc[representatives["is_representative"]]
    assert set(selected.loc[selected["family"] == "A", "descriptor"]) == {
        "a2_max_dist",
        "mean_bond_length",
    }
    assert "avg_na_neighbors" in selected["descriptor"].tolist()

    candidates = runStage3(
        feature_df,
        y,
        systems,
        anions,
        representatives,
        alpha=1.0,
        seed=31,
        output_dir=output_dir,
        max_descriptors=3,
    )
    assert (candidates["n_components"] == 3).any()

    stage3_csv = pd.read_csv(output_dir / "stage3_combination_candidates.csv")
    triple_csv = stage3_csv.loc[stage3_csv["n_components"] == 3].head(1)
    assert len(triple_csv) == 1
    triple_components = json.loads(triple_csv.iloc[0]["components"])
    triple_operators = json.loads(triple_csv.iloc[0]["operators"])
    triple_provenance = json.loads(triple_csv.iloc[0]["formula_provenance"])
    assert len(triple_components) == 3
    assert len(triple_operators) == 2
    assert triple_provenance["components"] == triple_components
    assert triple_provenance["operators"] == triple_operators

    validation, baseline = runStage4(
        feature_df,
        y,
        systems,
        anions,
        filtered_deconfound,
        triple_csv,
        alpha=1.0,
        seed=31,
        top_k=1,
        output_dir=output_dir,
    )
    assert validation.iloc[0]["n_components"] == 3
    assert validation.iloc[0]["components"] == triple_components
    assert bool(validation.iloc[0]["anion_stratified_skipped"]) is True
    assert "fewer than two" in validation.iloc[0]["anion_stratified_skip_reason"]
    assert bool(validation.iloc[0]["loso_skipped"]) is False
    assert bool(validation.iloc[0]["repeated_subsample_skipped"]) is False
    assert bool(baseline.iloc[0]["anion_stratified_skipped"]) is True

    stage4_csv = pd.read_csv(output_dir / "stage4_validation_results.csv")
    stage4_row = stage4_csv.iloc[0]
    assert json.loads(stage4_row["components"]) == triple_components
    assert json.loads(stage4_row["formula_provenance"])["components"] == triple_components
    evidence_blocks = json.loads(stage4_row["evidence_blocks"])
    assert set(evidence_blocks) == {
        "noise_baseline",
        "factor_spanning",
        "per_system",
        "bootstrap_ci",
    }
    for name in evidence_blocks:
        assert evidence_blocks[name]["status"] == "exploratory"
        assert isinstance(evidence_blocks[name]["available"], bool)
        assert json.loads(stage4_row[name])["status"] == "exploratory"


def test_cli_missing_cif_fails_closed_with_a_clean_diagnostic(tmp_path) -> None:
    """A Stage-0 missing-CIF error must not create Pipeline artifacts or a traceback."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(
        {
            "material_id": ["synthetic-missing-cif"],
            "cif_path": ["missing.cif"],
            "system": ["NASICON"],
            "anion_type": ["oxide"],
            "log_sigma": [-3.0],
        }
    ).to_csv(data_dir / "raw.csv", index=False)
    run_info = tmp_path / "run_info.yaml"
    run_info.write_text(
        f"""data:
  raw_file: data/raw.csv
  featurized_file: data/features.csv
  target_column: log_sigma
  structure_column: cif_path
  system_column: system
  anion_type_column: anion_type
shared_input:
  frozen: true
  raw_file: data/raw.csv
  descriptor_registry: {Path(descriptors.__file__).resolve()}
  registry_revision: integration-test-registry
tracks:
  pipeline:
    output_dir: results/pipeline
combination:
  max_descriptors: 3
""",
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "run_pipeline.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--run-info", str(run_info)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    diagnostic = f"{completed.stdout}\n{completed.stderr}".lower()

    assert completed.returncode == 2
    assert "error: cif preflight failed" in diagnostic
    assert "traceback" not in diagnostic
    assert not (tmp_path / "results" / "pipeline").exists()


def test_stage2_family_capacity_is_a_hard_upper_bound() -> None:
    """A missing family must not expand the three-descriptor candidate pool."""
    names = ["a_0", "a_1", "a_2", "a_3", "b_0"]
    stability = pd.DataFrame(
        {
            "feature_name": names,
            "selection_freq": [1.0] * len(names),
            "is_stable": [True] * len(names),
            "above_noise_baseline": [True] * len(names),
        }
    )
    deconfound = pd.DataFrame(
        {
            "descriptor": names,
            "deconfounded_spearman": [0.9, 0.8, 0.7, 0.6, 0.5],
        }
    )
    registry = {
        name: (lambda _structure: 0.0, "A" if name.startswith("a_") else "B", False)
        for name in names
    }

    selected = PhysicalGrouper(max_per_family=2).group_and_select(
        stability, deconfound, descriptor_registry=registry
    )
    selected_counts = selected.loc[selected["is_representative"]].groupby("family").size()

    assert selected_counts.max() == 2
    assert selected_counts.loc["A"] == 2
