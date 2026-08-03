"""Physics-constrained descriptor combination search and validation.

Formula construction is deliberately small and auditable: raw descriptor
values are combined with ``+``, multiplication, or explicitly permitted ratio
directions.  Pair and triple rules live in a declarative registry below, and
every candidate carries the rule and raw-value provenance that admitted it.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from descriptors import (
    AVAILABLE_STRUCTURE_DESCRIPTORS,
    STRUCTURE_DESCRIPTOR_METADATA,
)
from descriptors.cv_strategies import (
    CV_SPEARMAN_SUMMARY_COLUMNS,
    MultiStrategyCV,
    summarize_cv_spearman,
)
from descriptors.deconfound import DeconfoundAnalyzer


# Rules are directional.  Commutative operations are copied in both directions;
# a ratio exists only in the physically named numerator -> denominator direction.
PAIR_OPERATOR_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("A", "B"): ("+", "multiply"),
    ("B", "A"): ("+", "multiply"),
    ("A", "D_prime"): ("multiply",),
    ("D_prime", "A"): ("multiply",),
    ("A", "C"): ("ratio",),
    ("B", "D_prime"): ("+", "multiply"),
    ("D_prime", "B"): ("+", "multiply"),
    ("A", "H"): ("+", "multiply"),
    ("H", "A"): ("+", "multiply"),
    ("E", "A"): ("multiply",),
    ("A", "E"): ("multiply",),
}
SAME_FAMILY_OPERATOR_RULES: dict[str, tuple[str, ...]] = {
    family: ("+", "multiply")
    for family in ("A", "B", "C", "D_prime", "E", "F", "G", "H")
}

COMBINATION_RESULT_COLUMNS = [
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

FORMULA_JSON_COLUMNS = (
    "components",
    "operators",
    "component_families",
    "formula_provenance",
)
VALIDATION_JSON_COLUMNS = (
    *FORMULA_JSON_COLUMNS,
    "noise_baseline",
    "factor_spanning",
    "per_system",
    "bootstrap_ci",
    "evidence_blocks",
    "cv_diagnostics",
)

COMBINATION_VALIDATION_RESULT_COLUMNS = [
    "combined_name",
    "d1",
    "d2",
    "operator",
    "components",
    "operators",
    "component_families",
    "n_components",
    "raw_value_source",
    "formula_provenance",
    "combined_deconf_spearman",
    *CV_SPEARMAN_SUMMARY_COLUMNS,
    "validation_status",
    "causal_claim",
    "uncertainty_method",
    "noise_baseline",
    "factor_spanning",
    "per_system",
    "bootstrap_ci",
    "evidence_blocks",
    "cv_diagnostics",
]


def _safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Return finite-pair Spearman, or NaN for insufficient/constant data."""
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    if int(mask.sum()) < 3:
        return float("nan")
    x_valid = x_arr[mask]
    y_valid = y_arr[mask]
    if np.unique(x_valid).size < 2 or np.unique(y_valid).size < 2:
        return float("nan")
    return float(stats.spearmanr(x_valid, y_valid).statistic)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json_ready(item) for item in list(value)]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    return value


