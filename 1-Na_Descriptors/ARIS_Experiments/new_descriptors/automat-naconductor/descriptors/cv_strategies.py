"""交叉验证策略实现。

支持多种 CV 策略以评估描述符在不同数据划分下的稳健性：
1. 阴离子分层 K 折（按阴离子类型 O/S/Se/F/Cl/Br/I 分层）
2. 留一体系交叉验证（LOSO-CV，按 NASICON/sulfide/halide 分组）
3. 重复随机子采样（按体系分层，多次重复评估波动范围）

所有策略统一使用 Ridge 回归模型，评价指标为 Spearman 秩相关和 MAE。
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import (
    LeaveOneGroupOut,
    StratifiedKFold,
    StratifiedShuffleSplit,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _fold_metrics(
    model: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
) -> tuple[float, float]:
    """训练模型并返回单折 (spearman_rho, mae)。"""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)
    rho = spearmanr(y_val, y_pred).statistic
    mae = float(np.mean(np.abs(y_val - y_pred)))
    return rho, mae


def _mean_or_nan(values: list[float]) -> float:
    """Return the finite-value mean, or NaN when no fold produced one."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return float(finite.mean()) if finite.size else float("nan")


CV_SPEARMAN_SUMMARY_COLUMNS = [
    "anion_stratified_spearman",
    "anion_stratified_skipped",
    "anion_stratified_skip_reason",
    "anion_stratified_available",
    "anion_stratified_downshifted",
    "anion_stratified_requested_n_folds",
    "anion_stratified_effective_n_folds",
    "loso_spearman",
    "loso_skipped",
    "loso_skip_reason",
    "loso_available",
    "repeated_subsample_spearman",
    "repeated_subsample_skipped",
    "repeated_subsample_skip_reason",
    "repeated_subsample_available",
    "composite_score",
    "composite_strategy_count",
    "composite_is_complete",
    "composite_score_basis",
]


