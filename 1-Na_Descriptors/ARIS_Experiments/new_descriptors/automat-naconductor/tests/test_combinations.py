from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from descriptors import STRUCTURE_DESCRIPTOR_METADATA
from descriptors.combination import CombinationValidator, ConstrainedCombinationSearch
from run_pipeline import runStage3, runStage4


EXPECTED_COMBINATION_RESULT_COLUMNS = [
    "combined_name",
    "d1",
    "d2",
    "operator",
    "components",
    "operators",
    "component_families",
    "n_components",
    "d1_family",
    "d2_family",
    "is_cross_family",
    "combined_raw_spearman",
    "combined_deconf_spearman",
    "n_valid",
    "raw_value_source",
    "formula_provenance",
]


def _representatives(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "descriptor": descriptor,
                "family": family,
                "is_representative": True,
            }
            for descriptor, family in rows
        ]
    )


def _search_inputs() -> tuple[pd.DataFrame, np.ndarray, list[str], list[str]]:
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": [2.0, 2.2, 2.4, 2.7, 3.0, 3.2, 3.5, 3.8, 4.0],
            "mean_bond_length": [1.5, 1.6, 1.8, 2.0, 2.1, 2.4, 2.5, 2.7, 2.9],
            "na_concentration": [0.0, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            "avg_na_neighbors": [1.0, 1.4, 1.7, 2.0, 2.2, 2.5, 2.8, 3.0, 3.2],
        }
    )
    y = np.linspace(-5.0, -1.0, len(feature_df))
    systems = ["s1"] * 3 + ["s2"] * 3 + ["s3"] * 3
    anions = ["O", "S", "Cl"] * 3
    return feature_df, y, systems, anions


def test_registry_exposes_search_metadata_and_inactive_compatibility_names() -> None:
    for metadata in STRUCTURE_DESCRIPTOR_METADATA.values():
        assert {"unit", "dimension", "active_for_search", "searchable"} <= set(metadata)

    assert STRUCTURE_DESCRIPTOR_METADATA["max_bond_length"]["alias_of"] == "a2_max_dist"
    assert STRUCTURE_DESCRIPTOR_METADATA["max_bond_length"]["active_for_search"] is False
    assert STRUCTURE_DESCRIPTOR_METADATA["bottleneck_anisotropy"]["active_for_search"] is False
    assert STRUCTURE_DESCRIPTOR_METADATA["bvse_barrier_estimate"]["active_for_search"] is False


def test_commutative_pairs_are_not_duplicated() -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives([("a2_max_dist", "A"), ("mean_bond_length", "A")])

    result = ConstrainedCombinationSearch().search(
        feature_df, y, systems, anions, reps, max_descriptors=2
    )
    names = result["combined_name"].tolist()

    assert names.count("(a2_max_dist + mean_bond_length)") == 1
    assert "(mean_bond_length + a2_max_dist)" not in names
    assert names.count("(a2_max_dist × mean_bond_length)") == 1
    assert "(mean_bond_length × a2_max_dist)" not in names


def test_ratio_uses_raw_physical_values_and_rejects_zero_denominator() -> None:
    numerator = np.array([2.0, 4.0, 8.0])
    denominator = np.array([1.0, 0.0, 4.0])

    result = ConstrainedCombinationSearch._generateCombinedFeature(
        numerator, denominator, "ratio"
    )

    assert np.allclose(result[[0, 2]], np.array([2.0, 2.0]))
    assert np.isnan(result[1])


def test_explicit_rules_allow_physical_ratio_and_forbid_arbitrary_ratio() -> None:
    assert ConstrainedCombinationSearch._getAllowedOperators("A", "C") == ["ratio"]
    assert "ratio" not in ConstrainedCombinationSearch._getAllowedOperators("A", "B")
    assert ConstrainedCombinationSearch._getAllowedOperators("C", "A") == []
    assert ConstrainedCombinationSearch._getAllowedOperators("B", "E") == []


def test_search_ratio_is_computed_from_raw_physical_values() -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives([("a2_max_dist", "A"), ("na_concentration", "C")])

    result = ConstrainedCombinationSearch().search(
        feature_df, y, systems, anions, reps, max_descriptors=2
    )
    ratio = result.loc[result["operator"] == "ratio"].iloc[0]

    assert ratio["raw_value_source"] == "feature_df"
    assert ratio["n_valid"] == 8
    assert ratio["formula_provenance"]["components"] == [
        "a2_max_dist",
        "na_concentration",
    ]
    assert ratio["formula_provenance"]["operators"] == ["ratio"]


