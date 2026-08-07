"""写入第 2 轮回复的第 3 部分（问题 2：修复后管线架构）。"""
import pathlib

p = pathlib.Path(
    r"E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main"
    r"\experiments\02_组合描述符搜索\automat-naconductor"
    r"\.omo\manual-review-bridge\round2_response_full.md"
)

text = """

---

# 问题 2：修复后管线架构

## 2.1 主数据流

```mermaid
flowchart TD
    classDef keep fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef mod fill:#fff8e1,stroke:#f9a825,color:#6d4c00
    classDef new fill:#e3f2fd,stroke:#1565c0,color:#0d47a1

    CIF["CIF 结构文件（冻结输入）"]
    RAW["naconductor_raw.csv（system / anion_type / log_sigma）"]
    S0["Stage 0 特征化（出：feature_df + 每列 observed_fraction）"]
    SH["影子列生成（每个真实描述符的列内置换副本）【新增】"]
    QB["控制基构造（在实际分析行子集上做 QR 或 SVD）【修改】"]
    OP["核心算子 partial_rank_assoc（x 与 y 双侧投影残差化 alpha=0）【新增】"]
    S1["Stage 1 固定基数筛选（真实列与影子列同路径竞争前 k 位）【修改】"]
    S2["Stage 2 稳定性选择（lambda 路径 + q 记录 + EV 上界 + 族内 medoid）【修改】"]
    S3["Stage 3 受约束枚举（注册表不变 + 增量有效性闸门）【修改】"]
    SETS["三个验证集合（top-k / random-k / bottom-k）【新增】"]
    S4["Stage 4 证据块（V1 V2 V3 V4 + LOSO 残差化目标）【修改】"]
    PERM["外层置换循环（详见图 2）【新增】"]
    REP["报告（每个 rho 列绑定估计量 + availability 一等列 + maxT 分位数）【修改】"]

    CIF --> S0
    RAW --> S0
    RAW --> QB
    S0 --> SH
    S0 --> QB
    S0 --> OP
    QB --> OP
    SH --> S1
    OP --> S1
    S1 --> S2
    S2 --> S3
    OP --> S3
    S3 --> SETS
    SETS --> S4
    OP --> S4
    S1 -.每轮重跑.-> PERM
    S2 -.每轮重跑.-> PERM
    S3 -.每轮重跑.-> PERM
    PERM --> REP
    S4 --> REP
```

**颜色标注**：绿色=保持不变，黄色=修改，蓝色=新增

**各阶段输入/输出契约**

| 阶段 | 输入 | 输出 | 状态 |
|---|---|---|---|
| Stage 0 特征化 | CIF + raw CSV | feature_df、每列 observed_fraction、注册表元数据 | 修改（新增 observed_fraction） |
| 影子列生成 | feature_df | 每个真实列的列内置换副本，继承缺失模式与边际分布 | **新增** |
| 控制基构造 | system/anion 标签 + 行索引集 | 正交基 Q、数值秩、声明容差 | 修改（从贪心秩筛选改为 QR/SVD） |
| 核心算子 | x、y、行索引集、Q | rho_partial_projection、resid_var_frac、deconfound_applied | **新增**（统一入口） |
| Stage 1 | feature_df + 影子列 + y | 前 k 位（真实与影子混合）+ 每列 n_valid | 修改（固定基数取代阈值） |
| Stage 2 | Stage 1 输出 | 稳定性频率（λ 路径最大值）、q、EV 上界、族代表（medoid） | 修改 |
| Stage 3 | 代表集 + feature_df | 候选表 + m_enum + 每候选 n_valid + provenance | 修改（新增增量有效性闸门） |
| 验证集合划分 | 候选表 | top-k / random-k / bottom-k 三组 | **新增** |
| Stage 4 | 三组候选 + y + 标签 | V1-V4 证据块 + LOSO 诊断 | 修改 |
| 外层置换 | 冻结配置 + B 个置换 | maxT 零分布 + 头条分位数 | **新增** |
| 报告 | 全部上游 | 绑定估计量的列 + availability + maxT | 修改 |

---

## 2.2 置换循环展开

```mermaid
flowchart TD
    OBS["观测臂跑一次：Stage 1 到 Stage 3 完整执行，记录 T_obs = 全枚举上的最大 abs rho_partial"]
    L0["外层置换 b = 1 到 B"]
    P1["体系内联合置换（同一个置换施加于全部描述符列，等价于体系内置换 y）"]
    P2["重跑 Stage 1 固定基数筛选（影子列同样参与竞争）"]
    P3["重跑 Stage 2 稳定性选择与族代表"]
    P4["重跑 Stage 3 枚举、排序、增量有效性闸门"]
    P5["记录 T_b = 该轮全枚举上的最大 abs rho_partial"]
    NUL["零分布 T_1 到 T_B"]
    PV["maxT 分位数（唯一含选择的头条统计量）"]
    NOT["每轮不重跑：V2 交叉拟合、V4 自举、LOSO 诊断（它们条件于被选中候选，不进入最大值统计量）"]

    OBS --> L0
    L0 --> P1 --> P2 --> P3 --> P4 --> P5
    P5 -->|下一轮| L0
    P5 --> NUL
    NUL --> PV
    OBS --> PV
    L0 -.不进入循环.- NOT
```

**关键设计点**

1. **循环包住 Stage 1-3，不包 Stage 4。** 头条统计量是"全枚举上的最大值"，只依赖筛选、稳定性、枚举、排序四步。V2/V4 是条件于已选中候选的量，放进循环既昂贵又无意义。
2. **置换的对象是"体系内的行索引"，且全部描述符列共用同一个置换。** 与"体系内置换 y"完全等价，保留描述符间联合依赖、缺失模式、组间结构，只切断与目标的链接。
3. **影子列也参与每一轮。** 否则置换轮的搜索空间与观测轮不同，两臂再次不可交换。
4. **配置在循环外冻结。** 所有阈值、基数 k、λ 网格、闸门在进入循环前固定。
5. **退化条件**：体系组规模越小，组内置换的有效随机性越低；单例组在每轮中保持真实配对，使零分布向观测值偏移（方向上保守）。

---

## 2.3 估计量绑定表

| 列名 | 估计量 | 计算方法 | 配套不确定性/对照 |
|---|---|---|---|
| `rho_raw_pooled` | 全部有效行上的池化原始秩关联 | Spearman | 无（仅作对照展示） |
| **`rho_partial_projection`** | **主指标**：双侧投影残差化后的秩关联 | 正交投影（alpha=0）+ Spearman | `perm_pct_candidate` + `ci_*_bca` |
| `resid_var_frac_x` / `_y` | 残差化后保留的方差占比 | 1 - R^2 of 控制模型 | — |
| `control_rank` / `deconfound_applied` | 实际使用的控制设计秩；是否真的执行了调整 | QR 数值秩 | — |
| `rho_within_system_<sys>` | 单个体系内的原始秩关联（分层调整，无函数形式假设） | 组内 Spearman | 小 n 用精确置换 p |
| `rho_within_pooled_z` | Fisher-z 逆方差加权合并的体系内关联 | Fisher-z 固定效应合并 | `het_Q`、`het_I2` |
| `rho_oof_dml_partial` | 交叉拟合双侧残差化后的折外偏关联 | DML 正交得分 + 逐折 Fisher-z 聚合 | `n_folds_available`、`n_oof` |
| `rho_loso_residualized` | 留一体系、折内残差化目标上的秩关联 | 逐折计算 + Fisher-z | 折间离散度 |
| `perm_pct_candidate` | 逐候选：rho_partial_projection 在置换零分布中的分位数 | V1，共享置换，B 抽样 | `n_success` |
| **`perm_pct_maxT`** | **含选择**：观测头条在"全枚举最大值"零分布中的分位数 | 外层 maxT | `B`、`m_enum` |
| `ci_lo_rho_partial_bca` / `ci_hi_*` | rho_partial_projection 的体系分层自举 BCa 区间 | 分层自举 + BCa | **明示不含选择不确定性，须与 perm_pct_maxT 并读** |
| `stability_freq_pathmax` | λ 路径上的最大选中频率 | MB stability selection | `q_mean`、`ev_bound` |
| `ev_bound` | 期望假阳性数上界 | MB / Shah-Samworth | — |
| `shadow_survival_rate` | 影子列通过 Stage 1 固定基数筛选的比例 | 与真实列同路径竞争 | 直接的经验假阳性率 |
| `n_valid` / `observed_fraction` / `m_enum` | 支持集与搜索空间规模 | — | 全部一等列 |
| `available_v1..v4` / `reason_v1..v4` | 各证据块可用性 | 由块内部派生 | `validation_status` 由此派生 |

**已删除且不得复现的列**：`system_proxy_ratio`、`label`、`deconf_p`、`composite_score`、`signal_retention`、`delta_pct`、`anion_stratified_*`、`repeated_subsample_*`、`above_noise_baseline`（由 `shadow_survival_rate` 取代）。

---

## 2.4 对照体系

```mermaid
flowchart LR
    subgraph TR["处理臂"]
        A1["真实描述符列"]
        A2["被选中的 top-k 公式"]
        A3["头条：全枚举最大值"]
    end
    subgraph CT["对照臂"]
        B1["影子列（真实列的列内置换副本）"]
        B2["random-k 与 bottom-k 公式"]
        B3["V1 体系内联合置换副本"]
        B4["外层 maxT 置换下的最大值"]
    end

    A1 --- B1
    A2 --- B2
    A2 --- B3
    A3 --- B4
```

**匹配维度检查表**——每个对照臂必须在"除与 y 的链接之外的一切维度"上与其处理臂匹配：

| 对照臂 | 边际分布 | 缺失模式 | 互相关 | 上游筛选路径 | 支持集大小 | 唯一被打断的 |
|---|---|---|---|---|---|---|
| 影子列 | ✔（列内置换） | ✔（继承 NaN） | ✘（可接受） | ✔（同走 Stage 1） | ✔ | 与 y 的配对 |
| random-k / bottom-k | ✔ | ✔ | ✔ | ✔（同一 Stage 3） | ✔ | 排序位置 |
| V1 联合置换 | ✔ | ✔ | ✔（共享置换） | 不适用 | ✔ | 与 y 的配对 |
| 外层 maxT | ✔ | ✔ | ✔ | ✔（每轮重跑全链） | ✔ | 与 y 的配对 + 整条选择链 |

对比当前状态：高斯噪声列在**四个维度上全部不匹配**，V1 在互相关维度不匹配，top-k 完全没有对照。

---

## 2.5 与当前管线的差异标注

**保持不变（当前设计里真正做对的部分，不要在重构中弄丢）**
- 组合算符的声明式注册表、交换算符规范无序对、比值方向显式登记、分母掩码、provenance 全程记录与严格 JSON 校验
- 稳定性选择的无放回 n/2 子采样、每子样本内独立拟合预处理
- build_feature_matrix 不做全量填充
- 体系内置换这个构思（V1）、体系分层自举这个重抽样方案（V4）
- 双轨隔离契约与冻结输入校验
- 描述符禁用 log/sqrt/power 的注册表约束、CIF 预检与有限值检查

**修改**
- 控制基构造：贪心秩筛选 → 行子集上的 QR/SVD 正交基
- 残差化：Ridge 收缩 → 投影，且双侧
- Stage 1：阈值判据 + 四分类标签 → 固定基数筛选，无标签
- Stage 2：单 alpha → λ 路径；y-依赖的族代表 → y-无关 medoid；高斯噪声基线 → 影子列同路径竞争
- Stage 3：新增增量有效性闸门；记录 m_enum 与支持集
- Stage 4：V2 改为正交得分 + 逐折聚合；V3 加闸门与合并；V4 自举主指标 + BCa；CV 只剩残差化目标上的 LOSO
- 报告：列名绑定估计量、availability 一等化、validation_status 派生

**新增**
- 影子列生成器
- 统一的 partial_rank_assoc 核心算子（取代散落调用点）
- 三个验证集合的划分（top-k / random-k / bottom-k）
- 外层体系内联合置换 maxT 循环
- 可选：外层嵌套 LOSO（W5-1，输出流程级估计）

**删除**（详见 W0-2）
- system_proxy_ratio、四分类标签、deconf_p、composite_score、signal_retention、delta_pct、above_noise_baseline、单列 X 上的模型包装、_formula_dimensionally_valid、_one_hot_encode、两条 CV 策略、YAML 中未实现或不存在的键

---

**最后一句诚实提醒**：这套架构完成后，你能声称的东西比现在**少得多**，且区间**宽得多**。这不是修复的副作用，这是修复的目的——当前那些数字之所以看起来强，很大一部分正是上面每一项要移除的东西贡献的。在数据集到达之前完成 Wave 0 与 Wave 1，是这个项目现在能做的回报率最高的事。
"""

with p.open("a", encoding="utf-8") as f:
    f.write(text)
print(f"Part 3 appended: {len(text)} chars")

# 验证完整文件
full = p.read_text(encoding="utf-8")
print(f"Full response file: {len(full)} chars, {full.count(chr(10)) + 1} lines")
