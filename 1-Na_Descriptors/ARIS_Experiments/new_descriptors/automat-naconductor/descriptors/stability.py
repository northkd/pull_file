"""稳定性选择（Stability Selection）与物理族代表选择。

稳定性选择的核心思想：多次自举采样，每次做特征选择，
统计每个特征被选中的频率。频率越高，说明该特征越稳定可靠。

为什么需要稳定性选择？
- 小样本（~84 行）+ 多描述符 → 特征选择容易过拟合
- 单次选择可能因随机性选中噪声特征
- 频率 > 阈值（默认 0.6）的特征才是"真信号"

噪声基线校准：加入随机噪声列，若真实描述符的选中频率
不高于噪声列的 95 分位数，则该描述符不比随机更好。

物理族代表选择（errata P4）：
- 每个物理族最多选 1 个代表（默认 max_per_family=1）
- 代表 = 该族中稳定性通过且 |线性残差秩相关| 最高的描述符（保留符号）
- 此容量是硬上限；缺少其它物理族不会增加任一族的名额
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Lasso
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# 描述符注册表和物理族定义
from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors._base import PHYSICAL_FAMILIES


PHYSICAL_GROUP_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "family_name",
    "rank_corr_of_linear_residuals",
    "selection_freq",
    "is_stable",
    "is_representative",
    "deconfound_status",
    "skip_reason",
    "n_valid",
]

STABILITY_RESULT_COLUMNS = [
    "feature_name",
    "selection_freq",
    "is_stable",
    "selection_method",
    "selection_alpha",
    "noise_baseline",
]


class StabilitySelector:
    """稳定性选择器：通过多次子采样 + Lasso 筛选稳定描述符。

    算法流程：
    1. 每次自举：随机抽取 fraction 比例的样本（无放回）
    2. 在子样本内部做中位数填充、标准化并拟合 Lasso
    3. 按 Lasso 非零系数判断"被选中"
    4. 统计每个特征在 n_bootstrap 次迭代中被选中的频率
    5. 若提供了噪声列，用噪声频率的 95 分位数作为基线校准
    """

    def __init__(
        self,
        n_bootstrap: int = 100,
        threshold: float = 0.6,
        fraction: float = 0.5,
        alpha: float = 1.0,
        seed: int = 42,
    ) -> None:
        """初始化稳定性选择器。

        参数:
            n_bootstrap: 自举迭代次数，越多越稳定但越慢
            threshold: 选中频率阈值，高于此值视为稳定描述符
            fraction: 每次自举的采样比例（0.5 = 抽一半样本）
            alpha: Lasso 选择正则化强度，越大选择越稀疏
            seed: 随机种子，保证可复现
        """
        self.n_bootstrap = n_bootstrap
        self.threshold = threshold
        self.fraction = fraction
        self.alpha = alpha
        self.seed = seed

    def _result_metadata(
        self,
        noise_baseline: float,
        noise_baseline_reason: str | None = None,
    ) -> dict[str, object]:
        """Return metadata shared by populated and schema-only results."""
        return {
            "selection_method": "subsampled_lasso",
            "selection_alpha": float(self.alpha),
            "preprocessing": ["median_imputation", "standard_scaling"],
            "noise_baseline": float(noise_baseline),
            "noise_baseline_reason": noise_baseline_reason,
            "noise_baseline_quantile": 0.95,
            "n_subsamples": int(self.n_bootstrap),
            "subsample_fraction": float(self.fraction),
            "seed": int(self.seed),
        }

    def run(
        self,
        X_real: np.ndarray,
        y: np.ndarray,
        X_noise: np.ndarray | None = None,
        real_col_names: list[str] | None = None,
        noise_col_names: list[str] | None = None,
    ) -> pd.DataFrame:
        """运行稳定性选择。

        参数:
            X_real: 原始真实描述符矩阵 (n_samples, n_real_features)，可含缺失值
            y: 目标向量 log_sigma (n_samples,)
            X_noise: 噪声列矩阵 (n_samples, n_noise)，用于基线校准
            real_col_names: 真实描述符列名列表
            noise_col_names: 噪声列列名列表

        返回:
            DataFrame，每行一个特征，包含:
            - feature_name: 特征名
            - selection_freq: 被选中的频率 (0~1)
            - is_stable: 频率是否 > threshold
        """
        n_samples, n_real = X_real.shape

        # 生成默认列名
        if real_col_names is None:
            real_col_names = [f"real_{i}" for i in range(n_real)]
        if noise_col_names is None and X_noise is not None:
            n_noise = X_noise.shape[1]
            noise_col_names = [f"noise_{i}" for i in range(n_noise)]

        # 拼接真实描述符和噪声列（若提供）
        if X_noise is not None:
            X_all = np.hstack([X_real, X_noise])
            all_names = list(real_col_names) + list(noise_col_names)
        else:
            X_all = X_real
            all_names = list(real_col_names)

        n_features = X_all.shape[1]
        selection_counts = np.zeros(n_features, dtype=int)

        if n_features == 0:
            empty_result = pd.DataFrame(columns=STABILITY_RESULT_COLUMNS)
            empty_result.attrs.update(self._result_metadata(
                noise_baseline=float("nan"),
                noise_baseline_reason="empty_feature_matrix",
            ))
            return empty_result

        # 每次自举的样本数
        subset_size = max(2, int(n_samples * self.fraction))

        rng = np.random.RandomState(self.seed)

        for _ in range(self.n_bootstrap):
            # 无放回采样
            indices = rng.choice(n_samples, size=subset_size, replace=False)
            X_sub = X_all[indices]
            y_sub = y[indices]

            # 每个子样本独立拟合预处理，避免全数据填充/缩放泄漏。
            model = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("lasso", Lasso(alpha=self.alpha, max_iter=20_000)),
            ])
            model.fit(X_sub, y_sub)
            coefs = model.named_steps["lasso"].coef_
            selected = np.abs(coefs) > 1e-12
            selection_counts += selected.astype(int)

        # 计算选中频率
        selection_freq = selection_counts / self.n_bootstrap

        # 计算噪声基线
        if X_noise is not None:
            n_real_feat = n_real
            noise_freqs = selection_freq[n_real_feat:]
            # 噪声基线 = 噪声列选中频率的 95 分位数
            if len(noise_freqs) > 0:
                noise_baseline = float(np.percentile(noise_freqs, 95))
                noise_baseline_reason = None
            else:
                noise_baseline = float("nan")
                noise_baseline_reason = "no_noise_frequencies_recorded"
        else:
            noise_baseline = float("nan")
            noise_baseline_reason = "no_noise_columns_configured"

        # 构建结果 DataFrame
        records = []
        for i, name in enumerate(all_names):
            freq = float(selection_freq[i])
            is_real = i < n_real

            records.append({
                "feature_name": name,
                "selection_freq": freq,
                "is_stable": freq > self.threshold,
                "is_noise": not is_real,
                "selection_method": "subsampled_lasso",
                "selection_alpha": float(self.alpha),
                "noise_baseline": noise_baseline,
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=[*STABILITY_RESULT_COLUMNS, "is_noise"],
        )

        # 仅返回真实描述符的结果（噪声列信息已用于计算基线）
        real_df = result_df[~result_df["is_noise"]].drop(columns=["is_noise"]).reset_index(drop=True)
        real_df.attrs.update(self._result_metadata(
            noise_baseline,
            noise_baseline_reason=noise_baseline_reason,
        ))

        return real_df


class PhysicalGrouper:
    """物理族代表选择器：从稳定描述符中按物理族挑选代表。

    策略（errata P4）：
    - 八大物理族 A, B, C, D', E, F, G, H
    - 每族默认最多选 max_per_family 个代表
    - 代表 = 族内稳定性通过 + |线性残差秩相关| 最高的描述符
    - ``max_per_family`` 是硬上限；不以缺失族为由扩容

    注意：D' 族在代码中用 "D_prime" 表示。
    """

    def __init__(self, max_per_family: int = 1) -> None:
        """初始化物理族选择器。

        参数:
            max_per_family: 每族最大代表数，默认 1（errata P4）
        """
        self.max_per_family = max_per_family

    def group_and_select(
        self,
        stability_df: pd.DataFrame,
        deconfound_df: pd.DataFrame,
        descriptor_registry: dict[str, tuple] | None = None,
    ) -> pd.DataFrame:
        """按物理族分组并选择代表描述符。

        参数:
            stability_df: StabilitySelector.run() 的输出 DataFrame
                必须包含 feature_name, selection_freq, is_stable
            deconfound_df: 去混杂结果 DataFrame
                必须包含 descriptor (列名=特征名), rank_corr_of_linear_residuals
            descriptor_registry: 描述符注册表，默认使用 SEARCHABLE_STRUCTURE_DESCRIPTORS
                格式: {name: (compute_func, family_key, is_high_risk)}

        返回:
            DataFrame，每行一个稳定描述符，包含:
            - descriptor: 描述符名
            - family: 所属物理族 (A/B/C/D_prime/E/F/G/H)
            - family_name: 物理族中文名
            - rank_corr_of_linear_residuals: 线性残差秩相关 rho
            - selection_freq: 稳定性选中频率
            - is_stable: 是否通过稳定性阈值
            - is_representative: 是否被选为族代表
        """
        if descriptor_registry is None:
            descriptor_registry = SEARCHABLE_STRUCTURE_DESCRIPTORS

        # 构建描述符 → 物理族映射
        desc_to_family: dict[str, str] = {}
        for name, (_, family_key, _) in descriptor_registry.items():
            desc_to_family[name] = family_key

        # 合并稳定性结果和去混杂结果
        # stability_df 用 feature_name，deconfound_df 用 descriptor 列名
        merged = stability_df.merge(
            deconfound_df,
            left_on="feature_name",
            right_on="descriptor",
            how="left",
        )

        # fail-fast：断言必需列存在，列名消失（如重命名遗漏）会让全部描述符静默变成
        # selection_freq=0.0, is_stable=False 且不报错。本项目已做过两次重命名。
        # deconfound_status / skip_reason / n_valid 同样必需——它们的唯一用途就是
        # 让"未算"与"算出来了"可区分，用带默认值的 .get() 取它们等于新造一条静默回退。
        required_columns = [
            "selection_freq",
            "is_stable",
            "rank_corr_of_linear_residuals",
            "deconfound_status",
            "skip_reason",
            "n_valid",
        ]
        missing_columns = [c for c in required_columns if c not in merged.columns]
        if missing_columns:
            raise ValueError(
                "group_and_select: merge 后缺少必需列: "
                f"{missing_columns}，可能由列重命名遗漏导致"
            )

        # 填充物理族信息
        records = []
        for _, row in merged.iterrows():
            desc_name = row["feature_name"]
            family_key = desc_to_family.get(desc_name, "unknown")
            family_info = PHYSICAL_FAMILIES.get(family_key, {})
            family_name = family_info.get("name", "unknown")

            records.append({
                "descriptor": desc_name,
                "family": family_key,
                "family_name": family_name,
                "rank_corr_of_linear_residuals": row["rank_corr_of_linear_residuals"],
                "selection_freq": row["selection_freq"],
                "is_stable": row["is_stable"],
                "is_representative": False,
                "deconfound_status": row["deconfound_status"],
                "skip_reason": row["skip_reason"],
                "n_valid": row["n_valid"],
            })

        result_df = pd.DataFrame.from_records(
            records,
            columns=PHYSICAL_GROUP_RESULT_COLUMNS,
        )
        result_df.attrs.update(stability_df.attrs)
        result_df.attrs.update(deconfound_df.attrs)

        if result_df.empty:
            return result_df

        # 筛选: 稳定的描述符才参与代表选择
        eligible = result_df[result_df["is_stable"]]

        # 按物理族分组
        family_groups = eligible.groupby("family")

        # 第一轮: 每族选 rank_corr_of_linear_residuals 最高的代表
        representatives: set[str] = set()

        for family_key in PHYSICAL_FAMILIES:
            if family_key not in family_groups.groups:
                continue

            group = family_groups.get_group(family_key)
            if group.empty:
                continue

            # 代表按 |rho| 排名，但输出保留 rank_corr_of_linear_residuals 的符号。
            top = group.loc[
                group["rank_corr_of_linear_residuals"].abs().nlargest(self.max_per_family).index
            ]
            representatives.update(top["descriptor"].tolist())

        # 标记代表
        result_df["is_representative"] = result_df["descriptor"].isin(representatives)

        return result_df