def test_triples_are_bounded_and_follow_two_plus_adjacent_family_plan() -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives(
        [
            ("a2_max_dist", "A"),
            ("mean_bond_length", "A"),
            ("avg_na_neighbors", "B"),
            ("na_concentration", "C"),
        ]
    )

    result = ConstrainedCombinationSearch().search(
        feature_df, y, systems, anions, reps, max_descriptors=3
    )
    triples = result.loc[result["n_components"] == 3]

    assert not triples.empty
    assert result["n_components"].max() == 3
    for components, families in zip(triples["components"], triples["component_families"]):
        assert len(components) == 3
        counts = pd.Series(families).value_counts().sort_values().tolist()
        assert counts == [1, 2]
        repeated_family = pd.Series(families).value_counts().idxmax()
        adjacent_family = pd.Series(families).value_counts().idxmin()
        assert (
            ConstrainedCombinationSearch._getAllowedOperators(
                repeated_family, adjacent_family
            )
            or ConstrainedCombinationSearch._getAllowedOperators(
                adjacent_family, repeated_family
            )
        )


def test_triple_addition_rejects_incompatible_result_dimension() -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives(
        [
            ("a2_max_dist", "A"),
            ("mean_bond_length", "A"),
            ("avg_na_neighbors", "B"),
        ]
    )

    result = ConstrainedCombinationSearch().search(
        feature_df, y, systems, anions, reps, max_descriptors=3
    )
    triples = result.loc[result["n_components"] == 3]

    assert not any(operators == ["+", "+"] for operators in triples["operators"])


def test_empty_search_has_stable_schema() -> None:
    feature_df, y, systems, anions = _search_inputs()
    result = ConstrainedCombinationSearch().search(
        feature_df,
        y,
        systems,
        anions,
        _representatives([]),
        max_descriptors=3,
    )

    assert result.empty
    assert result.columns.tolist() == EXPECTED_COMBINATION_RESULT_COLUMNS


def test_stage3_csv_round_trip_preserves_triple_formula_for_validation(tmp_path) -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives(
        [
            ("a2_max_dist", "A"),
            ("mean_bond_length", "A"),
            ("avg_na_neighbors", "B"),
        ]
    )

    runStage3(
        feature_df,
        y,
        systems,
        anions,
        reps,
        alpha=1.0,
        seed=13,
        output_dir=tmp_path,
    )
    reloaded = pd.read_csv(tmp_path / "stage3_combination_candidates.csv")
    triple = reloaded.loc[reloaded["n_components"] == 3].head(1)

    assert not triple.empty
    validation = CombinationValidator(seed=13).validate(
        feature_df,
        y,
        systems,
        anions,
        triple,
        top_k=1,
        n_bootstrap=10,
    )
    assert validation.iloc[0]["n_components"] == 3
    assert validation.iloc[0]["components"] == json.loads(triple.iloc[0]["components"])
    assert validation.iloc[0]["formula_provenance"]["components"] == validation.iloc[0][
        "components"
    ]
    assert len(validation.iloc[0]["operators"]) == 2
    assert len(validation.iloc[0]["component_families"]) == 3
    assert len(validation.iloc[0]["formula_provenance"]["rules"]) == 2


def test_stage3_respects_configured_two_descriptor_limit(tmp_path) -> None:
    feature_df, y, systems, anions = _search_inputs()
    reps = _representatives(
        [
            ("a2_max_dist", "A"),
            ("mean_bond_length", "A"),
            ("avg_na_neighbors", "B"),
        ]
    )

    result = runStage3(
        feature_df,
        y,
        systems,
        anions,
        reps,
        alpha=1.0,
        seed=13,
        output_dir=tmp_path,
        max_descriptors=2,
    )

    assert not result.empty
    assert result["n_components"].max() == 2