def _containers_to_csv_frame(
    dataframe: pd.DataFrame, columns: Sequence[str]
) -> pd.DataFrame:
    serialised = dataframe.copy()
    for column in columns:
        if column not in serialised.columns:
            continue

        def encode(value: Any) -> Any:
            if isinstance(value, (list, tuple, np.ndarray, Mapping)):
                return json.dumps(
                    _json_ready(value),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            if value is None or (isinstance(value, float) and np.isnan(value)):
                return value
            raise ValueError(
                f"formula field {column!r} must be a list/dict before CSV serialisation"
            )

        serialised[column] = serialised[column].map(encode)
    return serialised


def combination_candidates_to_csv_frame(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe copy with formula containers encoded as strict JSON."""
    return _containers_to_csv_frame(candidates_df, FORMULA_JSON_COLUMNS)


def combination_validation_to_csv_frame(validation_df: pd.DataFrame) -> pd.DataFrame:
    """Return a CSV-safe copy with formula/evidence artifacts encoded as JSON."""
    return _containers_to_csv_frame(validation_df, VALIDATION_JSON_COLUMNS)


class ConstrainedCombinationSearch:
    """Enumerate plan-constrained formulas and rank their raw-value signal."""

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    @staticmethod
    def _getAllowedOperators(family1: str, family2: str) -> list[str]:
        """Return only operators explicitly registered for this direction."""
        if family1 == family2:
            return list(SAME_FAMILY_OPERATOR_RULES.get(family1, ()))
        return list(PAIR_OPERATOR_RULES.get((family1, family2), ()))

    @staticmethod
    def _generateCombinedFeature(
        d1_values: np.ndarray,
        d2_values: np.ndarray,
        operator: str,
    ) -> np.ndarray:
        """Apply one allowed operation without imputation or denominator hacks."""
        d1 = np.asarray(d1_values, dtype=float)
        d2 = np.asarray(d2_values, dtype=float)
        if operator == "+":
            return d1 + d2
        if operator == "multiply":
            return d1 * d2
        if operator == "ratio":
            result = np.full(np.broadcast_shapes(d1.shape, d2.shape), np.nan)
            valid = np.isfinite(d1) & np.isfinite(d2) & (d2 != 0.0)
            np.divide(d1, d2, out=result, where=valid)
            return result
        raise ValueError(f"Unsupported combination operator: {operator}")

    @staticmethod
    def _apply_formula(arrays: Sequence[np.ndarray], operators: Sequence[str]) -> np.ndarray:
        if len(arrays) < 2 or len(operators) != len(arrays) - 1:
            raise ValueError("A formula requires n components and n-1 operators")
        result = np.asarray(arrays[0], dtype=float)
        for values, operator in zip(arrays[1:], operators):
            result = ConstrainedCombinationSearch._generateCombinedFeature(
                result, np.asarray(values, dtype=float), operator
            )
        return result

    @staticmethod
    def _descriptor_dimension(name: str, reps: pd.DataFrame) -> str | None:
        metadata = STRUCTURE_DESCRIPTOR_METADATA.get(name)
        if metadata is not None:
            return str(metadata["dimension"])
        if "dimension" in reps.columns:
            values = reps.loc[reps["descriptor"] == name, "dimension"]
            if not values.empty and pd.notna(values.iloc[0]):
                return str(values.iloc[0])
        return None

    @classmethod
    def _operator_dimensionally_valid(
        cls,
        d1: str,
        d2: str,
        operator: str,
        reps: pd.DataFrame,
    ) -> bool:
        # Addition is only meaningful for equal known dimensions. Unknown custom
        # descriptors remain usable for compatibility with external registries.
        if operator != "+":
            return True
        dim1 = cls._descriptor_dimension(d1, reps)
        dim2 = cls._descriptor_dimension(d2, reps)
        return dim1 is None or dim2 is None or dim1 == dim2

    @classmethod
    def _formula_dimensionally_valid(
        cls,
        components: Sequence[str],
        operators: Sequence[str],
        reps: pd.DataFrame,
    ) -> bool:
        current = cls._descriptor_dimension(components[0], reps)
        for component, operator in zip(components[1:], operators):
            other = cls._descriptor_dimension(component, reps)
            if operator == "+":
                if current is not None and other is not None and current != other:
                    return False
                current = current or other
            elif operator == "multiply":
                current = (
                    f"({current})*({other})"
                    if current is not None and other is not None else None
                )
            elif operator == "ratio":
                current = (
                    "dimensionless"
                    if current is not None and current == other
                    else f"({current})/({other})"
                    if current is not None and other is not None
                    else None
                )
        return True

    @staticmethod
    def _is_active(name: str) -> bool:
        metadata = STRUCTURE_DESCRIPTOR_METADATA.get(name)
        return metadata is None or bool(metadata.get("active_for_search", True))

    def _evaluate_candidate(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        confounders: pd.DataFrame,
        components: list[str],
        families: list[str],
        operators: list[str],
        rule_ids: list[str],
    ) -> dict[str, Any] | None:
        if any(name not in feature_df.columns for name in components):
            return None
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        values = self._apply_formula(arrays, operators)
        valid = np.isfinite(values) & np.isfinite(y)
        n_valid = int(valid.sum())
        if n_valid < 5:
            return None

        raw_rho = _safe_spearman(values[valid], y[valid])
        deconf_rho = DeconfoundAnalyzer(alpha=self.alpha).deconfounded_spearman(
            values[valid],
            y[valid],
            confounders.loc[valid].reset_index(drop=True),
        )
        symbols = {"+": "+", "multiply": "×", "ratio": "/"}
        name = components[0]
        for component, operator in zip(components[1:], operators):
            name = f"({name} {symbols[operator]} {component})"

        provenance = {
            "components": list(components),
            "component_families": list(families),
            "operators": list(operators),
            "rules": list(rule_ids),
            "raw_value_source": "feature_df",
            "missing_value_policy": "mask_nonfinite_and_zero_denominators",
            "standardisation": "finished_formula_only_in_model_fit",
        }
        return {
            "combined_name": name,
            "d1": components[0],
            "d2": components[1],
            "operator": operators[0],
            "components": list(components),
            "operators": list(operators),
            "component_families": list(families),
            "n_components": len(components),
            "d1_family": families[0],
            "d2_family": families[1],
            "is_cross_family": len(set(families)) > 1,
            "combined_raw_spearman": raw_rho,
            "combined_deconf_spearman": float(deconf_rho),
            "n_valid": n_valid,
            "raw_value_source": "feature_df",
            "formula_provenance": provenance,
        }

    def search(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        representative_df: pd.DataFrame,
        max_candidates: int = 150,
        max_descriptors: int = 3,
    ) -> pd.DataFrame:
        """Search explicit pairs and plan-constrained triples from raw columns."""
        if max_descriptors not in (2, 3):
            raise ValueError("max_descriptors must be 2 or 3")
        if representative_df.empty:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        representative_mask = (
            representative_df["is_representative"]
            if "is_representative" in representative_df.columns
            else pd.Series(True, index=representative_df.index)
        )
        reps = representative_df.loc[representative_mask == True].copy()  # noqa: E712
        if reps.empty:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        reps = reps.loc[reps["descriptor"].map(self._is_active)]
        rep_names = list(dict.fromkeys(reps["descriptor"].astype(str).tolist()))
        desc_to_family = dict(zip(reps["descriptor"], reps["family"]))
        for name, (_, family, _) in AVAILABLE_STRUCTURE_DESCRIPTORS.items():
            desc_to_family.setdefault(name, family)

        y_arr = np.asarray(y, dtype=float)
        deconf = DeconfoundAnalyzer(alpha=self.alpha)
        confounders, _control_metadata = deconf.build_rank_aware_controls(
            system_labels, anion_labels
        )
        confounders.index = feature_df.index
        candidates: list[dict[str, Any]] = []

        # Commutative pairs appear once. Ratio direction is emitted only when
        # the exact ordered family rule admits it.
        for d1, d2 in combinations(rep_names, 2):
            f1, f2 = desc_to_family[d1], desc_to_family[d2]
            forward = self._getAllowedOperators(f1, f2)
            reverse = self._getAllowedOperators(f2, f1)
            for operator in ("+", "multiply"):
                if operator not in forward and operator not in reverse:
                    continue
                if not self._operator_dimensionally_valid(d1, d2, operator, reps):
                    continue
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d1, d2],
                    [f1, f2],
                    [operator],
                    [f"pair:{min(f1, f2)}-{max(f1, f2)}:{operator}"],
                )
                if record is not None:
                    candidates.append(record)
            if "ratio" in forward:
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d1, d2],
                    [f1, f2],
                    ["ratio"],
                    [f"directional_ratio:{f1}->{f2}"],
                )
                if record is not None:
                    candidates.append(record)
            if "ratio" in reverse:
                record = self._evaluate_candidate(
                    feature_df,
                    y_arr,
                    confounders,
                    [d2, d1],
                    [f2, f1],
                    ["ratio"],
                    [f"directional_ratio:{f2}->{f1}"],
                )
                if record is not None:
                    candidates.append(record)

        if max_descriptors == 3:
            by_family: dict[str, list[str]] = {}
            for name in rep_names:
                by_family.setdefault(desc_to_family[name], []).append(name)
            for repeated_family, family_names in by_family.items():
                for d1, d2 in combinations(family_names, 2):
                    for adjacent_family, adjacent_names in by_family.items():
                        if adjacent_family == repeated_family:
                            continue
                        cross_ops = self._getAllowedOperators(
                            repeated_family, adjacent_family
                        )
                        if not cross_ops:
                            continue
                        for d3 in adjacent_names:
                            for within_op in SAME_FAMILY_OPERATOR_RULES.get(
                                repeated_family, ()
                            ):
                                if not self._operator_dimensionally_valid(
                                    d1, d2, within_op, reps
                                ):
                                    continue
                                for cross_op in cross_ops:
                                    if not self._formula_dimensionally_valid(
                                        [d1, d2, d3],
                                        [within_op, cross_op],
                                        reps,
                                    ):
                                        continue
                                    record = self._evaluate_candidate(
                                        feature_df,
                                        y_arr,
                                        confounders,
                                        [d1, d2, d3],
                                        [repeated_family, repeated_family, adjacent_family],
                                        [within_op, cross_op],
                                        [
                                            f"triple:two_from:{repeated_family}",
                                            f"triple:adjacent:{repeated_family}->{adjacent_family}:{cross_op}",
                                        ],
                                    )
                                    if record is not None:
                                        candidates.append(record)

        if not candidates:
            return pd.DataFrame(columns=COMBINATION_RESULT_COLUMNS)
        result = pd.DataFrame.from_records(candidates, columns=COMBINATION_RESULT_COLUMNS)
        result = result.sort_values(
            "combined_deconf_spearman",
            key=lambda values: values.abs(),
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)
        return result.head(max_candidates).reset_index(drop=True)


class CombinationValidator:
    """Generate exploratory V1--V4 evidence plus existing CV diagnostics."""

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    @staticmethod
    def _is_missing_field(value: Any) -> bool:
        return value is None or (
            isinstance(value, (float, np.floating)) and np.isnan(value)
        )

    @classmethod
    def _parse_formula_list(cls, value: Any, field: str) -> list[str]:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"formula field {field!r} is not valid JSON"
                ) from exc
        elif isinstance(value, (tuple, np.ndarray)):
            value = list(value)
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item for item in value
        ):
            raise ValueError(f"formula field {field!r} must be a list[str]")
        return list(value)

    @classmethod
    def _parse_formula_provenance(cls, value: Any) -> dict[str, Any] | None:
        if cls._is_missing_field(value):
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError("formula provenance is not valid JSON") from exc
        if not isinstance(value, Mapping):
            raise ValueError("formula provenance must be a JSON object")
        return dict(value)

    @classmethod
    def _candidate_formula(cls, candidate: Mapping[str, Any]) -> tuple[list[str], list[str]]:
        raw_components = candidate.get("components")
        raw_operators = candidate.get("operators")
        components_missing = cls._is_missing_field(raw_components)
        operators_missing = cls._is_missing_field(raw_operators)

        # Backward compatibility is limited to the legacy pair API where both
        # structured fields are genuinely absent. Partially present/corrupt
        # structured formula data is never silently downgraded.
        if components_missing and operators_missing:
            try:
                components = [candidate["d1"], candidate["d2"]]
                operators = [candidate["operator"]]
            except KeyError as exc:
                raise ValueError("legacy formula is missing d1/d2/operator") from exc
            if not all(isinstance(item, str) and item for item in components + operators):
                raise ValueError("legacy formula fields must be non-empty strings")
        elif components_missing or operators_missing:
            raise ValueError(
                "formula components and operators must be provided together"
            )
        else:
            components = cls._parse_formula_list(raw_components, "components")
            operators = cls._parse_formula_list(raw_operators, "operators")

        if not 2 <= len(components) <= 3:
            raise ValueError("formula must contain two or three components")
        if len(operators) != len(components) - 1:
            raise ValueError("formula operator count must equal component count minus one")
        if any(operator not in {"+", "multiply", "ratio"} for operator in operators):
            raise ValueError("formula contains an unsupported operator")

        declared_n = candidate.get("n_components")
        if not cls._is_missing_field(declared_n) and int(declared_n) != len(components):
            raise ValueError("formula n_components is inconsistent with components")
        for key, expected in (
            ("d1", components[0]),
            ("d2", components[1]),
            ("operator", operators[0]),
        ):
            declared = candidate.get(key)
            if not cls._is_missing_field(declared) and declared != expected:
                raise ValueError(f"formula field {key!r} is inconsistent with structured formula")

        provenance = cls._parse_formula_provenance(candidate.get("formula_provenance"))
        if provenance is not None:
            if "components" not in provenance or "operators" not in provenance:
                raise ValueError("formula provenance must contain components and operators")
            provenance_components = cls._parse_formula_list(
                provenance["components"], "formula_provenance.components"
            )
            provenance_operators = cls._parse_formula_list(
                provenance["operators"], "formula_provenance.operators"
            )
            if provenance_components != components or provenance_operators != operators:
                raise ValueError("formula provenance is inconsistent with formula fields")
        return components, operators

    def _formula_values(
        self, feature_df: pd.DataFrame, candidate: Mapping[str, Any]
    ) -> tuple[np.ndarray, list[str], list[str]]:
        components, operators = self._candidate_formula(candidate)
        missing = [name for name in components if name not in feature_df.columns]
        if missing:
            raise KeyError(f"Candidate components absent from feature_df: {missing}")
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        values = ConstrainedCombinationSearch._apply_formula(arrays, operators)
        return values, components, operators

    def _noise_baseline(
        self,
        feature_df: pd.DataFrame,
        candidate: Mapping[str, Any],
        y: np.ndarray,
        system_labels: np.ndarray,
        observed: float,
        n_draws: int = 100,
    ) -> dict[str, Any]:
        components, operators = self._candidate_formula(candidate)
        arrays = [feature_df[name].to_numpy(dtype=float) for name in components]
        rng = np.random.default_rng(self.seed)
        noise_scores: list[float] = []
        for _ in range(n_draws):
            permuted: list[np.ndarray] = []
            for values in arrays:
                shuffled = values.copy()
                for system in np.unique(system_labels):
                    idx = np.flatnonzero(system_labels == system)
                    shuffled[idx] = values[rng.permutation(idx)]
                permuted.append(shuffled)
            noise = ConstrainedCombinationSearch._apply_formula(permuted, operators)
            score = _safe_spearman(noise, y)
            if np.isfinite(score):
                noise_scores.append(abs(score))
        observed_abs = abs(observed) if np.isfinite(observed) else float("nan")
        if not noise_scores:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "no finite matched-noise formula correlations",
                "n_requested": n_draws,
                "n_success": 0,
            }
        noise_arr = np.asarray(noise_scores)
        return {
            "status": "exploratory",
            "available": np.isfinite(observed_abs),
            "reason": None if np.isfinite(observed_abs) else "observed association unavailable",
            "observed_abs_spearman": observed_abs,
            "noise_median_abs_spearman": float(np.median(noise_arr)),
            "noise_95pct_abs_spearman": float(np.quantile(noise_arr, 0.95)),
            "observed_percentile": (
                float(np.mean(noise_arr <= observed_abs))
                if np.isfinite(observed_abs) else float("nan")
            ),
            "n_requested": n_draws,
            "n_success": len(noise_scores),
            "comparison": "matched_formula_within_system_component_permutation",
        }

    def _factor_spanning(
        self,
        values: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        anion_labels: np.ndarray,
    ) -> dict[str, Any]:
        target_mask = np.isfinite(y)
        finite_pair_mask = np.isfinite(values) & target_mask
        if int(target_mask.sum()) < 6 or int(np.isfinite(values[target_mask]).sum()) < 3:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "V2 requires at least six targets and three observed formula values",
                "method": "fold_safe_oof_target_residual_prediction",
                "causal_claim": False,
                "n_oof_samples": 0,
                "n_folds_requested": 0,
                "n_folds_available": 0,
            }
        analyzer = DeconfoundAnalyzer(alpha=self.alpha)
        x_valid, y_valid = values[finite_pair_mask], y[finite_pair_mask]
        system_valid = system_labels[finite_pair_mask]
        anion_valid = anion_labels[finite_pair_mask]
        system_controls = analyzer._one_hot_frame(
            system_valid.tolist(), "system"
        ).reset_index(drop=True)
        all_controls, control_metadata = analyzer.build_rank_aware_controls(
            system_valid.tolist(), anion_valid.tolist()
        )
        system_rho = analyzer.deconfounded_spearman(
            x_valid, y_valid, system_controls
        )
        all_rho = analyzer.deconfounded_spearman(x_valid, y_valid, all_controls)

        values_oof = values[target_mask]
        y_oof = y[target_mask]
        systems_oof = system_labels[target_mask]
        anions_oof = anion_labels[target_mask]
        unique_systems, system_counts = np.unique(systems_oof, return_counts=True)
        if unique_systems.size > 1 and int(system_counts.min()) >= 2:
            n_splits = min(5, int(system_counts.min()))
            splitter = StratifiedKFold(
                n_splits=n_splits, shuffle=True, random_state=self.seed
            )
            split_iter = splitter.split(values_oof, systems_oof)
            split_basis = "system_stratified"
        else:
            n_splits = min(5, len(y_oof))
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=self.seed)
            split_iter = splitter.split(values_oof)
            split_basis = "random_kfold"

        heldout_residuals: list[np.ndarray] = []
        heldout_predictions: list[np.ndarray] = []
        fold_details: list[dict[str, Any]] = []
        for fold, (train_idx, test_idx) in enumerate(split_iter, start=1):
            train_values = values_oof[train_idx]
            if int(np.isfinite(train_values).sum()) < 2:
                fold_details.append({
                    "fold": fold,
                    "status": "skipped",
                    "reason": "fewer than two observed training formula values",
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                })
                continue
            train_controls, fold_control_metadata = analyzer.build_rank_aware_controls(
                systems_oof[train_idx].tolist(), anions_oof[train_idx].tolist()
            )
            selected_columns = list(train_controls.columns)

            def encode_controls(indices: np.ndarray) -> np.ndarray:
                encoded = np.zeros((len(indices), len(selected_columns)), dtype=float)
                for col_idx, column in enumerate(selected_columns):
                    if column.startswith("system_"):
                        category = column[len("system_"):]
                        encoded[:, col_idx] = systems_oof[indices].astype(str) == category
                    elif column.startswith("anion_type_"):
                        category = column[len("anion_type_"):]
                        encoded[:, col_idx] = anions_oof[indices].astype(str) == category
                return encoded

            z_train = train_controls.to_numpy(dtype=float)
            z_test = encode_controls(test_idx)
            if z_train.shape[1]:
                control_model = Ridge(alpha=self.alpha)
                control_model.fit(z_train, y_oof[train_idx])
                train_residual = y_oof[train_idx] - control_model.predict(z_train)
                test_residual = y_oof[test_idx] - control_model.predict(z_test)
            else:
                train_mean = float(np.mean(y_oof[train_idx]))
                train_residual = y_oof[train_idx] - train_mean
                test_residual = y_oof[test_idx] - train_mean

            formula_model = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=self.alpha)),
            ])
            try:
                formula_model.fit(train_values.reshape(-1, 1), train_residual)
                prediction = formula_model.predict(values_oof[test_idx].reshape(-1, 1))
            except ValueError as exc:
                fold_details.append({
                    "fold": fold,
                    "status": "skipped",
                    "reason": str(exc),
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                })
                continue
            heldout_residuals.append(test_residual)
            heldout_predictions.append(prediction)
            fold_details.append({
                "fold": fold,
                "status": "available",
                "n_train": len(train_idx),
                "n_test": len(test_idx),
                "residualization_columns": selected_columns,
                "anion_incremental_rank": fold_control_metadata[
                    "anion_incremental_rank"
                ],
            })

        if heldout_residuals:
            residual_target = np.concatenate(heldout_residuals)
            formula_prediction = np.concatenate(heldout_predictions)
            oof_rho = _safe_spearman(residual_target, formula_prediction)
            n_oof_samples = len(residual_target)
        else:
            oof_rho = float("nan")
            n_oof_samples = 0
        n_folds_available = sum(
            detail["status"] == "available" for detail in fold_details
        )
        available = bool(np.isfinite(oof_rho) and n_folds_available >= 2)
        return {
            "status": "exploratory",
            "available": available,
            "reason": None if available else "insufficient nondegenerate OOF residual evidence",
            "method": "fold_safe_oof_target_residual_prediction",
            "causal_claim": False,
            "oof_residual_target_vs_formula_prediction_spearman": oof_rho,
            "n_oof_samples": n_oof_samples,
            "n_folds_requested": n_splits,
            "n_folds_available": n_folds_available,
            "split_basis": split_basis,
            "folds": fold_details,
            "interpretation": "predictive_association_after_known_factors_not_causal",
            "supplementary_partial_association": {
                "system_primary_spearman": float(system_rho),
                "known_factors_spearman": float(all_rho),
                "n_finite_pairs": int(finite_pair_mask.sum()),
            },
            **control_metadata,
        }

    @staticmethod
    def _per_system(
        values: np.ndarray, y: np.ndarray, system_labels: np.ndarray
    ) -> dict[str, Any]:
        groups: dict[str, dict[str, Any]] = {}
        for system in sorted(np.unique(system_labels).astype(str)):
            mask = (system_labels.astype(str) == system) & np.isfinite(values) & np.isfinite(y)
            n = int(mask.sum())
            rho = _safe_spearman(values[mask], y[mask])
            groups[system] = {
                "n": n,
                "raw_spearman": rho,
                "available": bool(np.isfinite(rho)),
                "reason": None if np.isfinite(rho) else "insufficient or constant within-system data",
            }
        return {
            "status": "exploratory",
            "available": any(group["available"] for group in groups.values()),
            "reason": None if groups else "no system groups",
            "groups": groups,
            "association": "raw_within_system_spearman",
        }

    def _bootstrap_ci(
        self,
        values: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        n_bootstrap: int,
    ) -> dict[str, Any]:
        mask = np.isfinite(values) & np.isfinite(y)
        values_valid, y_valid = values[mask], y[mask]
        systems_valid = system_labels[mask]
        estimate = _safe_spearman(values_valid, y_valid)
        if n_bootstrap < 1 or len(values_valid) < 5:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "bootstrap requires at least five observations and one draw",
                "estimate": estimate,
                "n_requested": int(n_bootstrap),
                "n_success": 0,
                "method": "system_stratified_bootstrap",
            }
        rng = np.random.default_rng(self.seed)
        group_indices = [
            np.flatnonzero(systems_valid == system)
            for system in np.unique(systems_valid)
        ]
        samples: list[float] = []
        for _ in range(n_bootstrap):
            draw = np.concatenate(
                [rng.choice(idx, size=len(idx), replace=True) for idx in group_indices]
            )
            rho = _safe_spearman(values_valid[draw], y_valid[draw])
            if np.isfinite(rho):
                samples.append(rho)
        if not samples:
            return {
                "status": "exploratory",
                "available": False,
                "reason": "all stratified bootstrap draws were degenerate",
                "estimate": estimate,
                "n_requested": int(n_bootstrap),
                "n_success": 0,
                "method": "system_stratified_bootstrap",
            }
        sample_arr = np.asarray(samples)
        return {
            "status": "exploratory",
            "available": True,
            "reason": None,
            "estimate": estimate,
            "ci_lower": float(np.quantile(sample_arr, 0.025)),
            "ci_upper": float(np.quantile(sample_arr, 0.975)),
            "confidence_level": 0.95,
            "n_requested": int(n_bootstrap),
            "n_success": len(samples),
            "method": "system_stratified_bootstrap",
        }

    @staticmethod
    def _unavailable_cv(reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
        raw = {
            key: {
                "strategy": key,
                "skipped": True,
                "reason": reason,
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
            for key in (
                "anion_stratified_cv",
                "leave_one_system_out",
                "repeated_subsample",
            )
        }
        raw["anion_stratified_cv"].update(
            requested_n_folds=3, effective_n_folds=0, downshifted=False
        )
        return raw, summarize_cv_spearman(raw)

    def _run_cv_diagnostics(
        self,
        X: np.ndarray,
        y: np.ndarray,
        systems: np.ndarray,
        anions: np.ndarray,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        """Run strategies independently so one unavailable split cannot hide others."""
        cv = MultiStrategyCV(alpha=self.alpha)
        results: dict[str, dict[str, Any]] = {}
        try:
            results["anion_stratified_cv"] = cv.anion_stratified_cv(X, y, anions)
        except (ValueError, RuntimeError) as exc:
            results["anion_stratified_cv"] = {
                "strategy": "anion_stratified_cv",
                "skipped": True,
                "reason": str(exc),
                "mean_spearman": float("nan"),
                "fold_results": [],
                "requested_n_folds": 3,
                "effective_n_folds": 0,
                "downshifted": False,
            }

        if np.unique(systems).size < 2:
            results["leave_one_system_out"] = {
                "strategy": "leave_one_system_out",
                "skipped": True,
                "reason": "LOSO CV requires at least two system groups",
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
        else:
            try:
                results["leave_one_system_out"] = cv.leave_one_system_out(
                    X, y, systems
                )
            except (ValueError, RuntimeError) as exc:
                results["leave_one_system_out"] = {
                    "strategy": "leave_one_system_out",
                    "skipped": True,
                    "reason": str(exc),
                    "mean_spearman": float("nan"),
                    "fold_results": [],
                }

        try:
            results["repeated_subsample"] = cv.repeated_subsample(X, y, systems)
        except (ValueError, RuntimeError) as exc:
            results["repeated_subsample"] = {
                "strategy": "repeated_subsample",
                "skipped": True,
                "reason": str(exc),
                "mean_spearman": float("nan"),
                "fold_results": [],
            }
        return results, summarize_cv_spearman(results)

    def full_validation(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidate: Mapping[str, Any] | pd.Series,
        n_bootstrap: int = 500,
    ) -> dict[str, Any]:
        """Return four named exploratory evidence blocks and CV diagnostics."""
        candidate_map = candidate.to_dict() if isinstance(candidate, pd.Series) else candidate
        values, _, _ = self._formula_values(feature_df, candidate_map)
        y_arr = np.asarray(y, dtype=float)
        systems = np.asarray(system_labels)
        anions = np.asarray(anion_labels)
        if not (len(values) == len(y_arr) == len(systems) == len(anions)):
            raise ValueError("feature, target, system, and anion lengths must match")
        observed = _safe_spearman(values, y_arr)
        finite = np.isfinite(values) & np.isfinite(y_arr)
        target_observed = np.isfinite(y_arr)

        if int(finite.sum()) < 5 or int(target_observed.sum()) < 5:
            cv_results, cv_summary = self._unavailable_cv(
                "fewer than five finite formula-target pairs"
            )
        else:
            cv_results, cv_summary = self._run_cv_diagnostics(
                values[target_observed].reshape(-1, 1),
                y_arr[target_observed],
                systems[target_observed],
                anions[target_observed],
            )

        blocks = {
            "noise_baseline": self._noise_baseline(
                feature_df, candidate_map, y_arr, systems, observed
            ),
            "factor_spanning": self._factor_spanning(
                values, y_arr, systems, anions
            ),
            "per_system": self._per_system(values, y_arr, systems),
            "bootstrap_ci": self._bootstrap_ci(
                values, y_arr, systems, n_bootstrap=n_bootstrap
            ),
        }
        return {
            **blocks,
            "cv_diagnostics": {
                "status": "exploratory",
                "summary": cv_summary,
                "strategies": cv_results,
                "n_target_observed": int(target_observed.sum()),
                "n_formula_observed": int(finite.sum()),
                "missing_formula_policy": "fold_local_median_imputation",
            },
            "status": "exploratory",
            "causal_claim": False,
            "uncertainty": {
                "status": "exploratory",
                "method": "system_stratified_bootstrap",
                "selection_uncertainty_included": False,
                "reason": "nested outer-group selection validation is not available",
            },
        }

    def validate(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidates_df: pd.DataFrame,
        top_k: int = 10,
        n_bootstrap: int = 500,
    ) -> pd.DataFrame:
        """Validate top candidates and flatten V1--V4 beside the pair API."""
        if candidates_df.empty:
            return pd.DataFrame(columns=COMBINATION_VALIDATION_RESULT_COLUMNS)
        records: list[dict[str, Any]] = []
        for _, row in candidates_df.head(top_k).iterrows():
            try:
                evidence = self.full_validation(
                    feature_df,
                    y,
                    system_labels,
                    anion_labels,
                    row,
                    n_bootstrap=n_bootstrap,
                )
            except KeyError:
                continue
            cv_summary = evidence["cv_diagnostics"]["summary"]
            blocks = {
                name: evidence[name]
                for name in (
                    "noise_baseline",
                    "factor_spanning",
                    "per_system",
                    "bootstrap_ci",
                )
            }
            components, operators = self._candidate_formula(row)
            raw_component_families = row.get("component_families")
            if self._is_missing_field(raw_component_families):
                component_families: list[str] = []
            else:
                component_families = self._parse_formula_list(
                    raw_component_families, "component_families"
                )
                if len(component_families) != len(components):
                    raise ValueError(
                        "formula component_families count must match components"
                    )
            provenance = self._parse_formula_provenance(row.get("formula_provenance"))
            if provenance is None:
                provenance = {
                    "components": components,
                    "operators": operators,
                    "raw_value_source": row.get("raw_value_source", "feature_df"),
                }
            elif "component_families" in provenance:
                provenance_families = self._parse_formula_list(
                    provenance["component_families"],
                    "formula_provenance.component_families",
                )
                if component_families and provenance_families != component_families:
                    raise ValueError(
                        "formula provenance component families are inconsistent"
                    )
                if not component_families:
                    component_families = provenance_families
            records.append(
                {
                    "combined_name": row["combined_name"],
                    "d1": row["d1"],
                    "d2": row["d2"],
                    "operator": row["operator"],
                    "components": components,
                    "operators": operators,
                    "component_families": list(component_families),
                    "n_components": len(components),
                    "raw_value_source": row.get("raw_value_source", "feature_df"),
                    "formula_provenance": dict(provenance),
                    "combined_deconf_spearman": row.get(
                        "combined_deconf_spearman", float("nan")
                    ),
                    **cv_summary,
                    "validation_status": "exploratory",
                    "causal_claim": False,
                    "uncertainty_method": "system_stratified_bootstrap",
                    **blocks,
                    "evidence_blocks": blocks,
                    "cv_diagnostics": evidence["cv_diagnostics"],
                }
            )
        if not records:
            return pd.DataFrame(columns=COMBINATION_VALIDATION_RESULT_COLUMNS)
        return pd.DataFrame.from_records(
            records, columns=COMBINATION_VALIDATION_RESULT_COLUMNS
        )
