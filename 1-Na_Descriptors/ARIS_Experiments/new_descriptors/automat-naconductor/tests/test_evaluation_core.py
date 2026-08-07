from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

import descriptors
from descriptors.combination import CombinationValidator
from descriptors.cv_strategies import MultiStrategyCV
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.featurizer import build_feature_matrix
from descriptors.stability import PhysicalGrouper, StabilitySelector
from run_pipeline import runStage1, runStage2, runStage4


def _balanced_cv_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.RandomState(7)
    systems = np.repeat(["NASICON", "sulfide", "halide"], 4)
    anions = np.tile(["O", "S"], 6)
    X = rng.normal(size=(12, 2))
    X[1, 0] = np.nan
    y = np.nan_to_num(X[:, 0], nan=0.0) + 0.1 * rng.normal(size=12)
    return X, y, systems, anions


def test_repeated_subsample_honours_repeat_fraction_and_seed() -> None:
    X, y, systems, _anions = _balanced_cv_data()

    first = MultiStrategyCV().repeated_subsample(
        X, y, systems, n_repeats=4, test_fraction=0.25, seed=19
    )
    second = MultiStrategyCV().repeated_subsample(
        X, y, systems, n_repeats=4, test_fraction=0.25, seed=19
    )

    assert len(first["fold_results"]) == 4
    assert all(len(fold["val_idx"]) == 3 for fold in first["fold_results"])
    assert [fold["val_idx"].tolist() for fold in first["fold_results"]] == [
        fold["val_idx"].tolist() for fold in second["fold_results"]
    ]
    assert first["n_repeats"] == 4
    assert first["test_fraction"] == pytest.approx(0.25)
    assert first["seed"] == 19


def test_repeated_subsample_explicitly_skips_infeasible_stratification() -> None:
    X = np.arange(12, dtype=float).reshape(6, 2)
    y = np.arange(6, dtype=float)
    systems = np.array(["A", "A", "B", "B", "C", "C"])

    result = MultiStrategyCV().repeated_subsample(
        X, y, systems, n_repeats=4, test_fraction=0.2, seed=19
    )

    assert result["skipped"] is True
    assert result["fold_results"] == []
    assert "test_fraction" in result["reason"]
    assert np.isnan(result["mean_spearman"])


def test_cv_model_pipeline_imputes_and_scales_inside_each_fold() -> None:
    X, y, systems, anions = _balanced_cv_data()
    cv = MultiStrategyCV()

    model = cv._make_model()
    results = cv.run_all(X, y, systems, anions)

    assert isinstance(model, Pipeline)
    assert list(model.named_steps) == ["imputer", "scale", "ridge"]
    assert all(result["fold_results"] for result in results.values())


def test_rare_anion_class_is_reported_as_skipped() -> None:
    X = np.arange(18, dtype=float).reshape(9, 2)
    y = np.arange(9, dtype=float)
    anions = np.array(["Cl"] * 8 + ["I"])

    result = MultiStrategyCV().anion_stratified_cv(X, y, anions, n_folds=3)

    assert result["skipped"] is True
    assert result["fold_results"] == []
    assert np.isnan(result["mean_spearman"])
    assert np.isnan(result["mean_mae"])
    assert "fewer than two" in result["reason"]
    assert result["requested_n_folds"] == 3
    assert result["effective_n_folds"] == 0


def test_anion_cv_reports_when_requested_folds_are_downshifted() -> None:
    X = np.arange(24, dtype=float).reshape(12, 2)
    y = np.arange(12, dtype=float)
    anions = np.repeat(["Cl", "I", "O"], 4)

    result = MultiStrategyCV().anion_stratified_cv(X, y, anions, n_folds=6)

    assert result["skipped"] is False
    assert result["requested_n_folds"] == 6
    assert result["effective_n_folds"] == 4
    assert result["downshifted"] is True
    assert len(result["fold_results"]) == 4


