"""去混杂分析器。

核心思想：混杂变量（如体系分类 system、阴离子类型 anion_type）同时影响
描述符 X 和电导率 Y。不去控制的话，"高相关"可能只是混杂效应而非物理信号。

方法：用 Ridge 回归分别从 X 和 Y 中"减去"混杂变量能解释的部分（残差化），
然后对残差计算 Spearman 秩相关。这样就把"因为属于某个体系而产生的相关"
和"体系内部的物理相关"分离开来。

体系代理比 system_proxy_ratio = 1 - (deconf_rho² / raw_rho²)：
  - 接近 1 → 相关几乎全由混杂驱动，描述符是体系代理
  - 接近 0 → 去混杂后相关依然强，是真实物理信号
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
    "deconfounded_spearman",
    "deconf_p",
    "system_proxy_ratio",
    "label",
]


class DeconfoundAnalyzer:
    """去混杂相关性分析器。

    对每个描述符，计算原始 Spearman 相关和去混杂后的偏 Spearman 相关，
    并据此判断描述符是"物理信号"还是"体系代理"。

    参数:
        alpha: Ridge 回归正则化强度。
            去混杂时用 Ridge 做残差化，alpha 控制正则化程度。
            alpha=0 等价于普通最小二乘；alpha 越大，残差化越保守。
            默认 1.0，对小样本（~100）有一定正则化保护。
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _one_hot_encode(labels_list: list[str], column_name: str) -> np.ndarray:
        """将分类标签列表转为带参考类别的 one-hot 矩阵。

        参数:
            labels_list: 分类标签列表，如 ["NASICON", "β-alumina", ...]
            column_name: 列名，仅用于 DataFrame 构造

        返回:
            one-hot 矩阵 (n_samples, n_categories - 1)，float64 类型
        """
        encoded = DeconfoundAnalyzer._one_hot_frame(labels_list, column_name)
        return encoded.values

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

    def partial_spearman(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> tuple[float, float]:
        """计算控制混杂变量后的偏 Spearman 秩相关。

        步骤:
        1. 用 Ridge 分别拟合 x ~ confounders 和 y ~ confounders
        2. 取残差: res_x = x - confounders_predicted_x, res_y 同理
        3. 对残差计算 spearmanr

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            (rho, p_value) — 去混杂后的 Spearman 相关系数和 p 值
        """
        z = confounders_df.values.astype(float)

        # 样本数不足时无法残差化，回退到原始相关
        n_samples = len(x)
        if n_samples < 3 or z.shape[1] == 0 or z.shape[1] >= n_samples:
            rho, p_val = stats.spearmanr(x, y)
            return float(rho), float(p_val)

        # Ridge 残差化: 对 x 和 y 分别做 x ~ Z, y ~ Z
        ridge = Ridge(alpha=self.alpha)

        # 残差 = 原始值 - 混杂预测值
        ridge.fit(z, x)
        res_x = x - ridge.predict(z)

        ridge.fit(z, y)
        res_y = y - ridge.predict(z)

        # 残差上的 Spearman 相关
        rho, p_val = stats.spearmanr(res_x, res_y)
        return float(rho), float(p_val)

    def deconfounded_spearman(
        self,
        x: np.ndarray,
        y: np.ndarray,
        confounders_df: pd.DataFrame,
    ) -> float:
        """计算去混杂 Spearman rho（便捷方法，只返回 rho）。

        参数:
            x: 描述符值向量 (n_samples,)
            y: 目标值向量 (n_samples,)
            confounders_df: 混杂变量矩阵 (n_samples, n_confounders)

        返回:
            去混杂后的 Spearman rho
        """
        rho, _ = self.partial_spearman(x, y, confounders_df)
        return rho

    # ------------------------------------------------------------------
    # 标签分类
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_descriptor(
        raw_rho: float,
        deconf_rho: float,
        system_proxy_ratio: float,
        deconf_p: float,
    ) -> str:
        """根据去混杂结果给描述符打标签。

        分类规则 (errata P3):
        - 去混杂后 |deconf_rho| > 0.3 → '强物理信号'（无论代理比多高，
          去混杂后仍显著相关，说明物理信号确实存在）
        - |deconf_rho| <= 0.3 且 system_proxy_ratio < 0.3 → '弱物理信号'
          （代理比低，但去混杂后信号也不强）
        - |deconf_rho| <= 0.3 且 0.3 <= system_proxy_ratio < 0.7 → '混合信号'
          （部分来自体系混杂，部分可能是物理）
        - |deconf_rho| <= 0.3 且 system_proxy_ratio >= 0.7 → '体系代理'
          （大部分相关由混杂驱动）
        - |raw_rho| < 0.2 → '噪声级'（连原始相关都极弱）

        参数:
            raw_rho: 原始 Spearman rho
            deconf_rho: 去混杂后 Spearman rho
            system_proxy_ratio: 体系代理比 [0, 1]
            deconf_p: 去混杂后 p 值

        返回:
            分类标签字符串
        """
        # 原始相关极弱 → 噪声级
        if abs(raw_rho) < 0.2:
            return "噪声级"

        # 去混杂后仍然显著 → 强物理信号（errata P3 核心修正）
        if abs(deconf_rho) > 0.3:
            return "强物理信号"

        # 去混杂后信号弱，根据代理比分
        if system_proxy_ratio < 0.3:
            return "弱物理信号"
        if system_proxy_ratio < 0.7:
            return "混合信号"
        return "体系代理"

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
        - deconfounded_spearman: 控制 system + anion 后的 rho
        - deconf_p: 去混杂后的 p 值
        - system_proxy_ratio: 体系代理比（1 - deconf_rho² / raw_rho²）
        - label: 分类标签

        参数:
            feature_df: 包含描述符列的 DataFrame（已标准化）
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 每个样本的体系标签，如 ["NASICON", ...]
            anion_labels: 每个样本的阴离子标签，如 ["O", ...]

        返回:
            分析结果 DataFrame，列为:
            descriptor, family, is_high_risk, raw_spearman,
            deconfounded_spearman, deconf_p, system_proxy_ratio, label
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

            # 跳过 NaN 过多的列：有效值不足 80% 则跳过
            valid_mask = ~np.isnan(x_raw) & ~np.isnan(y_arr)
            n_valid = int(valid_mask.sum())
            if n_valid < 5:
                continue

            x_valid = x_raw[valid_mask]
            y_valid = y_arr[valid_mask]
            conf_valid = confounders_df.loc[valid_mask].reset_index(drop=True)

            # 原始 Spearman 相关
            raw_rho, _raw_p = stats.spearmanr(x_valid, y_valid)
            raw_rho = float(raw_rho)

            # 去混杂偏 Spearman 相关
            deconf_rho, deconf_p = self.partial_spearman(
                x_valid, y_valid, conf_valid,
            )

            # 体系代理比
            raw_rho_sq = raw_rho ** 2
            deconf_rho_sq = deconf_rho ** 2

            if raw_rho_sq < 1e-12:
                # 原始相关几乎为零，代理比无意义，设为 0
                system_proxy_ratio = 0.0
            elif raw_rho * deconf_rho < 0:
                # 原始和去混杂后符号相反 → 相关完全由混杂驱动
                system_proxy_ratio = 1.0
            else:
                system_proxy_ratio = 1.0 - deconf_rho_sq / raw_rho_sq
                # 钳位到 [0, 1]
                system_proxy_ratio = max(0.0, min(1.0, system_proxy_ratio))

            # 查询 family 和 is_high_risk
            _func, family, is_high_risk = SEARCHABLE_STRUCTURE_DESCRIPTORS.get(
                col, (None, "Unknown", False),
            )

            # 分类标签
            label = self._classify_descriptor(
                raw_rho, deconf_rho, system_proxy_ratio, deconf_p,
            )

            records.append({
                "descriptor": col,
                "family": family,
                "is_high_risk": is_high_risk,
                "raw_spearman": raw_rho,
                "deconfounded_spearman": deconf_rho,
                "deconf_p": deconf_p,
                "system_proxy_ratio": system_proxy_ratio,
                "label": label,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=DECONFOUND_RESULT_COLUMNS,
        )

        # 按 |deconfounded_spearman| 降序排列：物理信号最强的排最前
        if not result_df.empty:
            result_df = result_df.sort_values(
                by="deconfounded_spearman",
                key=lambda s: s.abs(),
                ascending=False,
            ).reset_index(drop=True)

        result_df.attrs.update(control_metadata)

        return result_df