def summarize_cv_spearman(
    cv_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Summarize CV without counting skipped/unavailable strategies as evidence."""
    strategies = (
        ("anion_stratified_cv", "anion_stratified"),
        ("leave_one_system_out", "loso"),
        ("repeated_subsample", "repeated_subsample"),
    )
    summary: dict[str, Any] = {}
    available_scores: list[float] = []

    for strategy_key, prefix in strategies:
        result = cv_results[strategy_key]
        spearman = float(result.get("mean_spearman", float("nan")))
        skipped = bool(result.get("skipped", False))
        available = bool(not skipped and np.isfinite(spearman))
        summary[f"{prefix}_spearman"] = spearman
        summary[f"{prefix}_skipped"] = skipped
        summary[f"{prefix}_skip_reason"] = result.get("reason") if skipped else None
        summary[f"{prefix}_available"] = available
        if available:
            available_scores.append(abs(spearman))

    anion_result = cv_results["anion_stratified_cv"]
    summary.update({
        "anion_stratified_downshifted": bool(
            anion_result.get("downshifted", False)
        ),
        "anion_stratified_requested_n_folds": int(
            anion_result.get("requested_n_folds", 0)
        ),
        "anion_stratified_effective_n_folds": int(
            anion_result.get("effective_n_folds", 0)
        ),
        "composite_score": (
            float(np.mean(available_scores))
            if available_scores else float("nan")
        ),
        "composite_strategy_count": len(available_scores),
        "composite_is_complete": len(available_scores) == len(strategies),
        "composite_score_basis": "mean_absolute_spearman_available_strategies",
    })
    return summary


class MultiStrategyCV:
    """多策略交叉验证评估器。

    用同一个 Ridge 模型在不同数据划分下评估描述符预测能力，
    检验"相关性是否稳健"而非"在某一划分下恰好好"。

    参数:
        alpha: Ridge 正则化强度，越大惩罚越重
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def _make_model(self) -> Pipeline:
        """Create a fresh fold-local imputation/scaling/Ridge pipeline."""
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=self.alpha)),
        ])

    def anion_stratified_cv(
        self,
        X: np.ndarray,
        y: np.ndarray,
        anion_labels: np.ndarray,
        n_folds: int = 3,
    ) -> dict[str, Any]:
        """阴离子分层 K 折交叉验证。

        按阴离子类型（O/S/Se/F/Cl/Br/I）分层，确保每折中
        各阴离子类型的比例大致相同。避免某类阴离子全部落在
        验证集导致"预测好只是因为记住该类"。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            anion_labels: 阴离子类型标签 (n_samples,)
            n_folds: 折数

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        anion_labels = np.asarray(anion_labels)

        # 将阴离子字符串标签编码为整数以供 StratifiedKFold 使用
        unique_anions, class_counts = np.unique(anion_labels, return_counts=True)
        requested_n_folds = int(n_folds)
        min_class_count = int(class_counts.min()) if class_counts.size else 0

        if requested_n_folds < 2 or min_class_count < 2:
            reason = (
                "anion-stratified CV skipped: at least one label has fewer than two samples"
            )
            return {
                "strategy": "anion_stratified_cv",
                "skipped": True,
                "reason": reason,
                "fold_results": [],
                "mean_spearman": float("nan"),
                "mean_mae": float("nan"),
                "requested_n_folds": requested_n_folds,
                "effective_n_folds": 0,
                "downshifted": False,
                "class_counts": {
                    str(label): int(count)
                    for label, count in zip(unique_anions, class_counts)
                },
            }

        effective_n_folds = min(requested_n_folds, min_class_count)
        anion_map = {a: i for i, a in enumerate(unique_anions)}
        anion_codes = np.array([anion_map[a] for a in anion_labels], dtype=int)

        skf = StratifiedKFold(
            n_splits=effective_n_folds,
            shuffle=True,
            random_state=42,
        )
        fold_results: list[dict[str, Any]] = []

        for fold, (train_idx, val_idx) in enumerate(skf.split(X, anion_codes), start=1):
            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": fold,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "anion_stratified_cv",
            "skipped": False,
            "reason": (
                f"requested {requested_n_folds} folds but class support allows "
                f"only {effective_n_folds}"
                if effective_n_folds != requested_n_folds else None
            ),
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
            "requested_n_folds": requested_n_folds,
            "effective_n_folds": effective_n_folds,
            "downshifted": effective_n_folds != requested_n_folds,
            "class_counts": {
                str(label): int(count)
                for label, count in zip(unique_anions, class_counts)
            },
        }

    def leave_one_system_out(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
    ) -> dict[str, Any]:
        """留一体系交叉验证（LOSO-CV）。

        每次留出一个体系（NASICON / sulfide / halide）的全部样本
        作为验证集，其余体系作为训练集。检验描述符跨体系的泛化
        能力——如果只在 NASICON 上有效，对硫化物/卤化物无效，
        说明"相关性"可能是体系特异的而非普适的。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签 (n_samples,)

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        system_labels = np.asarray(system_labels)

        # 将体系字符串标签编码为整数组号以供 LeaveOneGroupOut 使用
        unique_systems = np.unique(system_labels)
        system_map = {s: i for i, s in enumerate(unique_systems)}
        groups = np.array([system_map[s] for s in system_labels], dtype=int)

        logo = LeaveOneGroupOut()
        fold_results: list[dict[str, Any]] = []

        for fold, (train_idx, val_idx) in enumerate(logo.split(X, y, groups), start=1):
            # 跳过训练集为空或验证集为空的极端情况
            if len(train_idx) == 0 or len(val_idx) == 0:
                continue

            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": fold,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "leave_one_system_out",
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
        }

    def repeated_subsample(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        n_repeats: int = 10,
        test_fraction: float = 0.2,
        seed: int = 42,
    ) -> dict[str, Any]:
        """重复随机子采样交叉验证。

        按体系标签分层，多次随机划分训练/验证集，评估结果的
        波动范围。如果 10 次重复的 Spearman 相关波动很大，
        说明结果对数据划分敏感，不够稳健。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签，用于分层
            n_repeats: 重复次数
            test_fraction: 验证集比例
            seed: 基础随机种子

        返回:
            {strategy, fold_results, mean_spearman, mean_mae}
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        system_labels = np.asarray(system_labels)

        # 将体系字符串标签编码为整数以供 StratifiedShuffleSplit 使用
        unique_systems = np.unique(system_labels)
        system_map = {s: i for i, s in enumerate(unique_systems)}
        system_codes = np.array([system_map[s] for s in system_labels], dtype=int)

        fold_results: list[dict[str, Any]] = []

        _, class_counts = np.unique(system_codes, return_counts=True)
        n_classes = len(class_counts)
        n_samples = len(system_codes)
        valid_fraction = 0.0 < test_fraction < 1.0
        n_test = int(np.ceil(n_samples * test_fraction)) if valid_fraction else 0
        n_train = n_samples - n_test
        infeasible_reason: str | None = None
        if n_repeats < 1:
            infeasible_reason = "n_repeats must be at least one"
        elif not valid_fraction:
            infeasible_reason = "test_fraction must be strictly between zero and one"
        elif class_counts.size == 0 or int(class_counts.min()) < 2:
            infeasible_reason = (
                "stratified subsampling requires at least two samples per system label"
            )
        elif n_test < n_classes or n_train < n_classes:
            infeasible_reason = (
                f"test_fraction={test_fraction} yields train/test sizes "
                f"{n_train}/{n_test}, which cannot represent all {n_classes} system labels"
            )

        if infeasible_reason is not None:
            return {
                "strategy": "repeated_subsample",
                "skipped": True,
                "reason": infeasible_reason,
                "fold_results": [],
                "mean_spearman": float("nan"),
                "mean_mae": float("nan"),
                "n_repeats": int(n_repeats),
                "test_fraction": float(test_fraction),
                "seed": int(seed),
            }

        splitter = StratifiedShuffleSplit(
            n_splits=n_repeats,
            test_size=test_fraction,
            random_state=seed,
        )
        for repeat_idx, (train_idx, val_idx) in enumerate(
            splitter.split(X, system_codes), start=1
        ):
            rho, mae = _fold_metrics(
                self._make_model(),
                X[train_idx], y[train_idx],
                X[val_idx], y[val_idx],
            )
            fold_results.append({
                "fold": repeat_idx,
                "train_idx": train_idx,
                "val_idx": val_idx,
                "spearman": rho,
                "mae": mae,
            })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "repeated_subsample",
            "skipped": False,
            "reason": None,
            "fold_results": fold_results,
            "mean_spearman": _mean_or_nan(spearmans),
            "mean_mae": _mean_or_nan(maes),
            "n_repeats": int(n_repeats),
            "test_fraction": float(test_fraction),
            "seed": int(seed),
        }

    def run_all(
        self,
        X: np.ndarray,
        y: np.ndarray,
        system_labels: np.ndarray,
        anion_labels: np.ndarray,
    ) -> dict[str, dict[str, Any]]:
        """依次运行全部三种 CV 策略。

        参数:
            X: 特征矩阵 (n_samples, n_features)
            y: 目标向量 (n_samples,)
            system_labels: 体系分组标签 (n_samples,)
            anion_labels: 阴离子类型标签 (n_samples,)

        返回:
            {anion_stratified_cv: {...}, leave_one_system_out: {...}, repeated_subsample: {...}}
        """
        return {
            "anion_stratified_cv": self.anion_stratified_cv(X, y, anion_labels),
            "leave_one_system_out": self.leave_one_system_out(X, y, system_labels),
            "repeated_subsample": self.repeated_subsample(X, y, system_labels),
        }