def test_build_feature_matrix_retains_raw_values_and_missingness() -> None:
    raw = pd.DataFrame(
        {
            "log_sigma": [-5.0, -4.0, -3.0, -2.0],
            "system": ["NASICON", "NASICON", "sulfide", "halide"],
            "anion_type": ["O", "O", "S", "Cl"],
            "a2_max_dist": [1.0, 2.0, np.nan, 100.0],
        }
    )

    feature_df, valid_cols, _noise_info = build_feature_matrix(
        raw, n_noise=2, noise_seed=23, min_valid_fraction=0.5
    )

    assert valid_cols == ["a2_max_dist"]
    np.testing.assert_allclose(
        feature_df["a2_max_dist"].to_numpy(),
        raw["a2_max_dist"].to_numpy(),
        equal_nan=True,
    )
    expected_noise = np.random.RandomState(23).randn(4, 2)
    np.testing.assert_allclose(
        feature_df[["noise_000", "noise_001"]].to_numpy(), expected_noise
    )


def test_grouped_deconfounding_records_rank_and_anion_redundancy() -> None:
    systems = ["NASICON"] * 4 + ["sulfide"] * 4 + ["halide"] * 4
    anions = ["O"] * 4 + ["S"] * 4 + ["Cl", "I", "Cl", "I"]
    y = np.linspace(-5.0, -1.0, 12)
    feature_df = pd.DataFrame({"a2_max_dist": y + 0.1})

    result = DeconfoundAnalyzer().analyze_all(feature_df, y, systems, anions)

    assert result.attrs["primary_control"] == "system"
    assert result.attrs["system_design_rank"] == 3
    assert result.attrs["confounder_rank"] == 4
    assert result.attrs["anion_incremental_rank"] == 1
    assert result.attrs["anion_redundant_count"] == 2
    assert result.attrs["anion_is_independent_control"] is False
    assert result.attrs["residualization_columns"] == [
        "system_halide",
        "system_sulfide",
        "anion_type_I",
    ]


def test_stability_selection_uses_subsample_local_lasso_and_exposes_metadata() -> None:
    rng = np.random.RandomState(5)
    signal = rng.normal(size=80)
    nuisance = rng.normal(size=80)
    X_real = np.column_stack([signal, nuisance])
    X_real[::9, 0] = np.nan
    y = 3.0 * signal + 0.1 * rng.normal(size=80)
    X_noise = rng.normal(size=(80, 5))

    result = StabilitySelector(
        n_bootstrap=40,
        threshold=0.6,
        fraction=0.65,
        alpha=0.05,
        seed=11,
    ).run(
        X_real,
        y,
        X_noise,
        real_col_names=["signal", "nuisance"],
        noise_col_names=[f"noise_{i}" for i in range(5)],
    )

    assert result.attrs["selection_method"] == "subsampled_lasso"
    assert result.attrs["selection_alpha"] == pytest.approx(0.05)
    assert result.attrs["preprocessing"] == ["median_imputation", "standard_scaling"]
    assert result.attrs["noise_baseline"] >= 0.0
    assert set(["selection_method", "selection_alpha", "noise_baseline"]).issubset(
        result.columns
    )
    assert result.set_index("feature_name").loc["signal", "selection_freq"] > 0.8


def test_physical_grouper_ranks_by_absolute_rho_but_retains_sign() -> None:
    stability = pd.DataFrame(
        {
            "feature_name": ["negative", "positive"],
            "selection_freq": [0.9, 0.9],
            "is_stable": [True, True],
            "above_noise_baseline": [True, True],
        }
    )
    deconfound = pd.DataFrame(
        {
            "descriptor": ["negative", "positive"],
            "deconfounded_spearman": [-0.8, 0.5],
        }
    )
    registry = {
        "negative": (lambda _x: 0.0, "A", False),
        "positive": (lambda _x: 0.0, "A", False),
    }

    result = PhysicalGrouper(max_per_family=1).group_and_select(
        stability, deconfound, descriptor_registry=registry
    )

    representative = result[result["is_representative"]].iloc[0]
    assert representative["descriptor"] == "negative"
    assert representative["deconfounded_spearman"] == pytest.approx(-0.8)


def test_stage1_returns_full_audit_and_prefiltered_results(tmp_path) -> None:
    n = 18
    y = np.linspace(-6.0, -1.0, n)
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": y,
            "na_concentration": np.random.RandomState(3).normal(size=n),
        }
    )
    systems = ["NASICON"] * 6 + ["sulfide"] * 6 + ["halide"] * 6
    anions = ["O"] * 6 + ["S"] * 6 + ["Cl", "I"] * 3

    full, filtered = runStage1(
        feature_df, y, systems, anions, alpha=1.0, output_dir=tmp_path
    )

    assert set(filtered["descriptor"]).issubset(set(full["descriptor"]))
    assert len(full) == 2
    assert (tmp_path / "stage1_deconfound_results.csv").exists()
    assert full.attrs["primary_control"] == "system"


