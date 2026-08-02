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
- 代表 = 该族中稳定性通过且去混杂 Spearman 最高的描述符
- 若某族无稳定描述符，允许其他族增至 max_per_family+1
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

# 描述符注册表和物理族定义
from descriptors import AVAILABLE_STRUCTURE_DESCRIPTORS
from descriptors._base import PHYSICAL_FAMILIES


class StabilitySelector:
    """稳定性选择器：通过多次自举 + Ridge 回归筛选稳定描述符。

    算法流程：
    1. 每次自举：随机抽取 fraction 比例的样本（无放回）
    2. 对子样本拟合 Ridge 回归
    3. 按系数绝对值大于中位数的标准判断"被选中"
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
            alpha: Ridge 正则化强度，越大系数越收缩
            seed: 随机种子，保证可复现
        """
        self.n_bootstrap = n_bootstrap
        self.threshold = threshold
        self.fraction = fraction
        self.alpha = alpha
        self.seed = seed

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
            X_real: 真实描述符矩阵 (n_samples, n_real_features)，应已标准化
            y: 目标向量 log_sigma (n_samples,)
            X_noise: 噪声列矩阵 (n_samples, n_noise)，用于基线校准
            real_col_names: 真实描述符列名列表
            noise_col_names: 噪声列列名列表

        返回:
            DataFrame，每行一个特征，包含:
            - feature_name: 特征名
            - selection_freq: 被选中的频率 (0~1)
            - is_stable: 频率是否 > threshold
            - above_noise_baseline: 频率是否 > 噪声基线（无噪声列时为 True）
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

        # 每次自举的样本数
        subset_size = max(2, int(n_samples * self.fraction))

        rng = np.random.RandomState(self.seed)

        for _ in range(self.n_bootstrap):
            # 无放回采样
            indices = rng.choice(n_samples, size=subset_size, replace=False)
            X_sub = X_all[indices]
            y_sub = y[indices]

            # 拟合 Ridge 回归
            model = Ridge(alpha=self.alpha, random_state=rng)
            model.fit(X_sub, y_sub)
            coefs = np.abs(model.coef_)

            # 选择标准: |coef| > median(|coef|)
            # 这是简单的"上半区"筛选，避免设定硬阈值
            if coefs.max() < 1e-12:
                # 所有系数接近零（极端情况），本轮无选中
                continue
            median_coef = np.median(coefs)
            selected = coefs > median_coef
            selection_counts += selected.astype(int)

        # 计算选中频率
        selection_freq = selection_counts / self.n_bootstrap

        # 计算噪声基线
        if X_noise is not None:
            n_real_feat = n_real
            noise_freqs = selection_freq[n_real_feat:]
            # 噪声基线 = 噪声列选中频率的 95 分位数
            noise_baseline = float(np.percentile(noise_freqs, 95)) if len(noise_freqs) > 0 else 0.0
        else:
            noise_baseline = 0.0

        # 构建结果 DataFrame
        records = []
        for i, name in enumerate(all_names):
            freq = float(selection_freq[i])
            is_real = i < n_real

            # above_noise_baseline: 真实描述符需要 > 噪声基线
            # 噪声列本身不参与此判断
            if is_real:
                above_baseline = freq > noise_baseline
            else:
                above_baseline = True  # 噪声列标记为 True，不影响筛选

            records.append({
                "feature_name": name,
                "selection_freq": freq,
                "is_stable": freq > self.threshold,
                "above_noise_baseline": above_baseline,
                "is_noise": not is_real,
            })

        result_df = pd.DataFrame(records)

        # 仅返回真实描述符的结果（噪声列信息已用于计算基线）
        real_df = result_df[~result_df["is_noise"]].drop(columns=["is_noise"]).reset_index(drop=True)

        return real_df


