【会话指示 - experiment-audit】

1. 本模板为单轮一次性审计。复制下方"prompt 正文"全部内容（从 `--- prompt 正文开始 ---` 到 `--- prompt 正文结束 ---`），粘贴到新的 Claude 对话中。
2. 审稿人返回回复后，复制回复全文回执行器（本 GLM），执行器解析后写入 aris/EXPERIMENT_AUDIT.md 和 aris/EXPERIMENT_AUDIT.json。
3. 单一对话完成所有检查项——不要分多次对话。
4. 如需对单一检查项追问细节，可在同一对话中继续。
5. 何时开新对话：仅当需要重新审计（不同时间点的代码状态）时开新对话。
6. 本次使用的清单 profile：stat-pipeline（A–H 共 8 项检查）
7. 本次审计范围（部分审计 partial）：
   - 已嵌入：descriptors/deconfound.py、descriptors/stability.py、descriptors/_base.py、run_pipeline.py、run_info.yaml
   - 已排除：results/（结果目录）、data/naconductor_featurized.csv（特征化数据）

--- prompt 正文开始 ---

You are a statistical pipeline integrity auditor. Read ALL file contents
below and check for the following failure patterns. This is a code and
design audit — judge the pipeline's logic, not the numerical values it
currently produces.

## 你的任务

按以下审计清单逐项检查，每项报告 Status (PASS | WARN | FAIL | NOT_APPLICABLE)、
Evidence (精确的 file:line 引用)、Details (具体发现)。

若某项所需的文件未在本 prompt 中提供，报 NOT_APPLICABLE 并说明缺什么，
不要因文件缺失而报 FAIL。

## 审计清单

### A. Target Variable Provenance
1. Where does the target variable come from — a single measurement protocol,
   or aggregated across heterogeneous sources?
2. If aggregated: are units, conditions, and measurement methods commensurable?
   Is any source-level attribute (instrument, temperature, sample preparation)
   likely to correlate with the predictors?
3. Is any preprocessing applied to the target (log, clipping, imputation) that
   could induce or destroy structure?
FAIL if: heterogeneous sources are pooled with no stated commensurability argument.

### B. Metric Self-Reference
1. Is any reported statistic normalized by a quantity derived from the same fit
   or the same data subset?
2. Does any composite or aggregate metric discard sign, direction, or ordering
   information that the pipeline elsewhere treats as decisive?
3. Are raw and derived statistics both reported, or only the derived one?
FAIL if: a composite score can reward a result that another part of the pipeline
would classify as a failure.

### C. Result File Existence
1. Does every referenced result file exist and contain the referenced key?
2. Does the claimed number match the file?
3. Are committed data files real outputs, or placeholders?
FAIL if: claimed results reference nonexistent files or mismatched numbers.
NOT_APPLICABLE if: no result files were provided for audit.

### D. Dead Path Detection
1. Is every defined stage, filter, or selection rule actually applied in the
   executed pipeline?
2. Does each stage's declared output feed the next stage's declared input?
   Trace the row/column counts end to end and report any point where the count
   entering a stage cannot be produced by the stage before it.
3. Are any defined functions, thresholds, or config keys never referenced?
FAIL if: a declared filter is documented as applied but is bypassed in code.

### E. Scope and Multiplicity
1. How many samples, groups, and repeats does the analysis actually use?
2. How many hypotheses / features / candidate combinations are examined?
3. Is any correction applied for examining many candidates and reporting the best?
4. Does the surrounding prose use words like "robust", "stable", "systematic"?
   Is the actual scope sufficient for that language?
WARN if: scope language exceeds actual evidence.
FAIL if: a best-of-N statistic is reported with no multiplicity control.

### F. Threshold Provenance
1. For every hard-coded numeric threshold, is there a stated justification?
2. Is that justification independent of the data (theory, prior literature,
   pre-specified convention) or derived from inspecting results?
3. Would the reported conclusion change under a modest perturbation of each
   threshold? Is any such sensitivity check present?
FAIL if: thresholds are undocumented AND the conclusion is threshold-sensitive.

### G. Null Distribution and Selection Effects
1. Is there any empirical null — permutation, randomization, or injected
   noise controls?
2. If controls exist, are they applied at the stage where selection actually
   happens, or only at a later stage?
3. Under the pipeline's own selection rule, what selection rate would a pure
   noise variable achieve by construction? Compute it if the rule permits.
4. Is the reported headline statistic compared against that null?
FAIL if: no null exists for a selection-based claim.
WARN if: a null exists but is applied at the wrong stage or has too few controls
to estimate the quoted quantile stably.

### H. Randomness and Reproducibility
1. Are all seeds fixed and recorded?
2. Are resampling, splitting, and shuffling deterministic given the seed?
3. Is the same seed reused across steps in a way that creates dependence
   between supposedly independent procedures?
4. Does the code's actual behaviour match the configuration files that describe it?
FAIL if: config files and code describe different procedures.

## 文件内容

--- 文件开始: descriptors/deconfound.py ---
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
--- 文件结束: descriptors/deconfound.py ---

--- 文件开始: descriptors/stability.py ---
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
- 代表 = 该族中稳定性通过且 |去混杂 Spearman| 最高的描述符（保留符号）
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
    "deconfounded_spearman",
    "selection_freq",
    "is_stable",
    "above_noise_baseline",
    "is_representative",
]