def test_stage2_receives_only_prefiltered_real_features_plus_fixed_noise(tmp_path) -> None:
    rng = np.random.RandomState(13)
    n = 30
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": rng.normal(size=n),
            "na_concentration": rng.normal(size=n),
            "noise_000": rng.normal(size=n),
            "noise_001": rng.normal(size=n),
        }
    )
    filtered = pd.DataFrame(
        {
            "descriptor": ["a2_max_dist"],
            "deconfounded_spearman": [0.7],
        }
    )

    runStage2(feature_df, feature_df["a2_max_dist"].to_numpy(), filtered, 0.05, 7, tmp_path)
    stability = pd.read_csv(tmp_path / "stage2_stability_results.csv")

    assert stability["feature_name"].tolist() == ["a2_max_dist"]
    assert "na_concentration" not in stability["feature_name"].tolist()


def test_empty_stage1_and_stage2_results_keep_schemas_and_attrs(tmp_path) -> None:
    n = 12
    feature_df = pd.DataFrame(
        {
            "material_id": [f"m{i}" for i in range(n)],
            "noise_000": np.random.RandomState(21).normal(size=n),
        }
    )
    y = np.linspace(-5.0, -1.0, n)
    systems = ["NASICON"] * 4 + ["sulfide"] * 4 + ["halide"] * 4
    anions = ["O"] * 4 + ["S"] * 4 + ["Cl", "I", "Cl", "I"]

    full, filtered = runStage1(
        feature_df, y, systems, anions, alpha=1.0, output_dir=tmp_path
    )
    representatives = runStage2(
        feature_df, y, filtered, alpha=0.05, seed=7, output_dir=tmp_path
    )

    expected_audit_columns = {
        "descriptor",
        "family",
        "is_high_risk",
        "raw_spearman",
        "deconfounded_spearman",
        "deconf_p",
        "system_proxy_ratio",
        "label",
    }
    assert full.empty and filtered.empty
    assert set(full.columns) == expected_audit_columns
    assert set(filtered.columns) == expected_audit_columns
    assert full.attrs["primary_control"] == "system"
    assert filtered.attrs == full.attrs
    assert representatives.empty
    assert "is_representative" in representatives.columns
    assert representatives.attrs["primary_control"] == "system"
    assert pd.read_csv(tmp_path / "stage1_deconfound_results.csv").empty
    assert pd.read_csv(tmp_path / "stage1_prefiltered_results.csv").empty
    assert pd.read_csv(tmp_path / "stage2_representatives.csv").empty


def test_physical_grouper_empty_result_is_schema_stable_and_preserves_attrs() -> None:
    stability = pd.DataFrame(
        columns=[
            "feature_name",
            "selection_freq",
            "is_stable",
            "above_noise_baseline",
        ]
    )
    stability.attrs["selection_method"] = "subsampled_lasso"
    deconfound = pd.DataFrame(
        columns=["descriptor", "deconfounded_spearman"]
    )
    deconfound.attrs["primary_control"] = "system"

    result = PhysicalGrouper().group_and_select(stability, deconfound)

    assert result.empty
    assert {
        "descriptor",
        "family",
        "family_name",
        "deconfounded_spearman",
        "selection_freq",
        "is_stable",
        "above_noise_baseline",
        "is_representative",
    }.issubset(result.columns)
    assert result.attrs["selection_method"] == "subsampled_lasso"
    assert result.attrs["primary_control"] == "system"


def test_stability_selector_with_no_features_returns_metadata_rich_empty_result() -> None:
    y = np.linspace(-2.0, 2.0, 10)

    result = StabilitySelector(n_bootstrap=5, alpha=0.05).run(
        np.empty((10, 0)),
        y,
        real_col_names=[],
    )

    assert result.empty
    assert {
        "feature_name",
        "selection_freq",
        "is_stable",
        "above_noise_baseline",
        "selection_method",
        "selection_alpha",
        "noise_baseline",
    }.issubset(result.columns)
    assert result.attrs["selection_method"] == "subsampled_lasso"
    assert result.attrs["noise_baseline"] == pytest.approx(0.0)


