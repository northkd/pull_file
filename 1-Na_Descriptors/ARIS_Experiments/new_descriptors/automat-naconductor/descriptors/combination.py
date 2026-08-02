"""约束组合描述符搜索与验证。

从 PhysicalGrouper 选出的代表描述符中，生成所有物理约束允许的
2-描述符组合（+, ×, ratio），用去混杂 Spearman 评估每个组合，
再用多策略 CV 验证排名靠前的组合。

物理约束核心规则：
- 同族描述符：+, ×, ratio 均允许
- 跨族描述符：仅在 CROSS_GROUP_RULES["allowed_pairs"] 中的对允许组合
- A↔C 对：仅允许 ratio，禁止 multiply
- ratio 运算：跨族时需显式允许或无特殊限制才可用
- 禁止 log/√/power/任意除法，仅 +, ×, 同量纲 ratio
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge

from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
from descriptors._base import CROSS_GROUP_RULES, PHYSICAL_FAMILIES
from descriptors.cv_strategies import MultiStrategyCV
from descriptors.deconfound import DeconfoundAnalyzer


class ConstrainedCombinationSearch:
    """约束组合搜索器。

    从代表描述符中生成所有物理约束允许的 2-描述符组合，
    用去混杂 Spearman 评估每个组合的物理信号强度。

    参数:
        alpha: Ridge 正则化强度（用于去混杂残差化）
        seed: 随机种子
    """

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    # ------------------------------------------------------------------
    # 约束检查
    # ------------------------------------------------------------------

    @staticmethod
    def _getAllowedOperators(
        family1: str,
        family2: str,
    ) -> list[str]:
        """根据物理约束返回允许的运算符列表。

        规则:
        - 同族 → +, ×, ratio 全部允许
        - 跨族但不在 allowed_pairs → 不允许任何组合
        - 跨族在 allowed_pairs → 检查 per_operator_restrictions:
          - 有显式 allowed_ops → 只允许列出的运算
          - 有显式 forbidden_ops → 排除列出的运算
          - 无限制 → 默认 +, ×, ratio 全部允许

        参数:
            family1: 第一个描述符的族键（如 "A", "D_prime"）
            family2: 第二个描述符的族键

        返回:
            允许的运算符列表，如 ["+", "multiply", "ratio"]
            空列表表示该跨族对不被允许
        """
        # 同族：所有运算允许
        if family1 == family2:
            return ["+", "multiply", "ratio"]

        # 跨族：检查是否在允许对中（两个方向都要查）
        allowed_pairs = CROSS_GROUP_RULES["allowed_pairs"]
        pair_forward = (family1, family2) in allowed_pairs
        pair_reverse = (family2, family1) in allowed_pairs

        if not pair_forward and not pair_reverse:
            # 不在允许对中 → 该跨族组合被禁止
            return []

        # 在允许对中，检查 per_operator_restrictions
        per_op = CROSS_GROUP_RULES.get("per_operator_restrictions", {})

        # 查找与该对相关的限制（两个方向都查）
        restrictions = per_op.get((family1, family2))
        if restrictions is None:
            restrictions = per_op.get((family2, family1))

        all_ops = ["+", "multiply", "ratio"]

        if restrictions is None:
            # 无特殊限制，所有运算允许
            return all_ops

        # 有显式 allowed_ops → 只允许列出的
        if "allowed_ops" in restrictions:
            return [op for op in all_ops if op in restrictions["allowed_ops"]]

        # 有 forbidden_ops → 排除列出的
        if "forbidden_ops" in restrictions:
            return [op for op in all_ops if op not in restrictions["forbidden_ops"]]

        return all_ops

    # ------------------------------------------------------------------
    # 组合特征生成
    # ------------------------------------------------------------------

    @staticmethod
    def _generateCombinedFeature(
        d1_values: np.ndarray,
        d2_values: np.ndarray,
        operator: str,
    ) -> np.ndarray:
        """根据运算符生成组合特征值。

        参数:
            d1_values: 第一个描述符值向量
            d2_values: 第二个描述符值向量
            operator: 运算符 ("+", "multiply", "ratio")

        返回:
            组合特征值向量
        """
        if operator == "+":
            return d1_values + d2_values
        elif operator == "multiply":
            return d1_values * d2_values
        elif operator == "ratio":
            # 加小 epsilon 避免除零
            return d1_values / (d2_values + 1e-8 * np.sign(d2_values + 1e-16))
        else:
            raise ValueError(f"不支持的运算符: {operator}")

    # ------------------------------------------------------------------
    # 主搜索方法
    # ------------------------------------------------------------------

    def search(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        representative_df: pd.DataFrame,
        max_candidates: int = 150,
    ) -> pd.DataFrame:
        """搜索物理约束下的最优 2-描述符组合。

        步骤:
        1. 筛选 is_representative == True 的代表描述符
        2. 生成所有有序对 (d1, d2)
        3. 对每对检查物理约束，确定允许的运算符
        4. 对每个有效 (对, 运算符) 生成组合特征
        5. 用去混杂 Spearman 评估每个组合
        6. 按 |去混杂 Spearman| 降序排列，截断至 max_candidates

        参数:
            feature_df: 包含描述符列（已标准化）+ 噪声列的 DataFrame
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 体系标签列表，用于去混杂
            anion_labels: 阴离子标签列表，用于去混杂
            representative_df: PhysicalGrouper 输出，需含列:
                descriptor, family, is_representative, deconfounded_spearman
            max_candidates: 最大候选数安全上限

        返回:
            DataFrame，列为:
            combined_name, d1, d2, operator, d1_family, d2_family,
            is_cross_family, combined_raw_spearman, combined_deconf_spearman
        """
        # --- 1. 筛选代表描述符 ---
        reps = representative_df[representative_df["is_representative"] == True].copy()  # noqa: E712
        if reps.empty:
            return pd.DataFrame(columns=[
                "combined_name", "d1", "d2", "operator",
                "d1_family", "d2_family", "is_cross_family",
                "combined_raw_spearman", "combined_deconf_spearman",
            ])

        rep_names = reps["descriptor"].tolist()
        # 构建描述符 → 族映射
        desc_to_family: dict[str, str] = {}
        for _, row in reps.iterrows():
            desc_to_family[row["descriptor"]] = row["family"]

        # 补充注册表中的族信息（以防 representative_df 缺失）
        for name, (_, family_key, _) in AVAILABLE_STRUCTURE_DESCRIPTORS.items():
            if name not in desc_to_family:
                desc_to_family[name] = family_key

        # --- 2. 构造去混杂变量矩阵 ---
        deconf = DeconfoundAnalyzer(alpha=self.alpha)
        system_onehot = deconf._one_hot_encode(system_labels, "system")
        anion_onehot = deconf._one_hot_encode(anion_labels, "anion_type")
        confounders_arr = np.hstack([system_onehot, anion_onehot])
        confounders_df = pd.DataFrame(
            confounders_arr,
            columns=[f"system_{i}" for i in range(system_onehot.shape[1])]
            + [f"anion_{i}" for i in range(anion_onehot.shape[1])],
        )

        y_arr = np.asarray(y, dtype=float)

        # --- 3. 生成所有有序对并检查约束 ---
        candidates: list[dict] = []

        for i, d1 in enumerate(rep_names):
            for j, d2 in enumerate(rep_names):
                if d1 == d2:
                    continue

                f1 = desc_to_family.get(d1, "unknown")
                f2 = desc_to_family.get(d2, "unknown")
                is_cross = f1 != f2

                # 查询允许的运算符
                allowed_ops = self._getAllowedOperators(f1, f2)
                if not allowed_ops:
                    continue

                for op in allowed_ops:
                    # ratio 的额外约束：
                    # 跨族时，如果 per_operator_restrictions 中
                    # 没有显式允许 ratio，但也没有限制，默认允许。
                    # 这里已在 _getAllowedOperators 中处理。

                    # 生成组合名
                    op_symbol = {"+": "+", "multiply": "×", "ratio": "/"}[op]
                    combined_name = f"({d1} {op_symbol} {d2})"

                    # 获取原始值
                    if d1 not in feature_df.columns or d2 not in feature_df.columns:
                        continue

                    d1_values = feature_df[d1].values.astype(float)
                    d2_values = feature_df[d2].values.astype(float)

                    # 有效样本掩码（排除 NaN）
                    valid_mask = (
                        ~np.isnan(d1_values)
                        & ~np.isnan(d2_values)
                        & ~np.isnan(y_arr)
                    )
                    n_valid = int(valid_mask.sum())
                    if n_valid < 5:
                        continue

                    d1_valid = d1_values[valid_mask]
                    d2_valid = d2_values[valid_mask]
                    y_valid = y_arr[valid_mask]
                    conf_valid = confounders_df.loc[valid_mask].reset_index(drop=True)

                    # 生成组合特征
                    combined_values = self._generateCombinedFeature(
                        d1_valid, d2_valid, op,
                    )

                    # 检查组合值是否有意义（非全零/全NaN/全Inf）
                    if np.all(np.isnan(combined_values)) or np.all(np.isinf(combined_values)):
                        continue
                    # 将 Inf 替换为 NaN 再处理
                    combined_values = np.where(
                        np.isfinite(combined_values), combined_values, np.nan,
                    )
                    finite_mask = ~np.isnan(combined_values)
                    if finite_mask.sum() < 5:
                        continue

                    # 原始 Spearman
                    raw_rho, _ = stats.spearmanr(
                        combined_values[finite_mask],
                        y_valid[finite_mask],
                    )
                    raw_rho = float(raw_rho)

                    # 去混杂 Spearman
                    deconf_rho = deconf.deconfounded_spearman(
                        combined_values[finite_mask],
                        y_valid[finite_mask],
                        conf_valid.loc[finite_mask].reset_index(drop=True),
                    )

                    candidates.append({
                        "combined_name": combined_name,
                        "d1": d1,
                        "d2": d2,
                        "operator": op,
                        "d1_family": f1,
                        "d2_family": f2,
                        "is_cross_family": is_cross,
                        "combined_raw_spearman": raw_rho,
                        "combined_deconf_spearman": deconf_rho,
                    })

        # --- 6. 排序与截断 ---
        if not candidates:
            return pd.DataFrame(columns=[
                "combined_name", "d1", "d2", "operator",
                "d1_family", "d2_family", "is_cross_family",
                "combined_raw_spearman", "combined_deconf_spearman",
            ])

        result_df = pd.DataFrame(candidates)
        result_df = result_df.sort_values(
            by="combined_deconf_spearman",
            key=lambda s: s.abs(),
            ascending=False,
        ).reset_index(drop=True)

        # 安全截断
        if len(result_df) > max_candidates:
            result_df = result_df.head(max_candidates).reset_index(drop=True)

        return result_df


class CombinationValidator:
    """组合描述符验证器。

    用多策略交叉验证验证排名靠前的组合描述符，
    检验去混杂相关性在不同数据划分下是否稳健。

    参数:
        alpha: Ridge 正则化强度
        seed: 随机种子
    """

    def __init__(self, alpha: float = 1.0, seed: int = 42) -> None:
        self.alpha = alpha
        self.seed = seed

    def validate(
        self,
        feature_df: pd.DataFrame,
        y: np.ndarray,
        system_labels: list[str],
        anion_labels: list[str],
        candidates_df: pd.DataFrame,
        top_k: int = 10,
    ) -> pd.DataFrame:
        """用多策略 CV 验证排名靠前的组合候选。

        对每个候选:
        1. 从 feature_df 重构组合特征
        2. 用 MultiStrategyCV.run_all 执行三种 CV 策略
        3. 计算综合得分 = 各策略 |Spearman| 的均值

        参数:
            feature_df: 包含原始描述符列的 DataFrame
            y: log_sigma 目标向量 (n_samples,)
            system_labels: 体系标签列表
            anion_labels: 阴离子标签列表
            candidates_df: ConstrainedCombinationSearch.search() 输出
            top_k: 验证前 k 个候选

        返回:
            DataFrame，列为:
            combined_name, d1, d2, operator, combined_deconf_spearman,
            anion_stratified_spearman, loso_spearman,
            repeated_subsample_spearman, composite_score
        """
        if candidates_df.empty:
            return pd.DataFrame(columns=[
                "combined_name", "d1", "d2", "operator",
                "combined_deconf_spearman",
                "anion_stratified_spearman", "loso_spearman",
                "repeated_subsample_spearman", "composite_score",
            ])

        # 取前 top_k 个
        top_df = candidates_df.head(top_k).copy()

        y_arr = np.asarray(y, dtype=float)
        system_arr = np.asarray(system_labels)
        anion_arr = np.asarray(anion_labels)

        cv = MultiStrategyCV(alpha=self.alpha)

        records: list[dict] = []
        for _, row in top_df.iterrows():
            d1 = row["d1"]
            d2 = row["d2"]
            op = row["operator"]

            # 检查描述符是否在 feature_df 中
            if d1 not in feature_df.columns or d2 not in feature_df.columns:
                continue

            d1_values = feature_df[d1].values.astype(float)
            d2_values = feature_df[d2].values.astype(float)

            # 重构组合特征
            combined = ConstrainedCombinationSearch._generateCombinedFeature(
                d1_values, d2_values, op,
            )

            # 将 Inf 替换为 NaN，再用列均值填充
            combined = np.where(np.isfinite(combined), combined, np.nan)
            col_mean = np.nanmean(combined)
            combined = np.where(np.isnan(combined), col_mean, combined)

            # Ridge 需要 2D 输入
            X_combined = combined.reshape(-1, 1)

            # 有效样本掩码
            valid_mask = ~np.isnan(X_combined[:, 0]) & ~np.isnan(y_arr)
            n_valid = int(valid_mask.sum())
            if n_valid < 5:
                continue

            X_valid = X_combined[valid_mask]
            y_valid = y_arr[valid_mask]
            system_valid = system_arr[valid_mask]
            anion_valid = anion_arr[valid_mask]

            # 运行多策略 CV
            cv_results = cv.run_all(X_valid, y_valid, system_valid, anion_valid)

            # 提取各策略的 mean_spearman
            anion_spearman = cv_results["anion_stratified_cv"]["mean_spearman"]
            loso_spearman = cv_results["leave_one_system_out"]["mean_spearman"]
            subsample_spearman = cv_results["repeated_subsample"]["mean_spearman"]

            # 综合得分 = 各策略 |Spearman| 的均值
            composite_score = float(np.mean([
                abs(anion_spearman),
                abs(loso_spearman),
                abs(subsample_spearman),
            ]))

            records.append({
                "combined_name": row["combined_name"],
                "d1": d1,
                "d2": d2,
                "operator": op,
                "combined_deconf_spearman": row["combined_deconf_spearman"],
                "anion_stratified_spearman": float(anion_spearman),
                "loso_spearman": float(loso_spearman),
                "repeated_subsample_spearman": float(subsample_spearman),
                "composite_score": composite_score,
            })

        if not records:
            return pd.DataFrame(columns=[
                "combined_name", "d1", "d2", "operator",
                "combined_deconf_spearman",
                "anion_stratified_spearman", "loso_spearman",
                "repeated_subsample_spearman", "composite_score",
            ])

        return pd.DataFrame(records)
