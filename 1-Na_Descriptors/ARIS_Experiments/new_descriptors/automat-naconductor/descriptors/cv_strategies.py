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
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold


def _fold_metrics(
    model: Ridge,
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


class MultiStrategyCV:
    """多策略交叉验证评估器。

    用同一个 Ridge 模型在不同数据划分下评估描述符预测能力，
    检验"相关性是否稳健"而非"在某一划分下恰好好"。

    参数:
        alpha: Ridge 正则化强度，越大惩罚越重
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def _make_model(self) -> Ridge:
        """创建新的 Ridge 实例（每折独立训练）。"""
        return Ridge(alpha=self.alpha)

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
        # 将阴离子字符串标签编码为整数以供 StratifiedKFold 使用
        unique_anions = np.unique(anion_labels)
        anion_map = {a: i for i, a in enumerate(unique_anions)}
        anion_codes = np.array([anion_map[a] for a in anion_labels], dtype=int)

        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
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
            "fold_results": fold_results,
            "mean_spearman": float(np.mean(spearmans)),
            "mean_mae": float(np.mean(maes)),
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
            "mean_spearman": float(np.mean(spearmans)),
            "mean_mae": float(np.mean(maes)),
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
        # 将体系字符串标签编码为整数以供 StratifiedKFold 使用
        unique_systems = np.unique(system_labels)
        system_map = {s: i for i, s in enumerate(unique_systems)}
        system_codes = np.array([system_map[s] for s in system_labels], dtype=int)

        # 用单折 StratifiedKFold 模拟一次分层随机划分
        # n_splits=1 配合不同 random_state 实现多次独立采样
        fold_results: list[dict[str, Any]] = []

        for repeat_idx in range(n_repeats):
            # 每次重复用不同种子，保证独立性
            skf = StratifiedKFold(
                n_splits=1,
                shuffle=True,
                random_state=seed + repeat_idx,
            )
            # skf.split 每次只生成一组 (train_idx, val_idx)
            for train_idx, val_idx in skf.split(X, system_codes):
                rho, mae = _fold_metrics(
                    self._make_model(),
                    X[train_idx], y[train_idx],
                    X[val_idx], y[val_idx],
                )
                fold_results.append({
                    "fold": repeat_idx + 1,
                    "train_idx": train_idx,
                    "val_idx": val_idx,
                    "spearman": rho,
                    "mae": mae,
                })

        spearmans = [f["spearman"] for f in fold_results]
        maes = [f["mae"] for f in fold_results]
        return {
            "strategy": "repeated_subsample",
            "fold_results": fold_results,
            "mean_spearman": float(np.mean(spearmans)),
            "mean_mae": float(np.mean(maes)),
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