def _skipped_anion_evaluation_data():
    n = 30
    x = np.linspace(-2.0, 2.0, n)
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": x,
            "na_concentration": 0.5 * x + 0.2,
        }
    )
    y = 1.5 * x + 0.1 * np.sin(np.arange(n))
    systems = ["NASICON"] * 10 + ["sulfide"] * 10 + ["halide"] * 10
    anions = ["I"] + ["Cl"] * (n - 1)
    candidates = pd.DataFrame(
        [{
            "combined_name": "a2_max_dist + na_concentration",
            "d1": "a2_max_dist",
            "d2": "na_concentration",
            "operator": "+",
            "combined_deconf_spearman": 0.8,
        }]
    )
    return feature_df, y, systems, anions, candidates


def test_combination_validation_scores_only_available_cv_strategies() -> None:
    feature_df, y, systems, anions, candidates = _skipped_anion_evaluation_data()

    result = CombinationValidator().validate(
        feature_df, y, systems, anions, candidates, top_k=1
    )
    row = result.iloc[0]

    assert bool(row["anion_stratified_skipped"]) is True
    assert "fewer than two" in row["anion_stratified_skip_reason"]
    assert np.isnan(row["anion_stratified_spearman"])
    assert bool(row["loso_skipped"]) is False
    assert bool(row["repeated_subsample_skipped"]) is False
    assert row["composite_strategy_count"] == 2
    assert bool(row["composite_is_complete"]) is False
    assert np.isfinite(row["composite_score"])


def test_stage4_baseline_records_skipped_anion_and_finite_partial_composite(tmp_path) -> None:
    feature_df, y, systems, anions, candidates = _skipped_anion_evaluation_data()
    deconfound = pd.DataFrame(
        [{
            "descriptor": "a2_max_dist",
            "family": "A",
            "deconfounded_spearman": 0.8,
        }]
    )

    validation, baseline = runStage4(
        feature_df,
        y,
        systems,
        anions,
        deconfound,
        candidates,
        alpha=1.0,
        seed=42,
        top_k=1,
        output_dir=tmp_path,
    )

    assert bool(validation.iloc[0]["anion_stratified_skipped"]) is True
    assert np.isfinite(validation.iloc[0]["composite_score"])
    assert bool(baseline.iloc[0]["anion_stratified_skipped"]) is True
    assert baseline.iloc[0]["composite_strategy_count"] == 2
    assert bool(baseline.iloc[0]["composite_is_complete"]) is False
    assert np.isfinite(baseline.iloc[0]["composite_score"])


def test_cli_fails_closed_when_featurized_artifact_has_no_valid_descriptors(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pd.DataFrame(
        {
            "material_id": [f"m{i}" for i in range(6)],
            "system": ["NASICON", "NASICON", "sulfide", "sulfide", "halide", "halide"],
            "anion_type": ["O", "O", "S", "S", "Cl", "I"],
            "log_sigma": np.linspace(-5.0, -1.0, 6),
            "a2_max_dist": [np.nan] * 6,
        }
    ).to_csv(data_dir / "naconductor_featurized.csv", index=False)
    run_info = tmp_path / "run_info.yaml"
    run_info.write_text(
        f"""data:
  raw_file: data/naconductor_raw.csv
  featurized_file: data/naconductor_featurized.csv
  target_column: log_sigma
  structure_column: cif_path
  system_column: system
  anion_type_column: anion_type
shared_input:
  frozen: true
  raw_file: data/naconductor_raw.csv
  descriptor_registry: {Path(descriptors.__file__).resolve()}
  registry_revision: test-registry
tracks:
  pipeline:
    output_dir: results/pipeline
combination:
  max_descriptors: 3
""",
        encoding="utf-8",
    )
    output_dir = tmp_path / "results" / "pipeline"
    script = Path(__file__).resolve().parents[1] / "run_pipeline.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--skip-featurize",
            "--run-info",
            str(run_info),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    diagnostic = f"{completed.stdout}\n{completed.stderr}".lower()

    assert completed.returncode != 0
    assert "no valid structural descriptor values are available" in diagnostic
    assert "regenerate" in diagnostic and "valid cif" in diagnostic
    assert not output_dir.exists()