@pytest.mark.parametrize(
    ("components", "operators"),
    [
        ("['a2_max_dist', 'mean_bond_length']", '["multiply"]'),
        ('["a2_max_dist", 3]', '["multiply"]'),
        ('["a2_max_dist", "mean_bond_length", "avg_na_neighbors"]', '["multiply"]'),
    ],
)
def test_serialized_formula_fields_are_strictly_validated(
    components: str,
    operators: str,
) -> None:
    feature_df, y, systems, anions = _search_inputs()
    candidate = {
        "combined_name": "invalid",
        "d1": "a2_max_dist",
        "d2": "mean_bond_length",
        "operator": "multiply",
        "components": components,
        "operators": operators,
    }

    with pytest.raises(ValueError, match="formula"):
        CombinationValidator().full_validation(
            feature_df, y, systems, anions, candidate, n_bootstrap=5
        )


def test_full_validation_has_four_named_exploratory_evidence_blocks() -> None:
    feature_df, y, systems, anions = _search_inputs()
    candidate = {
        "combined_name": "(a2_max_dist / na_concentration)",
        "d1": "a2_max_dist",
        "d2": "na_concentration",
        "operator": "ratio",
        "components": ["a2_max_dist", "na_concentration"],
        "operators": ["ratio"],
        "combined_deconf_spearman": 0.7,
    }

    result = CombinationValidator(seed=11).full_validation(
        feature_df, y, systems, anions, candidate, n_bootstrap=40
    )

    assert {"noise_baseline", "factor_spanning", "per_system", "bootstrap_ci"} <= set(result)
    assert result["status"] == "exploratory"
    assert result["causal_claim"] is False
    assert result["uncertainty"]["method"] == "system_stratified_bootstrap"
    assert result["bootstrap_ci"]["n_requested"] == 40
    assert "cv_diagnostics" in result
    for key in ("noise_baseline", "factor_spanning", "per_system", "bootstrap_ci"):
        assert result[key]["status"] == "exploratory"
    v2 = result["factor_spanning"]
    assert v2["method"] == "fold_safe_oof_target_residual_prediction"
    assert "oof_residual_target_vs_formula_prediction_spearman" in v2
    assert v2["n_oof_samples"] <= len(y)
    assert v2["n_folds_available"] <= v2["n_folds_requested"]
    assert v2["causal_claim"] is False
    assert "supplementary_partial_association" in v2


def test_factor_spanning_uses_rank_aware_system_primary_controls() -> None:
    n = 18
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": np.linspace(2.0, 4.0, n),
            "mean_bond_length": np.linspace(1.0, 2.0, n),
        }
    )
    y = np.linspace(-5.0, -1.0, n)
    systems = ["s1"] * 6 + ["s2"] * 6 + ["s3"] * 6
    # Anion is perfectly redundant with system in this fixture.
    anions = ["O"] * 6 + ["S"] * 6 + ["Cl"] * 6
    candidate = {
        "d1": "a2_max_dist",
        "d2": "mean_bond_length",
        "operator": "multiply",
    }

    block = CombinationValidator(seed=3).full_validation(
        feature_df, y, systems, anions, candidate, n_bootstrap=10
    )["factor_spanning"]

    assert block["primary_control"] == "system"
    assert block["anion_incremental_rank"] == 0
    assert block["anion_redundant_count"] == 2
    assert all(name.startswith("system_") for name in block["residualization_columns"])


def test_cv_keeps_formula_missing_values_for_fold_local_imputation() -> None:
    n = 30
    denominator = np.linspace(0.1, 1.0, n)
    denominator[4] = 0.0
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": np.linspace(2.0, 4.0, n),
            "na_concentration": denominator,
        }
    )
    y = np.linspace(-5.0, -1.0, n)
    systems = ["s1"] * 10 + ["s2"] * 10 + ["s3"] * 10
    anions = ["O", "S", "Cl"] * 10
    candidate = {
        "d1": "a2_max_dist",
        "d2": "na_concentration",
        "operator": "ratio",
    }

    result = CombinationValidator(seed=5).full_validation(
        feature_df, y, systems, anions, candidate, n_bootstrap=10
    )
    class_counts = result["cv_diagnostics"]["strategies"][
        "anion_stratified_cv"
    ]["class_counts"]

    assert sum(class_counts.values()) == n
    assert result["cv_diagnostics"]["n_target_observed"] == n
    assert result["cv_diagnostics"]["n_formula_observed"] == n - 1


