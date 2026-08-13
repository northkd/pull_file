"""线性残差秩相关分析器。

核心思想：混杂变量（如体系分类 system、阴离子类型 anion_type）同时影响
描述符 X 和电导率 Y。不去控制的话，"高相关"可能只是混杂效应而非物理信号。

方法：用 Ridge 回归分别从 X 和 Y 中"减去"混杂变量能解释的部分（残差化），
然后对残差计算 Spearman 秩相关。这样就把"因为属于某个体系而产生的相关"
和"体系内部的物理相关"分离开来。

注意：本分析器计算的 rank_corr_of_linear_residuals 不是文献意义上的
partial Spearman（后者先秩变换再偏出）。本实现先在原始尺度上做 Ridge
线性残差化，再对残差求 Spearman。该量对 x 的单调变换不不变，因线性
残差化不保秩。详见 run_info.yaml 的 estimand 段。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge


DECONFOUND_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "is_high_risk",
    "raw_spearman",
    "rank_corr_of_linear_residuals",
    "deconfound_status",
    "skip_reason",
    "n_valid",
]


class DeconfoundAnalyzer:
    """去混杂相关性分析器。

    对每个描述符，计算原始 Spearman 相关和去混杂后的正交投影残差秩相关。

    注意：本分析器计算的 rank_corr_of_linear_residuals 不是文献意义上的
    partial Spearman（后者先秩变换再偏出）。本实现先在原始尺度上做正交投影
    残差化（OLS 残差，alpha=0），再对残差求 Spearman。该量对 x 的单调变换
    不不变，因线性残差化不保秩。详见 run_info.yaml 的 estimand 段。

    参数:
        alpha: 保留仅为不波及调用点（CombinationValidator 等仍构造
            DeconfoundAnalyzer(alpha=self.alpha)）；本类的
            rank_corr_of_linear_residuals 已改为正交投影，alpha 不影响其行为。
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _one_hot_frame(labels_list: list[str], column_name: str) -> pd.DataFrame:
        """Return reference-coded dummy variables with stable, named columns."""
        labels = pd.Series(labels_list, name=column_name, dtype="string")
        return pd.get_dummies(
            labels,
            prefix=column_name,
            drop_first=True,
            dtype=float,
        )

    @staticmethod
    def build_rank_aware_controls(
        system_labels: list[str],
        anion_labels: list[str],
    ) -> tuple[pd.DataFrame, dict[str, object]]:
        """Build system-primary controls and audit redundant anion contrasts."""
        if len(system_labels) != len(anion_labels):
            raise ValueError("system and anion label lengths must match")
        system_frame = DeconfoundAnalyzer._one_hot_frame(
            system_labels, "system"
        ).reset_index(drop=True)
        anion_frame = DeconfoundAnalyzer._one_hot_frame(
            anion_labels, "anion_type"
        ).reset_index(drop=True)

        intercept = np.ones((len(system_labels), 1), dtype=float)
        system_design = np.column_stack(
            [intercept, system_frame.to_numpy(dtype=float)]
        )
        combined_design = np.column_stack(
            [system_design, anion_frame.to_numpy(dtype=float)]
        )
        system_rank = int(np.linalg.matrix_rank(system_design))
        confounder_rank = int(np.linalg.matrix_rank(combined_design))

        current_design = system_design
        current_rank = system_rank
        incremental: list[str] = []
        redundant: list[str] = []
        for column in anion_frame.columns:
            candidate = np.column_stack(
                [current_design, anion_frame[[column]].to_numpy(dtype=float)]
            )
            candidate_rank = int(np.linalg.matrix_rank(candidate))
            if candidate_rank > current_rank:
                incremental.append(str(column))
                current_design = candidate
                current_rank = candidate_rank
            else:
                redundant.append(str(column))

        controls = pd.concat([system_frame, anion_frame[incremental]], axis=1)
        metadata: dict[str, object] = {
            "primary_control": "system",
            "system_design_rank": system_rank,
            "confounder_rank": confounder_rank,
            "anion_incremental_rank": confounder_rank - system_rank,
            "anion_redundant_count": len(redundant),
            "anion_incremental_columns": incremental,
            "anion_redundant_columns": redundant,
            "anion_is_independent_control": False,
            "control_coding": "reference_class_with_intercept",
            "control_columns": [
                "intercept",
                *map(str, system_frame.columns),
                *map(str, anion_frame.columns),
            ],
            "residualization_columns": list(map(str, controls.columns)),
        }
        return controls, metadata

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    def _projection_residuals(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[np.ndarray | None, np.ndarray | None, str | None]:
        """对 x 和 y 做正交投影残差化（等价于带截距的 OLS 残差）。

        给控制矩阵 z 追加一列全 1 作为截距，使 lstsq 等价于带截距的 OLS。

        返回:
            (res_x, res_y, failure_reason)。成功时 failure_reason 为 None；
            秩亏时为 "rank_deficient"；lstsq 数值失败时为 "lstsq_numerical_failure"。
            失败时 res_x 和 res_y 均为 None。
        """
        z = confounders_df.values.astype(float)
        n_samples = len(x)
        z_with_intercept = np.column_stack([np.ones(n_samples), z])
        try:
            coef_x, _, _, rank_x = np.linalg.lstsq(z_with_intercept, x, rcond=None)
            coef_y, _, _, rank_y = np.linalg.lstsq(z_with_intercept, y, rcond=None)
        except np.linalg.LinAlgError:
            return None, None, "lstsq_numerical_failure"

        n_cols = z_with_intercept.shape[1]
        rank_x_int = int(np.asarray(rank_x).item()) if np.asarray(rank_x).size == 1 else int(np.asarray(rank_x).flatten()[0])
        rank_y_int = int(np.asarray(rank_y).item()) if np.asarray(rank_y).size == 1 else int(np.asarray(rank_y).flatten()[0])
        if rank_x_int < n_cols or rank_y_int < n_cols:
            return None, None, "rank_deficient"

        res_x = x - z_with_intercept @ coef_x
        res_y = y - z_with_intercept @ coef_y
        return res_x, res_y, None

    def rank_corr_of_linear_residuals(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[float, float, str]:
        """计算控制混杂变量后的正交投影残差秩相关。

        注意：本方法不是文献意义上的 partial Spearman（后者先秩变换再偏出）。
        本方法先在原始尺度上对 x 与 y 各自做正交投影残差化（等价于 OLS 残差，
        alpha=0），再对两组残差求 Spearman。该量对 x 的单调变换不不变，因线性
        残差化不保秩。

        步骤:
        1. 用最小二乘分别拟合 x ~ confounders 和 y ~ confounders
        2. 取残差: res_x = x - Z @ coef_x, res_y 同理
        3. 对残差计算 spearmanr

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            (rho, p_value, status) — 正交投影残差化后的 Spearman 相关系数、
            p 值和状态码。status 取值：
            - "ok": 正常完成残差化与秩相关
            - "insufficient_samples": n_samples < 3，无法做 Spearman
            - "empty_control_space": 控制矩阵列数为 0，无混杂可控制
            - "controls_rank_deficient": 控制列数 >= 样本数，或控制矩阵秩亏，残差化退化
            - "lstsq_numerical_failure": lstsq 抛出 LinAlgError，数值失败（非秩亏）
            退化时 rho 和 p_value 均为 NaN，不静默回退到原始 Spearman。
        """
        z = confounders_df.values.astype(float)

        # 退化路径：不再回退到原始 Spearman，返回显式 NaN + 可辨识 status
        n_samples = len(x)
        if n_samples < 3:
            return float("nan"), float("nan"), "insufficient_samples"
        if z.shape[1] == 0:
            return float("nan"), float("nan"), "empty_control_space"
        if z.shape[1] + 1 >= n_samples:
            return float("nan"), float("nan"), "controls_rank_deficient"

        # 正交投影残差化（等价于 alpha=0 的 OLS 残差）：
        res_x, res_y, failure_reason = self._projection_residuals(x, y, confounders_df)
        if failure_reason is not None:
            if failure_reason == "rank_deficient":
                return float("nan"), float("nan"), "controls_rank_deficient"
            else:  # "lstsq_numerical_failure"
                return float("nan"), float("nan"), "lstsq_numerical_failure"

        # 残差上的 Spearman 相关
        rho, p_val = stats.spearmanr(res_x, res_y)
        return float(rho), float(p_val), "ok"

    def rank_corr_of_linear_residuals_rho(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[float, str]:
        """计算线性残差秩相关 rho（便捷方法，只返回 rho 和 status）。

        注意：本方法返回的是 rank_corr_of_linear_residuals，不是文献意义上
        的 partial Spearman。详见 run_info.yaml 的 estimand 段。

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            (rho, status) — 线性残差化后的 Spearman rho 和状态码。
            退化时 rho 为 NaN，status 标识退化原因。
        """
        rho, _, status = self.rank_corr_of_linear_residuals(x, y, confounders_df)
        return rho, status

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def analyze_all(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
    ) -> pd.DataFrame:
        """对所有描述符列执行去混杂分析。

        对每个描述符计算:
        - raw_spearman: 原始 Spearman rho
        - rank_corr_of_linear_residuals: 控制 system + anion 后的线性残差秩相关 rho

        参数:
            feature_df: 包含描述符列的 DataFrame（已标准化）
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 每个样本的体系标签，如 ["NASICON", ...]
            anion_labels: 每个样本的阴离子标签，如 ["O", ...]

        返回:
            分析结果 DataFrame，列为:
            descriptor, family, is_high_risk, raw_spearman,
            rank_corr_of_linear_residuals
        """
        # --- 构造混杂变量矩阵 ---
        confounders_df, control_metadata = self.build_rank_aware_controls(
            system_labels, anion_labels
        )

        # --- 获取描述符注册表，用于查询 family 和 is_high_risk ---
        from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS

        y_arr = np.asarray(y, dtype=float)

        # --- 确定描述符列 ---
        registered_names = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
        descriptor_cols = [c for c in feature_df.columns if c in registered_names]

        records: list[dict] = []
        for col in descriptor_cols:
            x_raw = feature_df[col].values.astype(float)

            # 有效值不足时不再 continue，而是产出显式 NaN 行
            valid_mask = ~np.isnan(x_raw) & ~np.isnan(y_arr)
            n_valid = int(valid_mask.sum())
            if n_valid < 5:
                _func, family, is_high_risk = SEARCHABLE_STRUCTURE_DESCRIPTORS.get(
                    col, (None, "unknown", False),
                )
                records.append({
                    "descriptor": col,
                    "family": family,
                    "is_high_risk": is_high_risk,
                    "raw_spearman": float("nan"),
                    "rank_corr_of_linear_residuals": float("nan"),
                    "deconfound_status": "not_attempted",
                    "skip_reason": "insufficient_valid_samples",
                    "n_valid": n_valid,
                })
                continue

            x_valid = x_raw[valid_mask]
            y_valid = y_arr[valid_mask]
            conf_valid = confounders_df.loc[valid_mask].reset_index(drop=True)

            # 原始 Spearman 相关
            raw_rho, _raw_p = stats.spearmanr(x_valid, y_valid)
            raw_rho = float(raw_rho)

            # 线性残差秩相关（非偏 Spearman），只保留 rho 和 status
            deconf_rho, deconf_status = self.rank_corr_of_linear_residuals_rho(
                x_valid, y_valid, conf_valid,
            )

            # 查询 family 和 is_high_risk
            _func, family, is_high_risk = SEARCHABLE_STRUCTURE_DESCRIPTORS.get(
                col, (None, "unknown", False),
            )

            records.append({
                "descriptor": col,
                "family": family,
                "is_high_risk": is_high_risk,
                "raw_spearman": raw_rho,
                "rank_corr_of_linear_residuals": deconf_rho,
                "deconfound_status": deconf_status,
                "skip_reason": None,
                "n_valid": n_valid,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=DECONFOUND_RESULT_COLUMNS,
        )

        # 按 |rank_corr_of_linear_residuals| 降序排列：物理信号最强的排最前
        if not result_df.empty:
            result_df = result_df.sort_values(
                by="rank_corr_of_linear_residuals",
                key=lambda s: s.abs(),
                ascending=False,
            ).reset_index(drop=True)

        result_df.attrs.update(control_metadata)

        return result_df