class PhysicalGrouper:
    """物理族代表选择器：从稳定描述符中按物理族挑选代表。

    策略（errata P4）：
    - 八大物理族 A, B, C, D', E, F, G, H
    - 每族默认最多选 max_per_family 个代表
    - 代表 = 族内稳定性通过 + 去混杂 Spearman 最高的描述符
    - 若某族无稳定描述符，允许其他族增加名额

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
                必须包含 feature_name, selection_freq, is_stable, above_noise_baseline
            deconfound_df: 去混杂结果 DataFrame
                必须包含 descriptor (列名=特征名), deconfounded_spearman
            descriptor_registry: 描述符注册表，默认使用 AVAILABLE_STRUCTURE_DESCRIPTORS
                格式: {name: (compute_func, family_key, is_high_risk)}

        返回:
            DataFrame，每行一个稳定描述符，包含:
            - descriptor: 描述符名
            - family: 所属物理族 (A/B/C/D_prime/E/F/G/H)
            - family_name: 物理族中文名
            - deconfounded_spearman: 去混杂 Spearman rho
            - selection_freq: 稳定性选中频率
            - is_stable: 是否通过稳定性阈值
            - above_noise_baseline: 是否超过噪声基线
            - is_representative: 是否被选为族代表
        """
        if descriptor_registry is None:
            descriptor_registry = AVAILABLE_STRUCTURE_DESCRIPTORS

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

        # 填充物理族信息
        records = []
        for _, row in merged.iterrows():
            desc_name = row["feature_name"]
            family_key = desc_to_family.get(desc_name, "unknown")
            family_info = PHYSICAL_FAMILIES.get(family_key, {})
            family_name = family_info.get("name", "未知")

            records.append({
                "descriptor": desc_name,
                "family": family_key,
                "family_name": family_name,
                "deconfounded_spearman": row.get("deconfounded_spearman", float("nan")),
                "selection_freq": row.get("selection_freq", 0.0),
                "is_stable": row.get("is_stable", False),
                "above_noise_baseline": row.get("above_noise_baseline", True),
                "is_representative": False,
            })

        result_df = pd.DataFrame(records)

        # 筛选: 稳定 + 超过噪声基线的描述符才参与代表选择
        eligible = result_df[result_df["is_stable"] & result_df["above_noise_baseline"]]

        # 按物理族分组
        family_groups = eligible.groupby("family")

        # 第一轮: 每族选 deconfounded_spearman 最高的代表
        representatives: set[str] = set()
        families_with_rep: set[str] = set()
        families_without_rep: set[str] = set()

        for family_key in PHYSICAL_FAMILIES:
            if family_key not in family_groups.groups:
                families_without_rep.add(family_key)
                continue

            group = family_groups.get_group(family_key)
            if group.empty:
                families_without_rep.add(family_key)
                continue

            # 按去混杂 Spearman 降序排列，取前 max_per_family 个
            top = group.nlargest(self.max_per_family, "deconfounded_spearman")
            representatives.update(top["descriptor"].tolist())
            families_with_rep.add(family_key)

        # 第二轮: 若有族无代表，允许其他族增加名额
        if families_without_rep:
            # 空缺族数决定可追加的名额
            extra_slots = len(families_without_rep) * self.max_per_family
            extra_per_family = self.max_per_family  # 每族可多选 1 个

            for family_key in families_with_rep:
                if extra_slots <= 0:
                    break

                group = family_groups.get_group(family_key)
                # 已选代表
                already_selected = group[group["descriptor"].isin(representatives)]
                remaining = group[~group["descriptor"].isin(representatives)]

                if remaining.empty:
                    continue

                # 从剩余中再选 extra_per_family 个
                additional = remaining.nlargest(
                    min(extra_per_family, extra_slots),
                    "deconfounded_spearman",
                )
                representatives.update(additional["descriptor"].tolist())
                extra_slots -= len(additional)

        # 标记代表
        result_df["is_representative"] = result_df["descriptor"].isin(representatives)

        return result_df