def test_small_group_cv_is_reported_as_skipped_instead_of_available() -> None:
    n = 12
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": np.linspace(2.0, 4.0, n),
            "mean_bond_length": np.linspace(1.0, 2.0, n),
        }
    )
    candidate = {
        "d1": "a2_max_dist",
        "d2": "mean_bond_length",
        "operator": "multiply",
    }

    result = CombinationValidator(seed=5).full_validation(
        feature_df,
        np.linspace(-5.0, -1.0, n),
        ["only-system"] * n,
        ["O", "S"] * (n // 2),
        candidate,
        n_bootstrap=10,
    )
    summary = result["cv_diagnostics"]["summary"]

    assert bool(summary["loso_skipped"]) is True
    assert bool(summary["loso_available"]) is False
    assert "two system" in summary["loso_skip_reason"]
    assert bool(summary["anion_stratified_skipped"]) is False


def test_validate_flattens_evidence_without_losing_cv_skip_semantics() -> None:
    n = 30
    x = np.linspace(-2.0, 2.0, n)
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": x,
            "mean_bond_length": 0.5 * x + 3.0,
        }
    )
    y = 1.5 * x + 0.1 * np.sin(np.arange(n))
    systems = ["s1"] * 10 + ["s2"] * 10 + ["s3"] * 10
    anions = ["I"] + ["Cl"] * (len(y) - 1)
    candidates = pd.DataFrame(
        [
            {
                "combined_name": "(a2_max_dist × mean_bond_length)",
                "d1": "a2_max_dist",
                "d2": "mean_bond_length",
                "operator": "multiply",
                "components": ["a2_max_dist", "mean_bond_length"],
                "operators": ["multiply"],
                "combined_deconf_spearman": 0.8,
            }
        ]
    )

    row = CombinationValidator(seed=7).validate(
        feature_df, y, systems, anions, candidates, top_k=1, n_bootstrap=20
    ).iloc[0]

    assert bool(row["anion_stratified_skipped"]) is True
    assert row["composite_strategy_count"] == 2
    assert bool(row["composite_is_complete"]) is False
    assert row["validation_status"] == "exploratory"
    assert row["uncertainty_method"] == "system_stratified_bootstrap"
    assert isinstance(row["evidence_blocks"], dict)
    assert set(row["evidence_blocks"]) == {
        "noise_baseline",
        "factor_spanning",
        "per_system",
        "bootstrap_ci",
    }
    assert row["components"] == ["a2_max_dist", "mean_bond_length"]
    assert row["operators"] == ["multiply"]
    assert row["formula_provenance"]["raw_value_source"] == "feature_df"


def test_stage4_csv_persists_v2_rank_metadata_as_json(tmp_path) -> None:
    n = 30
    x = np.linspace(-2.0, 2.0, n)
    feature_df = pd.DataFrame(
        {
            "a2_max_dist": x,
            "mean_bond_length": 0.5 * x + 3.0,
        }
    )
    y = 1.5 * x + 0.1 * np.sin(np.arange(n))
    systems = ["s1"] * 10 + ["s2"] * 10 + ["s3"] * 10
    anions = ["O"] * 10 + ["S"] * 10 + ["Cl"] * 10
    candidates = pd.DataFrame(
        [
            {
                "combined_name": "(a2_max_dist × mean_bond_length)",
                "d1": "a2_max_dist",
                "d2": "mean_bond_length",
                "operator": "multiply",
                "components": ["a2_max_dist", "mean_bond_length"],
                "operators": ["multiply"],
                "component_families": ["A", "A"],
                "n_components": 2,
                "raw_value_source": "feature_df",
                "combined_deconf_spearman": 0.8,
            }
        ]
    )
    deconfound = pd.DataFrame(
        [
            {
                "descriptor": "a2_max_dist",
                "family": "A",
                "deconfounded_spearman": 0.8,
            }
        ]
    )

    runStage4(
        feature_df,
        y,
        systems,
        anions,
        deconfound,
        candidates,
        alpha=1.0,
        seed=9,
        top_k=1,
        output_dir=tmp_path,
    )
    saved = pd.read_csv(tmp_path / "stage4_validation_results.csv").iloc[0]
    v2 = json.loads(saved["factor_spanning"])

    assert v2["primary_control"] == "system"
    assert v2["anion_incremental_rank"] == 0
    assert len(v2["anion_redundant_columns"]) == 2
    assert v2["method"] == "fold_safe_oof_target_residual_prediction"