STABILITY_RESULT_COLUMNS = [
    "feature_name",
    "selection_freq",
    "is_stable",
    "above_noise_baseline",
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

    def _result_metadata(self, noise_baseline: float) -> dict[str, object]:
        """Return metadata shared by populated and schema-only results."""
        return {
            "selection_method": "subsampled_lasso",
            "selection_alpha": float(self.alpha),
            "preprocessing": ["median_imputation", "standard_scaling"],
            "noise_baseline": float(noise_baseline),
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

        if n_features == 0:
            empty_result = pd.DataFrame(columns=STABILITY_RESULT_COLUMNS)
            empty_result.attrs.update(self._result_metadata(noise_baseline=0.0))
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
        real_df.attrs.update(self._result_metadata(noise_baseline))

        return real_df


class PhysicalGrouper:
    """物理族代表选择器：从稳定描述符中按物理族挑选代表。

    策略（errata P4）：
    - 八大物理族 A, B, C, D', E, F, G, H
    - 每族默认最多选 max_per_family 个代表
    - 代表 = 族内稳定性通过 + |去混杂 Spearman| 最高的描述符
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
                必须包含 feature_name, selection_freq, is_stable, above_noise_baseline
            deconfound_df: 去混杂结果 DataFrame
                必须包含 descriptor (列名=特征名), deconfounded_spearman
            descriptor_registry: 描述符注册表，默认使用 SEARCHABLE_STRUCTURE_DESCRIPTORS
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

        result_df = pd.DataFrame.from_records(
            records,
            columns=PHYSICAL_GROUP_RESULT_COLUMNS,
        )
        result_df.attrs.update(stability_df.attrs)
        result_df.attrs.update(deconfound_df.attrs)

        if result_df.empty:
            return result_df

        # 筛选: 稳定 + 超过噪声基线的描述符才参与代表选择
        eligible = result_df[result_df["is_stable"] & result_df["above_noise_baseline"]]

        # 按物理族分组
        family_groups = eligible.groupby("family")

        # 第一轮: 每族选 deconfounded_spearman 最高的代表
        representatives: set[str] = set()

        for family_key in PHYSICAL_FAMILIES:
            if family_key not in family_groups.groups:
                continue

            group = family_groups.get_group(family_key)
            if group.empty:
                continue

            # 代表按 |rho| 排名，但输出保留 deconfounded_spearman 的符号。
            top = group.loc[
                group["deconfounded_spearman"].abs().nlargest(self.max_per_family).index
            ]
            representatives.update(top["descriptor"].tolist())

        # 标记代表
        result_df["is_representative"] = result_df["descriptor"].isin(representatives)

        return result_df
--- 文件结束: descriptors/stability.py ---

--- 文件开始: descriptors/_base.py ---
"""结构描述符基础工具与物理族定义。

提供描述符计算所需的公共辅助函数、物理族定义、跨组约束规则，
以及 Shannon 有效离子半径、阴离子集合等常量。
"""
from __future__ import annotations

import warnings
from collections import Counter

import numpy as np
from pymatgen.core import Structure
from scipy.spatial import Voronoi

# ============================================================
# 阴离子元素集合
# ============================================================
ANION_ELEMENTS: set[str] = {"O", "S", "Se", "F", "Cl", "Br", "I", "N", "H"}

# ============================================================
# Na+ 有效离子半径 (Å)，按配位数索引
# 来源: Shannon 经典有效离子半径表
# ============================================================
NA_EFFECTIVE_RADII_A: dict[int, float] = {
    4: 0.99,
    5: 1.00,
    6: 1.02,
    7: 1.12,
    8: 1.18,
    9: 1.24,
    12: 1.39,
}
NA_FALLBACK_CN = 6

# ============================================================
# 阴离子有效离子半径 (Å)，N 无经典值故为 None
# ============================================================
ANION_EFFECTIVE_RADII_A: dict[str, float | None] = {
    "O": 1.40,
    "S": 1.84,
    "Se": 1.98,
    "F": 1.33,
    "Cl": 1.81,
    "Br": 1.96,
    "I": 2.20,
    "H": 1.40,
    "N": None,
}

# ============================================================
# 电负性 (Pauling 标度)，用于 G 族电子代理描述符
# ============================================================
ELECTRONEGATIVITY: dict[str, float] = {
    "Na": 0.93,
    "O": 3.44,
    "S": 2.58,
    "F": 3.98,
    "Cl": 3.16,
    "Br": 2.96,
    "I": 2.66,
    "Se": 2.55,
    "N": 3.04,
    "H": 2.20,
}

# ============================================================
# 八大物理族定义
# ============================================================
PHYSICAL_FAMILIES: dict[str, dict[str, str]] = {
    "A": {"name": "Na多面体", "module": "family_a_polyhedron"},
    "B": {"name": "Na-Na网络", "module": "family_b_network"},
    "C": {"name": "Na浓度", "module": "family_c_concentration"},
    "D_prime": {"name": "空位拓扑", "module": "family_d_vacancy_topo"},
    "E": {"name": "骨架刚性", "module": "family_e_framework"},
    "F": {"name": "长程关联", "module": "family_f_longrange"},
    "G": {"name": "电子代理", "module": "family_g_electronic"},
    "H": {"name": "对称性破缺", "module": "family_h_symmetry"},
}

# ============================================================
# 跨组组合约束
# ============================================================
CROSS_GROUP_RULES: dict[str, object] = {
    # 允许的跨组对
    "allowed_pairs": [
        ("A", "B"),
        ("A", "D_prime"),
        ("A", "C"),
        ("B", "D_prime"),
        ("A", "H"),
        ("E", "A"),
    ],
    # 高风险族
    "high_risk_families": ["G", "H"],
    # 特殊限制: A↔C 仅允许比率运算，不允许乘法
    "per_operator_restrictions": {
        ("A", "C"): {"allowed_ops": ["ratio"], "forbidden_ops": ["multiply"]},
    },
}


# ============================================================
# 辅助函数
# ============================================================

def element_symbol(value: object) -> str:
    """Return an element symbol for an Element, Species, or species name."""
    symbol = getattr(value, "symbol", None)
    if symbol is not None:
        return str(symbol)
    return str(value).rstrip("+-0123456789")


def site_occupancies_by_symbol(site) -> dict[str, float]:
    """Aggregate a site's occupancies by charge-independent element symbol."""
    totals: dict[str, float] = {}
    for species, occupancy in site.species.items():
        symbol = element_symbol(species)
        totals[symbol] = totals.get(symbol, 0.0) + float(occupancy)
    return totals

def get_na_sites(struct: Structure) -> list[int]:
    """获取结构中 Na 位点的索引列表。

    Na 位点 = 主要物种为 Na 的位点（考虑部分占位）。
    """
    na_indices: list[int] = []
    for i, site in enumerate(struct):
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        if na_occ > 1e-6:
            na_indices.append(i)
    return na_indices


def get_anion_sites(struct: Structure) -> list[int]:
    """获取结构中阴离子位点的索引列表。"""
    anion_indices: list[int] = []
    for i, site in enumerate(struct):
        for symbol in site_occupancies_by_symbol(site):
            if symbol in ANION_ELEMENTS:
                anion_indices.append(i)
                break
    return anion_indices


def get_framework_sites(struct: Structure) -> list[int]:
    """获取骨架位点索引：非 Na、非阴离子的位点。"""
    na_set = set(get_na_sites(struct))
    anion_set = set(get_anion_sites(struct))
    return [i for i in range(len(struct)) if i not in na_set and i not in anion_set]


def _major_species(site) -> str:
    """获取位点上占位最多的元素符号。"""
    species_dict = site_occupancies_by_symbol(site)
    if not species_dict:
        return ""
    return max(species_dict.items(), key=lambda kv: kv[1])[0]


def _site_occ(site, symbol: str) -> float:
    """获取位点上某元素的占位数。"""
    return site_occupancies_by_symbol(site).get(symbol, 0.0)


def get_na_x_bonds(
    struct: Structure,
    na_idx: int,
    max_dist: float = 4.0,
) -> list[tuple[int, float]]:
    """获取 Na 位点与近邻阴离子的键信息。

    参数:
        struct: pymatgen Structure 对象
        na_idx: Na 位点索引
        max_dist: 最大搜索距离 (Å)

    返回:
        (anion_site_idx, distance) 列表，按距离升序
    """
    center = struct[na_idx]
    raw = struct.get_sites_in_sphere(
        center.coords, max_dist, include_index=True, include_image=True
    )
    bonds: list[tuple[int, float]] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == na_idx and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            if idx is not None:
                bonds.append((idx, dist))
    bonds.sort(key=lambda x: x[1])
    return bonds


def _anion_cutoff(anion_symbols: set[str]) -> float:
    """根据阴离子类型确定截断距离 (Å)。"""
    cutoffs = {
        "O": 3.20, "F": 3.20, "N": 3.35,
        "S": 3.85, "Cl": 3.85, "H": 3.20,
        "Se": 4.05, "Br": 4.05, "I": 4.35,
    }
    return max((cutoffs.get(sym, 4.0) for sym in anion_symbols), default=4.0)


def _shell_neighbors(
    struct: Structure,
    center_index: int,
    anion_symbols: set[str],
) -> list[dict]:
    """提取 Na 位点的第一配位壳层 Na-X 近邻。

    沿用 part1.py 的简化规则: 取最短键长 +0.70Å 内的阴离子，
    若不足 4 个则补至 4。
    """
    center = struct[center_index]
    cutoff = _anion_cutoff(anion_symbols)
    raw = struct.get_sites_in_sphere(
        center.coords, cutoff, include_index=True, include_image=True
    )
    center_coords = np.array(center.coords, dtype=float)
    neighbors: list[dict] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == center_index and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            coords_arr = np.array(site.coords, dtype=float)
            neighbors.append({
                "symbol": sym, "distance": dist,
                "coords": coords_arr, "index": idx,
            })
    neighbors.sort(key=lambda x: x["distance"])
    if not neighbors:
        return []
    first = neighbors[0]["distance"]
    kept = [n for n in neighbors if n["distance"] <= first + 0.70]
    if len(kept) <= 3 and len(neighbors) > len(kept):
        kept = neighbors[:min(4, len(neighbors))]
    return kept


def _effective_na_radius(cn: int | None) -> float:
    """根据配位数返回 Na+ 有效离子半径 (Å)。

    未列入的 CN 使用 CN=6 的默认值。
    """
    if cn is not None and cn in NA_EFFECTIVE_RADII_A:
        return NA_EFFECTIVE_RADII_A[cn]
    return NA_EFFECTIVE_RADII_A[NA_FALLBACK_CN]


def _effective_anion_radius(anion_symbols: set[str]) -> float | None:
    """计算阴离子有效离子半径加权平均值 (Å)。

    若阴离子中包含 N（无经典值），返回 None。
    """
    if not anion_symbols:
        return None
    values: list[tuple[str, float]] = []
    missing: list[str] = []
    for sym in sorted(anion_symbols):
        r = ANION_EFFECTIVE_RADII_A.get(sym)
        if r is None:
            missing.append(sym)
        else:
            values.append((sym, r))
    if missing or not values:
        return None
    return sum(r for _, r in values) / len(values)


def find_interstitial_sites(
    struct: Structure,
    min_dist_from_atom: float = 1.5,
) -> list[dict]:
    """用 scipy.spatial.Voronoi 寻找周期性晶胞中的间隙位点。

    算法 (errata P2 修正):
    1. 将所有原子坐标转为笛卡尔坐标
    2. 生成周期性影像 (±1 个晶胞在三个方向)
    3. 对所有点（原始+影像）做 Voronoi 剖分
    4. 筛选 Voronoi 顶点: 仅保留在原胞内的顶点，
       且该顶点与最近原子距离 >= min_dist_from_atom

    返回:
        间隙位点列表，每个元素为 {"coords": np.ndarray, "volume": float}
        coords 为笛卡尔坐标 (Å)，volume 为对应 Voronoi 区域体积 (Å³)
    """
    if len(struct) == 0:
        return []

    # 原始原子笛卡尔坐标
    cart_coords = np.array([site.coords for site in struct], dtype=float)
    lattice = struct.lattice

    # 生成周期性影像
    all_points: list[np.ndarray] = [cart_coords]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                if i == 0 and j == 0 and k == 0:
                    continue
                shift = i * lattice.matrix[0] + j * lattice.matrix[1] + k * lattice.matrix[2]
                all_points.append(cart_coords + shift)

    all_points_arr = np.vstack(all_points)

    # Voronoi 剖分
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            vor = Voronoi(all_points_arr)
    except Exception:
        return []

    interstitial_sites: list[dict] = []
    for vertex in vor.vertices:
        # 检查是否在原胞内 (用分数坐标)
        frac = lattice.get_fractional_coords(vertex)
        in_cell = all(-1e-6 <= f < 1.0 - 1e-6 for f in frac)
        if not in_cell:
            continue

        # 周期性影像已包含在 Voronoi 点集中；用其检查最近原子距离。
        dists = np.linalg.norm(all_points_arr - vertex, axis=1)
        min_dist = float(np.min(dists))
        if min_dist < min_dist_from_atom:
            continue

        interstitial_sites.append({
            "coords": np.array(vertex, dtype=float),
            "volume": 0.0,
        })

    # 去重: 同一区域可能因周期性影像重复出现
    if len(interstitial_sites) > 1:
        unique: list[dict] = [interstitial_sites[0]]
        for site in interstitial_sites[1:]:
            is_dup = False
            for u in unique:
                site_frac = lattice.get_fractional_coords(site["coords"])
                unique_frac = lattice.get_fractional_coords(u["coords"])
                distance, _image = lattice.get_distance_and_image(site_frac, unique_frac)
                if float(distance) < 0.5:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(site)
        interstitial_sites = unique

    return interstitial_sites


def compute_polyhedron_volume(struct: Structure, na_idx: int) -> float:
    """计算 Na 位点的 Voronoi 多面体体积 (Å³)。

    使用 pymatgen 的 VoronoiNN 计算配位多面体体积。
    """
    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        poly_info = vnn.get_voronoi_polyhedra(struct, na_idx)
        total_vol = 0.0
        for neighbor_info in poly_info.values():
            total_vol += neighbor_info.get("volume", 0.0)
        return float(total_vol) if total_vol > 0 else float("nan")
    except Exception:
        return float("nan")


def _safe_mean(values: list[float]) -> float:
    """安全求均值，空列表返回 NaN。"""
    if not values:
        return float("nan")
    return float(np.mean(values))


def _safe_std(values: list[float]) -> float:
    """安全求标准差，空列表返回 NaN。"""
    if len(values) < 2:
        return float("nan")
    return float(np.std(values, ddof=0))


def _safe_cv(values: list[float]) -> float:
    """安全求变异系数 (CV=std/mean)，空列表或零均值返回 NaN。"""
    if not values:
        return float("nan")
    m = float(np.mean(values))
    if abs(m) < 1e-12:
        return float("nan")
    return float(np.std(values, ddof=0) / m)
--- 文件结束: descriptors/_base.py ---

--- 文件开始: run_pipeline.py ---
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""4阶段管线：从原始数据到最终报告。

用法（在 automat-naconductor 目录下运行）:
    python run_pipeline.py
    python run_pipeline.py --skip-featurize    # 跳过Stage 0（已有特征化数据）
    python run_pipeline.py --top-k 20          # 验证前20个组合（默认10）

4个阶段:
    Stage 0: 特征化（compute_features.py的等价脚本版）
    Stage 1: 单描述符筛选（去混杂分析）
    Stage 2: 稳定性选择 + 物理族代表
    Stage 3: 约束组合搜索
    Stage 4: 多策略CV验证 + 最终报告
"""
from __future__ import annotations

import sys
sys.stdout.reconfigure(encoding='utf-8')

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from automat_utils import resolve_frozen_input_identity
from descriptors import SEARCHABLE_STRUCTURE_DESCRIPTORS
from descriptors.featurizer import featurize_dataset, build_feature_matrix
from descriptors.deconfound import DeconfoundAnalyzer
from descriptors.stability import StabilitySelector, PhysicalGrouper
from descriptors.combination import (
    CombinationValidator,
    ConstrainedCombinationSearch,
    combination_candidates_to_csv_frame,
    combination_validation_to_csv_frame,
)
from descriptors.cv_strategies import (
    CV_SPEARMAN_SUMMARY_COLUMNS,
    MultiStrategyCV,
    summarize_cv_spearman,
)
from run_config import config_get, load_run_info

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


class InsufficientFeatureDataError(RuntimeError):
    """Raised when no structural descriptor has enough valid data to analyze."""


BASELINE_RESULT_COLUMNS = [
    "descriptor",
    "family",
    "deconfounded_spearman",
    *CV_SPEARMAN_SUMMARY_COLUMNS,
]


def _configured_max_descriptors(
    config_path: Path | None = None,
) -> int:
    """Read and validate the Stage-3 formula-size contract from run_info.yaml."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    value = int(config_get(config, "combination.max_descriptors"))
    if value not in (2, 3):
        raise ValueError("combination.max_descriptors must be 2 or 3")
    return value


def _resolve_config_input_path(value: str | Path, config_path: Path) -> Path:
    """Resolve a frozen input relative to the selected run-info file."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.resolve().parent / path).resolve()


def _frozen_pipeline_input_contract(config_path: Path) -> dict[str, Any]:
    """Validate and resolve the raw/registry inputs shared with the Agent track."""
    config = load_run_info(config_path)
    identity = resolve_frozen_input_identity(config, config_path)
    return {
        "raw_file": identity.raw_file,
        "featurized_file": _resolve_config_input_path(
            config_get(config, "data.featurized_file"), config_path
        ),
        "structure_column": str(config_get(config, "data.structure_column")),
        "target_column": str(config_get(config, "data.target_column")),
        "system_column": str(config_get(config, "data.system_column")),
        "anion_column": str(config_get(config, "data.anion_type_column")),
        "descriptor_registry": identity.descriptor_registry,
        "registry_revision": identity.registry_revision,
        "frozen_identity": identity,
    }


def _configured_pipeline_output_dir(
    config_path: Path | None = None,
) -> str:
    """Read the isolated Pipeline output directory from the shared run contract."""
    path = config_path or Path(__file__).with_name("run_info.yaml")
    config = load_run_info(path)
    return _validate_pipeline_output_dir(config_get(config, "tracks.pipeline.output_dir"))


def _validate_pipeline_output_dir(value: str | Path) -> str:
    """Reject an output path that could overwrite Agent-track artifacts."""
    output_dir = Path(value)
    expected_prefix = ("results", "pipeline")
    if (
        output_dir.is_absolute()
        or output_dir.parts[: len(expected_prefix)] != expected_prefix
        or ".." in output_dir.parts
    ):
        raise ValueError(
            "tracks.pipeline.output_dir must be a relative results/pipeline/ path"
        )
    return str(output_dir)


def _format_cv_metric(row: pd.Series, prefix: str) -> str:
    """Format a CV metric while keeping skipped strategies visibly distinct."""
    if bool(row.get(f"{prefix}_skipped", False)):
        return "SKIPPED"
    value = float(row.get(f"{prefix}_spearman", float("nan")))
    return f"{value:.3f}"


# ============================================================
# 命令行参数
# ============================================================

def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    config_probe = argparse.ArgumentParser(add_help=False)
    config_probe.add_argument(
        "--run-info",
        type=Path,
        default=Path(__file__).with_name("run_info.yaml"),
    )
    probe_args, _unknown = config_probe.parse_known_args(argv)
    try:
        frozen_input = _frozen_pipeline_input_contract(probe_args.run_info)
        configured_output_dir = _configured_pipeline_output_dir(probe_args.run_info)
        configured_max_descriptors = _configured_max_descriptors(probe_args.run_info)
    except (KeyError, ValueError) as exc:
        config_probe.error(str(exc))

    parser = argparse.ArgumentParser(
        description="Na离子导体描述符搜索 4阶段管线",
    )
    parser.add_argument(
        "--run-info",
        type=Path,
        default=probe_args.run_info,
        help="冻结共享输入与 Pipeline 输出目录的 YAML 配置。",
    )
    parser.add_argument(
        "--skip-featurize",
        action="store_true",
        help="跳过Stage 0（已有特征化数据时使用）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Stage 4中验证前k个组合候选（默认10）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=configured_output_dir,
        help="Pipeline 输出目录（默认 results/pipeline/；不读取 Agent 输出）",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge正则化强度（默认1.0）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（默认42）",
    )
    parser.add_argument(
        "--selection-alpha",
        type=float,
        default=0.05,
        help="Lasso稳定性选择正则化强度（默认0.05）",
    )
    parser.add_argument(
        "--max-descriptors",
        type=int,
        choices=(2, 3),
        default=configured_max_descriptors,
        help="Stage 3公式最大描述符数（默认读取run_info.yaml）",
    )
    args = parser.parse_args(argv)
    try:
        args.output_dir = _validate_pipeline_output_dir(args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    for key, value in frozen_input.items():
        setattr(args, key, value)
    return args


# ============================================================
# Stage 0: 特征化
# ============================================================

def runStage0(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str], np.ndarray]:
    """Stage 0: 从原始数据计算结构描述符，构建保留原值的特征矩阵。

    返回:
        (feature_df, raw_df, system_labels, anion_labels, y)
        - feature_df: 原始描述符矩阵（含固定噪声列、缺失值和元数据列）
        - raw_df: 原始特征化数据（含描述符原始值）
        - system_labels: 体系标签列表
        - anion_labels: 阴离子类型标签列表
        - y: log_sigma 目标向量
    """
    featurized_path = Path(args.featurized_file)

    if args.skip_featurize and featurized_path.exists():
        print("[Stage 0] 跳过特征化，加载已有数据...")
        raw_df = pd.read_csv(featurized_path, encoding="utf-8")
    else:
        raw_csv = Path(args.raw_file)
        if not raw_csv.exists():
            print(f"错误: 找不到输入文件 {raw_csv}")
            sys.exit(1)

        print("[Stage 0] 正在计算结构描述符...")
        print("  预计耗时 3-5 分钟（84 个 CIF × 41 个描述符）")
        raw_df = featurize_dataset(
            str(raw_csv),
            str(featurized_path),
            cif_column=args.structure_column,
        )

    # 构建保留原始值的特征矩阵；预测预处理在每个训练折内完成。
    print("[Stage 0] 构建原始特征矩阵...")
    feature_df, valid_cols, noise_info_df = build_feature_matrix(
        raw_df, target_col=args.target_column
    )

    # 提取标签和目标
    system_labels = raw_df[args.system_column].tolist()
    anion_labels = raw_df[args.anion_column].tolist()
    y = raw_df[args.target_column].values.astype(float)

    n_real = len(valid_cols)
    n_noise = len([c for c in feature_df.columns if c.startswith("noise_")])
    if n_real == 0:
        raise InsufficientFeatureDataError(
            "No valid structural descriptor values are available after coverage "
            "filtering; regenerate the featurized dataset from valid CIF inputs."
        )
    print(f"[Stage 0] 完成: {len(raw_df)} 样本, {n_real} 有效描述符, {n_noise} 噪声列")

    return feature_df, raw_df, system_labels, anion_labels, y


# ============================================================
# Stage 1: 单描述符去混杂筛选
# ============================================================

def runStage1(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    alpha: float,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 1: 对所有描述符执行去混杂分析，筛选有效信号。

    返回:
        (完整审计结果, 预筛选结果)。预筛选结果仅保留标签为
        强物理/弱物理/混合的描述符。
    """
    print("\n" + "=" * 60)
    print("[Stage 1] 单描述符去混杂筛选")
    print("=" * 60)

    analyzer = DeconfoundAnalyzer(alpha=alpha)
    deconfound_df = analyzer.analyze_all(feature_df, y, system_labels, anion_labels)

    # 保存完整结果
    deconfound_df.to_csv(output_dir / "stage1_deconfound_results.csv", index=False, encoding="utf-8")

    # 标签分布统计
    label_counts = deconfound_df["label"].value_counts()
    print("\n标签分布:")
    for label_name in ["强物理信号", "弱物理信号", "混合信号", "体系代理", "噪声级"]:
        count = label_counts.get(label_name, 0)
        print(f"  {label_name}: {count}")

    # 预筛选: 保留标签为强物理信号/弱物理信号/混合信号的描述符 (errata P5)
    pass_labels = {"强物理信号", "弱物理信号", "混合信号"}
    filtered_df = deconfound_df[deconfound_df["label"].isin(pass_labels)].copy()
    filtered_df.to_csv(
        output_dir / "stage1_prefiltered_results.csv",
        index=False,
        encoding="utf-8",
    )
    n_pass = len(filtered_df)
    n_total = len(deconfound_df)
    print(f"\nStage 1: {n_pass} 描述符通过预筛选（共 {n_total} 个）")

    return deconfound_df, filtered_df


# ============================================================
# Stage 2: 稳定性选择 + 物理族代表
# ============================================================

def runStage2(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    deconfound_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int = 2,
) -> pd.DataFrame:
    """Stage 2: stability selection and the bounded Stage-3 candidate pool.

    Pair-only search keeps one stable representative per family.  A permitted
    three-descriptor search retains up to two stable representatives per
    family: the second slot is a narrowly scoped formula-candidate slot needed
    for the plan-approved ``two from one family + adjacent family`` triples,
    rather than a second independent scientific finding.

    Returns:
        Candidate-representative DataFrame with ``is_representative``.
    """
    if max_descriptors not in (2, 3):
        raise ValueError("max_descriptors must be 2 or 3")
    print("\n" + "=" * 60)
    print("[Stage 2] 稳定性选择与物理族代表")
    print("=" * 60)

    # Stage 2 只允许 Stage 1 预筛选后的真实描述符；固定噪声列全部保留。
    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    prefiltered = set(deconfound_df["descriptor"].tolist())
    real_col_names = [
        c for c in feature_df.columns
        if c in registered and c in prefiltered
    ]
    noise_col_names = [c for c in feature_df.columns if c.startswith("noise_")]

    X_real = feature_df[real_col_names].values.astype(float)
    X_noise = feature_df[noise_col_names].values.astype(float) if noise_col_names else None

    # 稳定性选择
    print("  运行稳定性选择（100次自举）...")
    selector = StabilitySelector(
        n_bootstrap=100,
        threshold=0.6,
        fraction=0.5,
        alpha=alpha,
        seed=seed,
    )
    stability_df = selector.run(X_real, y, X_noise, real_col_names, noise_col_names)

    # 保存稳定性结果
    stability_df.to_csv(output_dir / "stage2_stability_results.csv", index=False, encoding="utf-8")

    n_stable = stability_df["is_stable"].sum()
    n_above_noise = stability_df["above_noise_baseline"].sum()
    print(f"  稳定描述符: {n_stable}, 超过噪声基线: {n_above_noise}")

    # 物理族代表选择
    print("  按物理族选择代表...")
    # A triple cannot be constructed from a one-per-family pool.  Keep the
    # legacy primary-representative capacity for pair-only search, and open
    # exactly one additional stable slot per family only when triples are
    # explicitly enabled by the frozen Pipeline contract.
    max_per_family = 2 if max_descriptors == 3 else 1
    grouper = PhysicalGrouper(max_per_family=max_per_family)
    representative_df = grouper.group_and_select(stability_df, deconfound_df)
    representative_df.attrs["max_descriptors"] = max_descriptors
    representative_df.attrs["max_representatives_per_family"] = max_per_family

    # 保存代表结果
    representative_df.to_csv(output_dir / "stage2_representatives.csv", index=False, encoding="utf-8")

    # 统计
    n_reps = representative_df["is_representative"].sum()
    print(
        f"\nStage 2: {n_reps} 个组合候选代表"
        f"（来自 {n_stable} 个稳定描述符；每族最多 {max_per_family} 个）"
    )

    # 打印每个代表
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        print(f"  [{row['family']}] {row['descriptor']} ({row['family_name']})"
              f"  去混杂ρ={rho:.3f}  频率={freq:.2f}")

    return representative_df


# ============================================================
# Stage 3: 约束组合搜索
# ============================================================

def runStage3(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    representative_df: pd.DataFrame,
    alpha: float,
    seed: int,
    output_dir: Path,
    max_descriptors: int | None = None,
) -> pd.DataFrame:
    """Stage 3: Search explicit raw-value pair and bounded-triple formulas.

    返回:
        组合候选 DataFrame
    """
    print("\n" + "=" * 60)
    print("[Stage 3] 约束组合搜索")
    print("=" * 60)

    searcher = ConstrainedCombinationSearch(alpha=alpha, seed=seed)
    effective_max_descriptors = (
        _configured_max_descriptors()
        if max_descriptors is None else int(max_descriptors)
    )
    candidates_df = searcher.search(
        feature_df, y, system_labels, anion_labels,
        representative_df,
        max_candidates=150,
        max_descriptors=effective_max_descriptors,
    )

    # 保存结果
    combination_candidates_to_csv_frame(candidates_df).to_csv(
        output_dir / "stage3_combination_candidates.csv",
        index=False,
        encoding="utf-8",
    )

    n_candidates = len(candidates_df)
    print(f"\nStage 3: {n_candidates} 个有效二/三描述符组合候选")

    # 打印 top 5
    if not candidates_df.empty:
        top5 = candidates_df.head(5)
        print("\nTop 5 组合候选（按 |去混杂Spearman| 降序）:")
        for _, row in top5.iterrows():
            cross_flag = "跨族" if row["is_cross_family"] else "同族"
            print(f"  {row['combined_name']}  "
                  f"去混杂ρ={row['combined_deconf_spearman']:.3f}  [{cross_flag}]")

    return candidates_df


# ============================================================
# Stage 4: 多策略CV验证
# ============================================================

def runStage4(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    system_labels: list[str],
    anion_labels: list[str],
    deconfound_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    alpha: float,
    seed: int,
    top_k: int,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 4: exploratory V1--V4 evidence, CV, and single baseline.

    返回:
        (validation_df, baseline_df)
        - validation_df: 组合描述符验证结果
        - baseline_df: 最佳单描述符基线结果
    """
    print("\n" + "=" * 60)
    print("[Stage 4] 多策略CV验证")
    print("=" * 60)

    # --- 组合验证 ---
    print(f"  验证 Top-{top_k} 组合候选（V1–V4，探索性证据）...")
    validator = CombinationValidator(alpha=alpha, seed=seed)
    validation_df = validator.validate(
        feature_df, y, system_labels, anion_labels,
        candidates_df, top_k=top_k,
    )

    # 保存验证结果
    combination_validation_to_csv_frame(validation_df).to_csv(
        output_dir / "stage4_validation_results.csv",
        index=False,
        encoding="utf-8",
    )

    n_validated = len(validation_df)
    print(f"  成功验证 {n_validated} 个组合")

    # --- 单描述符基线 ---
    baseline_df = pd.DataFrame(columns=BASELINE_RESULT_COLUMNS)
    # 选出去混杂Spearman绝对值最高的描述符作为基线
    if not deconfound_df.empty:
        best_single_row = deconfound_df.iloc[0]  # 已按 |deconfounded_spearman| 降序排列
        best_single_name = best_single_row["descriptor"]

        print(f"\n  最佳单描述符基线: {best_single_name}")
        print("  运行多策略CV...")

        # 获取该描述符的特征列
        if best_single_name in feature_df.columns:
            x_single = feature_df[best_single_name].values.astype(float)
            X_single = x_single.reshape(-1, 1)
            y_arr = np.asarray(y, dtype=float)

            # 有效样本掩码
            valid_mask = ~np.isnan(y_arr)
            if valid_mask.sum() >= 5:
                cv = MultiStrategyCV(alpha=alpha)
                cv_results = cv.run_all(
                    X_single[valid_mask],
                    y_arr[valid_mask],
                    np.asarray(system_labels)[valid_mask],
                    np.asarray(anion_labels)[valid_mask],
                )
                cv_summary = summarize_cv_spearman(cv_results)

                baseline_records = [{
                    "descriptor": best_single_name,
                    "family": best_single_row["family"],
                    "deconfounded_spearman": best_single_row["deconfounded_spearman"],
                    **cv_summary,
                }]
                baseline_df = pd.DataFrame.from_records(
                    baseline_records,
                    columns=BASELINE_RESULT_COLUMNS,
                )
            else:
                print("  警告: 有效样本不足，跳过单描述符基线CV")
        else:
            print(f"  警告: 描述符 {best_single_name} 不在特征矩阵中，跳过基线CV")
    else:
        best_single_name = "N/A"

    # 保存基线结果
    if not baseline_df.empty:
        baseline_df.to_csv(output_dir / "stage4_single_descriptor_baseline.csv", index=False, encoding="utf-8")
        print(f"  基线描述符: {best_single_name}")
        for _, row in baseline_df.iterrows():
            print(f"    阴离子分层: {_format_cv_metric(row, 'anion_stratified')}")
            print(f"    LOSO:       {_format_cv_metric(row, 'loso')}")
            print(f"    重复子采样: {_format_cv_metric(row, 'repeated_subsample')}")
            print(
                f"    综合得分:   {row['composite_score']:.3f} "
                f"({int(row['composite_strategy_count'])}/3 strategies)"
            )

    return validation_df, baseline_df


# ============================================================
# 报告生成
# ============================================================

def generateReport(
    raw_df: pd.DataFrame,
    deconfound_df: pd.DataFrame,
    filtered_deconfound_df: pd.DataFrame,
    representative_df: pd.DataFrame,
    candidates_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """生成最终 Markdown 报告和 JSON 报告。"""
    print("\n" + "=" * 60)
    print("生成最终报告")
    print("=" * 60)

    # ---- 收集报告数据 ----
    n_samples = len(raw_df)
    system_counts = raw_df["system"].value_counts().to_dict()
    n_nasicon = system_counts.get("NASICON", 0)
    n_sulfide = system_counts.get("sulfide", 0)
    n_halide = system_counts.get("halide", 0)

    y_values = raw_df["log_sigma"].dropna().values
    y_min = float(y_values.min()) if len(y_values) > 0 else 0.0
    y_max = float(y_values.max()) if len(y_values) > 0 else 0.0

    registered = set(SEARCHABLE_STRUCTURE_DESCRIPTORS.keys())
    n_total_desc = len(registered)
    n_valid_desc = len(filtered_deconfound_df)

    # ---- Stage 1 表格 ----
    top10_deconf = deconfound_df.head(10)
    stage1_table_rows = []
    for _, row in top10_deconf.iterrows():
        stage1_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | "
            f"{row['raw_spearman']:.3f} | {row['deconfounded_spearman']:.3f} | "
            f"{row['system_proxy_ratio']:.3f} | {row['label']} |"
        )
    stage1_table = "\n".join(stage1_table_rows)

    # 标签分布
    label_counts = deconfound_df["label"].value_counts().to_dict()

    # ---- Stage 2 代表表格 ----
    reps = representative_df[representative_df["is_representative"] == True]  # noqa: E712
    stage2_table_rows = []
    for _, row in reps.iterrows():
        rho = row.get("deconfounded_spearman", float("nan"))
        freq = row.get("selection_freq", 0.0)
        stage2_table_rows.append(
            f"| {row['descriptor']} | {row['family']} | {row['family_name']} | "
            f"{rho:.3f} | {freq:.2f} |"
        )
    stage2_table = "\n".join(stage2_table_rows)
    stage2_capacity = int(
        representative_df.attrs.get("max_representatives_per_family", 1)
    )

    # ---- Stage 3 Top10 组合表格 ----
    top10_comb = candidates_df.head(10)
    stage3_table_rows = []
    for _, row in top10_comb.iterrows():
        cross_flag = "是" if row["is_cross_family"] else "否"
        components = row.get("components", [row["d1"], row["d2"]])
        operators = row.get("operators", [row["operator"]])
        stage3_table_rows.append(
            f"| {row['combined_name']} | {len(components)} | "
            f"{', '.join(map(str, components))} | {', '.join(map(str, operators))} | "
            f"{row['combined_deconf_spearman']:.3f} | {cross_flag} |"
        )
    stage3_table = "\n".join(stage3_table_rows)

    # ---- Stage 4 表格 ----
    # 基线行
    if not baseline_df.empty:
        bl = baseline_df.iloc[0]
        baseline_row = (
            f"| {bl['descriptor']} | {_format_cv_metric(bl, 'anion_stratified')} | "
            f"{_format_cv_metric(bl, 'loso')} | "
            f"{_format_cv_metric(bl, 'repeated_subsample')} |"
        )
        best_single_name = bl["descriptor"]
        best_single_family = bl.get("family", "Unknown")
        best_single_rho = bl.get("deconfounded_spearman", 0.0)
    else:
        baseline_row = "| N/A | N/A | N/A | N/A |"
        best_single_name = "N/A"
        best_single_family = "N/A"
        best_single_rho = 0.0

    # 组合验证表格
    stage4_table_rows = []
    for _, row in validation_df.iterrows():
        blocks = row.get("evidence_blocks", {})
        availability = "/".join(
            "OK" if bool(blocks.get(name, {}).get("available", False)) else "N/A"
            for name in ("noise_baseline", "factor_spanning", "per_system", "bootstrap_ci")
        )
        bootstrap = row.get("bootstrap_ci", {})
        if bool(bootstrap.get("available", False)):
            uncertainty = (
                f"[{bootstrap['ci_lower']:.3f}, {bootstrap['ci_upper']:.3f}]"
            )
        else:
            uncertainty = "UNAVAILABLE"
        stage4_table_rows.append(
            f"| {row['combined_name']} | {int(row.get('n_components', 2))} | "
            f"{row['combined_deconf_spearman']:.3f} | "
            f"{_format_cv_metric(row, 'anion_stratified')} | "
            f"{_format_cv_metric(row, 'loso')} | "
            f"{_format_cv_metric(row, 'repeated_subsample')} | "
            f"{row['composite_score']:.3f} "
            f"({int(row['composite_strategy_count'])}/3) | {availability} | "
            f"{uncertainty} | 探索性 |"
        )
    stage4_table = "\n".join(stage4_table_rows)

    if not validation_df.empty:
        best_v2 = validation_df.iloc[0].get("factor_spanning", {})
        best_v2_rho = best_v2.get(
            "oof_residual_target_vs_formula_prediction_spearman", float("nan")
        )
        best_v2_summary = (
            f"OOF残差预测Spearman={best_v2_rho:.3f}, "
            f"可用折={best_v2.get('n_folds_available', 0)}/"
            f"{best_v2.get('n_folds_requested', 0)}, "
            f"OOF样本={best_v2.get('n_oof_samples', 0)}"
        )
        best_v2_control_audit = (
            f"primary={best_v2.get('primary_control', 'unavailable')}, "
            f"system_rank={best_v2.get('system_design_rank', 'N/A')}, "
            f"combined_rank={best_v2.get('confounder_rank', 'N/A')}, "
            f"anion_incremental_rank={best_v2.get('anion_incremental_rank', 'N/A')}, "
            f"redundant_anion_columns="
            f"{best_v2.get('anion_redundant_columns', [])}"
        )
    else:
        best_v2_summary = "UNAVAILABLE"
        best_v2_control_audit = "UNAVAILABLE"

    # ---- 结论 ----
    # 最强组合
    if not validation_df.empty:
        best_comb_row = validation_df.iloc[0]
        best_comb_name = best_comb_row["combined_name"]
        best_comb_score = best_comb_row["composite_score"]
    else:
        best_comb_name = "N/A"
        best_comb_score = 0.0

    # 组合相比单描述符提升
    if not baseline_df.empty and not validation_df.empty:
        baseline_composite = baseline_df.iloc[0]["composite_score"]
        delta_pct = ((best_comb_score - baseline_composite) / abs(baseline_composite) * 100
                     if abs(baseline_composite) > 1e-8 else 0.0)
    else:
        delta_pct = 0.0

    # 跨CV策略一致性评估
    if not validation_df.empty:
        # 仅检查实际可用（未跳过且有限）的策略；跳过不计作证据。
        signs = []
        for _, row in validation_df.head(3).iterrows():
            for prefix in (
                "anion_stratified",
                "loso",
                "repeated_subsample",
            ):
                if bool(row.get(f"{prefix}_available", False)):
                    signs.append(np.sign(row[f"{prefix}_spearman"]))
        n_positive = sum(1 for s in signs if s > 0)
        n_negative = sum(1 for s in signs if s < 0)
        if not signs:
            consistency_desc = "无可用CV策略"
        elif n_positive == 0 and n_negative == 0:
            consistency_desc = "所有CV策略均无显著相关"
        elif n_positive == len(signs) or n_negative == len(signs):
            consistency_desc = "全部同向，一致性优秀"
        elif n_positive > n_negative * 2 or n_negative > n_positive * 2:
            consistency_desc = "多数同向，一致性良好"
        else:
            consistency_desc = "方向不一致，需谨慎解读"
    else:
        consistency_desc = "无验证结果"

    # 去混杂后信号保留率
    if not deconfound_df.empty:
        raw_rho_sq = deconfound_df["raw_spearman"].pow(2).mean()
        deconf_rho_sq = deconfound_df["deconfounded_spearman"].pow(2).mean()
        signal_retention = (deconf_rho_sq / raw_rho_sq * 100) if raw_rho_sq > 1e-12 else 0.0
    else:
        signal_retention = 0.0

    # ---- 组装 Markdown 报告 ----
    report = f"""# Na离子导体描述符搜索报告

## 数据概览
- 样本数: {n_samples}
- 体系分布: NASICON={n_nasicon}, sulfide={n_sulfide}, halide={n_halide}
- 目标范围: log_sigma ∈ [{y_min:.2f}, {y_max:.2f}]
- 描述符总数: {n_total_desc}, 有效描述符: {n_valid_desc}

## Stage 1: 单描述符去混杂筛选
| 描述符 | 族 | 原始Spearman | 去混杂Spearman | 体系代理比 | 标签 |
|--------|-----|-------------|---------------|-----------|------|
{stage1_table}

### 标签分布
- 强物理信号: {label_counts.get('强物理信号', 0)}
- 弱物理信号: {label_counts.get('弱物理信号', 0)}
- 混合信号: {label_counts.get('混合信号', 0)}
- 体系代理: {label_counts.get('体系代理', 0)}
- 噪声级: {label_counts.get('噪声级', 0)}

## Stage 2: 稳定性选择与族代表
候选池规则：每个物理族最多保留 {stage2_capacity} 个稳定代表。三描述符模式下，
第二个同族名额仅用于受限的"同族两个 + 相邻族一个"公式构造，不应被解读为第二项独立科学发现。

### 族代表列表
| 描述符 | 族 | 族名 | 去混杂Spearman | 稳定性频率 |
|--------|-----|------|---------------|-----------|
{stage2_table}

## Stage 3: 约束组合搜索
### Top 10 组合候选
| 组合名 | 描述符数 | 组成 | 运算符序列 | 去混杂Spearman | 跨族? |
|--------|----------|------|------------|---------------|-------|
{stage3_table}

## Stage 4: V1–V4探索性验证与多策略CV
### 最佳单描述符基线
| 描述符 | 阴离子分层 | LOSO | 重复子采样 |
|--------|-----------|------|-----------|
{baseline_row}

### Top组合验证结果
| 组合名 | 描述符数 | 去混杂Spearman | 阴离子分层 | LOSO | 重复子采样 | 综合得分 | V1/V2/V3/V4 | 体系分层Bootstrap 95% CI | 状态 |
|--------|----------|---------------|-----------|------|-----------|---------|-------------|---------------------------|------|
{stage4_table}

注：V1–V4依次为匹配噪声基线、已知因素后关联、体系内原始Spearman、体系分层Bootstrap区间。`SKIPPED` 策略不计入综合得分；括号显示可用策略数/3。所有组合证据均为探索性，不作因果解释；完整公式组成、运算符、规则和原始值来源保存在 CSV/JSON provenance 中。

### V2 已知因素后目标残差预测审计（最佳组合）
- {best_v2_summary}
- 控制设计: {best_v2_control_audit}
- 语义: 折安全的探索性预测关联；不是因果效应。双侧偏相关仅作为补充证据保存在 artifact 中。

## 结论
### 物理发现
- 最强单描述符: {best_single_name} ({best_single_family}族), 去混杂Spearman = {best_single_rho:.3f}
- 最强组合: {best_comb_name}, 综合得分 = {best_comb_score:.3f}
- 组合相比单描述符提升: {delta_pct:.1f}%

### 稳健性评估
- 跨CV策略一致性: {consistency_desc}
- 去混杂后信号保留率: {signal_retention:.1f}%
"""

    report_path = output_dir / "final_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"  Markdown 报告: {report_path}")

    # ---- 组装 JSON 报告 ----
    report_json = {
        "data_overview": {
            "n_samples": n_samples,
            "system_distribution": {"NASICON": n_nasicon, "sulfide": n_sulfide, "halide": n_halide},
            "log_sigma_range": [y_min, y_max],
            "n_total_descriptors": n_total_desc,
            "n_valid_descriptors": n_valid_desc,
        },
        "stage1_deconfound": {
            "label_distribution": label_counts,
            "top10": deconfound_df.head(10).to_dict(orient="records"),
        },
        "stage2_stability": {
            "representatives": reps.to_dict(orient="records") if not reps.empty else [],
        },
        "stage3_combination": {
            "n_candidates": len(candidates_df),
            "top10": candidates_df.head(10).to_dict(orient="records") if not candidates_df.empty else [],
        },
        "stage4_validation": {
            "baseline": baseline_df.to_dict(orient="records") if not baseline_df.empty else [],
            "top_combinations": validation_df.to_dict(orient="records") if not validation_df.empty else [],
        },
        "conclusion": {
            "best_single_descriptor": best_single_name,
            "best_single_family": best_single_family,
            "best_single_rho": float(best_single_rho),
            "best_combination": best_comb_name,
            "best_combination_score": float(best_comb_score),
            "combination_improvement_pct": float(delta_pct),
            "cv_consistency": consistency_desc,
            "signal_retention_pct": float(signal_retention),
        },
    }

    json_path = output_dir / "final_report.json"
    json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  JSON 报告: {json_path}")


# ============================================================
# 主入口
# ============================================================

def main() -> None:
    """管线主入口。"""
    t_start = time.time()

    args = parseArgs()
    output_dir = Path(args.output_dir)

    print("=" * 60)
    print("Na离子导体描述符搜索管线")
    print(
        f"  ridge_alpha={args.alpha}, selection_alpha={args.selection_alpha}, "
        f"seed={args.seed}, top_k={args.top_k}, "
        f"max_descriptors={args.max_descriptors}"
    )
    print(f"  输出目录: {output_dir.resolve()}")
    print("=" * 60)

    # Stage 0: 特征化
    feature_df, raw_df, system_labels, anion_labels, y = runStage0(args)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: 单描述符去混杂筛选
    deconfound_df, filtered_deconfound_df = runStage1(
        feature_df, y, system_labels, anion_labels, args.alpha, output_dir
    )

    # Stage 2: 稳定性选择 + 物理族代表
    representative_df = runStage2(
        feature_df,
        y,
        filtered_deconfound_df,
        args.selection_alpha,
        args.seed,
        output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 3: 约束组合搜索
    candidates_df = runStage3(
        feature_df, y, system_labels, anion_labels,
        representative_df, args.alpha, args.seed, output_dir,
        max_descriptors=args.max_descriptors,
    )

    # Stage 4: 多策略CV验证
    validation_df, baseline_df = runStage4(
        feature_df, y, system_labels, anion_labels,
        filtered_deconfound_df,
        candidates_df,
        args.alpha,
        args.seed,
        args.top_k,
        output_dir,
    )

    # 生成报告
    generateReport(
        raw_df, deconfound_df, filtered_deconfound_df,
        representative_df, candidates_df, validation_df, baseline_df,
        output_dir,
    )

    # 结束
    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"管线完成! 总耗时: {elapsed:.1f} 秒")
    print(f"所有结果保存在: {output_dir.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except (InsufficientFeatureDataError, FileNotFoundError) as exc:
        # A missing raw/CIF input is a controlled data-integrity failure, not a
        # Python crash.  Keep the diagnosis concise and preserve the guarantee
        # that Stage 0 failed before ``results/pipeline`` was created.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
--- 文件结束: run_pipeline.py ---

--- 文件开始: run_info.yaml ---
# Na离子导体描述符搜索配置
# 基于 automat 框架，针对 Na 离子固态电解质结构描述符与电导率关系研究

task:
  name: naconductor
  description: >
    搜索 Na 离子固态导体的局域结构描述符组合，
    使其与 log10(σ/S·cm⁻¹) 的去混杂 Spearman 相关性最大化。
    描述符从 CIF 结构文件计算，禁止使用 log/√/幂运算构造新特征。
    目标是找到物理可解释、统计稳健的描述符组合，
    而非单纯追求预测精度。

data:
  raw_file: data/naconductor_raw.csv
  featurized_file: data/naconductor_featurized.csv
  target_column: log_sigma
  structure_column: cif_path
  material_id_column: material_id
  formula_column: formula
  system_column: system
  anion_type_column: anion_type
  # 不做 train/val/test 预拆分——用 CV 策略替代
  # 原始数据 84 行，全量参与交叉验证

cv_strategies:
  # 策略 1：阴离子分层 K 折；类别不足两例时显式跳过，支持不足时显式降折
  - name: anion_stratified_cv
    folds: 3
    stratify_by: anion_type
    random_seed: 42
    insufficient_class_policy: skip
    requested_fold_downshift: explicit
  # 策略 2：留一体系交叉验证（LOSO-CV）
  # 每次留出一个体系（NASICON/sulfide/halide）作为验证集
  - name: leave_one_system_out
    group_column: system
  # 策略 3：重复随机子采样
  - name: repeated_subsample
    n_repeats: 10
    test_fraction: 0.2
    stratify_by: system
    random_seed: 42

deconfound:
  # 混杂变量列表——这些变量与目标相关但不是因果通路
  # 在计算描述符-目标相关性时需要控制
  confounders:
    - system          # 主控制：体系类型（NASICON/sulfide/halide）
    - anion_type      # 增量控制；报告相对 system 的秩增量/冗余，不作独立因果解释
  categorical_coding: reference_class
  primary_control: system
  report_design_rank: true
  # 去混杂方法：偏相关 / DML（Double Machine Learning）
  method: partial_correlation  # 可选: partial_correlation, dml
  # 去混杂后的 Spearman rho 作为主要评价指标
  primary_metric: deconfounded_spearman

stability_selection:
  # 子采样 Lasso；填充和缩放在每个子样本 Pipeline 内独立拟合
  method: subsampled_lasso
  selection_alpha: 0.05
  preprocessing:
    - median_imputation
    - standard_scaling
  n_bootstrap: 100
  threshold: 0.6          # 被选中的频率阈值
  fraction: 0.5           # 每次自举采样比例
  random_seed: 42

combination:
  # 原始物理值上的受约束枚举；只在完整公式进入模型后做折内标准化
  method: constrained_enumeration
  raw_value_source: feature_df
  max_descriptors: 3
  min_descriptors: 2
  pair_rules:
    source_of_truth: descriptors.combination.PAIR_OPERATOR_RULES
    execution: enforced_by_declarative_registry
    commutative_operators: [add, multiply]
    canonical_unordered_pairs: true
    directional_ratios: explicit_registry_entries_only
    reject_zero_or_nonfinite_denominator: true
    default_ratio_allowed: false
  triple_rules:
    adjacency_source_of_truth: descriptors.combination.PAIR_OPERATOR_RULES
    same_family_source_of_truth: descriptors.combination.SAME_FAMILY_OPERATOR_RULES
    execution: enforced_by_declarative_registry
    enabled: true
    shape: two_from_one_family_plus_one_from_explicit_adjacent_family
    arbitrary_triples: false
  # 禁止的运算符——描述符构造中不允许使用
  forbidden_operators:
    - log          # 禁止对原始描述符取对数（因为目标已是 log）
    - sqrt         # 禁止开方（物理意义不明确）
    - power        # 禁止幂运算（过拟合风险高）
  # 下列语义目前是人工解释审查要求，不是程序化筛选条件。
  manual_physical_interpretation_review:
    enforced_by_search: false
    review_questions:
      - monotonic_with_ion_size
      - positive_correlation_with_vacancy

combination_validation:
  status: exploratory
  causal_claim: false
  evidence_blocks:
    - noise_baseline
    - factor_spanning
    - per_system
    - bootstrap_ci
  bootstrap:
    method: system_stratified
    random_seed: 42
  factor_spanning:
    primary_method: fold_safe_oof_target_residual_prediction
    control_design: rank_aware_system_primary_plus_incremental_anion
    formula_preprocessing: fold_local_median_imputation_and_scaling
    partial_association_role: supplementary_only
  selection_uncertainty:
    nested_outer_group_selection_available: false

evaluation:
  # 主要评价指标
  primary: deconfounded_spearman
  # 辅助评价指标
  secondary:
    - cv_spearman       # 交叉验证 Spearman rho
    - cv_mae            # 交叉验证 MAE
    - cv_rmse           # 交叉验证 RMSE
    - stability_score   # 稳定性选择得分
  # 模型
  model:
    # Ridge 回归：84 样本用 RF 容易过拟合，Ridge 正则化更稳健
    name: ridge
    alpha: 1.0          # L2 正则化强度
    random_seed: 42
    fold_preprocessing:
      - median_imputation
      - standard_scaling
  # 相关性方法
  correlation_method: spearman   # 使用 Spearman 秩相关（非参数，适合小样本）

# 两条轨道只共享这一冻结输入契约；任何运行结果均不共享。
shared_input:
  frozen: true
  raw_file: data/naconductor_raw.csv
  descriptor_registry: descriptors/__init__.py
  registry_revision: structural-registry-v1-2026-08-03
  semantics: >
    Agent 与 pipeline 可以同时启动，并只读取本节指定的原始 CSV 与注册表。
    在 C9 前禁止任一轨道读取、修改或据另一轨道的结果作筛选决定。

tracks:
  pipeline:
    output_dir: results/pipeline
    reads: [shared_input]
    must_not_read: [results/agent]
    status: exploratory

  agent:
    results_file: results/agent/results.tsv
    ideas_file: results/agent/ideas.tsv
    feature_cache_file: results/agent/descriptor_features.csv
    figure_file: results/agent/figures/metric_history.png
    reads: [shared_input]
    must_not_read: [results/pipeline]
    status:
      primary_metric: deconfounded_spearman
      max_iterations: 30
      patience: 8
      semantics: >
        仅对 status 为 evaluated、keep 或 discard 的有限去混杂 Spearman
        计入耐心；crash 和不可用 CV 策略不会伪造改善或消耗耐心。

c9_cross_track_review:
  user_authorization_required: true
  inputs_must_be_completed_and_frozen: true
  read_only_inputs: [results/agent, results/pipeline]
  interpretation: >
    结果一致仅是独立三角验证或优先复核线索，不构成因果证据；
    两条轨道均不建立因果关系。
--- 文件结束: run_info.yaml ---

## 输出格式

For each check, report:
- Status: PASS | WARN | FAIL | NOT_APPLICABLE
- Evidence: exact file:line references
- Details: what specifically was found

请按以下结构输出（每项检查用 ### 开头，字母与标题之间用句点分隔）：

### A. [检查项标题]: [PASS | WARN | FAIL | NOT_APPLICABLE]
- Evidence: [file:line references]
- Details: [findings]

### B. [检查项标题]: [PASS | WARN | FAIL | NOT_APPLICABLE]
...

最后必须单独输出一行总判定，格式严格如下：

## Overall Verdict: [PASS | WARN | FAIL]

## Action Items
- [specific fixes if WARN or FAIL]

## Claim Impact
- Claim 1: [supported | needs_qualifier | unsupported]

[执行器提示]
以下为任务边界说明（不是审稿判断，仅供定义本次审计对象）：

1. 本次审计对象是上述 5 个文件的代码与配置逻辑，不是数值结果。
2. 被排除的路径及原因：
   - results/：结果目录，本次审计未嵌入其中任何文件。因此检查项 C（Result File Existence）中凡涉及结果文件存在性的核验将无法进行，请报 NOT_APPLICABLE 并说明缺什么。
   - data/naconductor_featurized.csv：特征化后的数据文件，同样未嵌入。目标变量 log_sigma 的原始数值无法从本 prompt 中直接核验。
3. 数据集状态：原始数据为 data/naconductor_raw.csv（84 行），其 cif_path 列指向 CIF 结构文件。本次审计聚焦于管线代码的逻辑与配置，不涉及对原始数据数值的核验。
4. 项目中尚存在未嵌入的模块：descriptors/featurizer.py、descriptors/combination.py、descriptors/cv_strategies.py、automat_utils.py、run_config.py 等。这些模块被 run_pipeline.py 引用但其源码未在本 prompt 中提供。若某检查项需要这些模块的内容才能判定，请报 NOT_APPLICABLE 并说明缺什么。
5. checklist profile：stat-pipeline（A–H 共 8 项检查）。

--- prompt 正文结束 ---
