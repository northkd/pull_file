# 双轨方案补充计划 (v1.1 增补)

> 基于用户决策：方案A（agent驱动）+ 方案B（Python流水线）并行，结果先各自展示给用户确认，再做综合评估
> 日期: 2026-08-02

---

## 0. 为什么保留两个方案

两个方案的**搜索哲学**根本不同：

| 维度 | 方案A: Agent驱动 | 方案B: Python流水线 |
|------|-----------------|-------------------|
| 搜索方式 | Agent自由探索，每次提出新想法 | 确定性穷举，物理约束限定搜索空间 |
| 组合发现 | 可能发现计划外的意外组合 | 只能找到约束空间内的组合 |
| 偏倚方向 | 偏向Agent认为"合理"的方向 | 偏向预设物理分组认为"合法"的方向 |
| 可复现性 | 低（依赖agent推理） | 高（确定性算法） |
| 过拟合风险 | 高（agent可能过拟合训练集模式） | 中（穷举但有噪声基线保护） |
| 因果推断 | 无（agent不理解混杂） | 有（去混杂是核心步骤） |

**如果两个方案找到相同的 top 组合** → 结果非常可靠（两种完全不同的搜索策略收敛到同一答案）

**如果两个方案找到不同的 top 组合** → 分析分歧原因，可能揭示：
- 方案A发现了物理分组规则遗漏的合法组合
- 方案B的约束空间内确实有方案A忽略的组合
- 某个组合的信号来自体系混杂而非物理（方案A无法检测，方案B可以）

---

## 1. 双轨文件结构

```
automat-naconductor/
├── program.md                    # [方案A] Agent契约（改造版）
├── run_info.yaml                 # [共用] 任务配置
├── run_status.py                 # [方案A] 停止判断
├── train.py                      # [方案A] 评估入口（改造版）
├── automat_utils.py              # [方案A] 工具函数（改造版）
├── pipeline.py                   # [方案B] 4阶段流水线入口
├── evaluate.py                   # [方案B] 综合评估
├── cv_strategies.py              # [共用] 多策略CV
├── deconfound.py                 # [共用] 去混杂分析
├── stability_selection.py        # [方案B] Stability Selection
├── physical_grouping.py          # [方案B] 物理分组去冗余
├── combination_search.py         # [方案B] 物理约束组合搜索
├── combination_validate.py       # [方案B] 组合验证
├── cross_evaluate.py             # [新增] 双轨综合评估
├── data/
│   ├── naconductor_raw.csv       # [共用] 原始数据
│   └── naconductor_featurized.csv # [共用] 描述符计算后
├── descriptors/
│   ├── __init__.py               # [共用] 描述符注册
│   ├── family_a_polyhedron.py    # [共用] ...
│   └── ...                       # [共用] 其余7族
├── featurizer.py                 # [共用] 从CIF批量计算
├── skills/
│   └── end-of-run-report/        # [方案A] 运行报告Skill
├── results/
│   ├── pipeline/                 # [方案B] 流水线输出
│   │   ├── stage1_deconfound.csv
│   │   ├── stage1_stability.csv
│   │   ├── stage2_representatives.csv
│   │   ├── stage3_combinations.csv
│   │   ├── stage4_validation.csv
│   │   └── final_report.md
│   └── agent/                    # [方案A] Agent输出
│       ├── results.tsv
│       ├── ideas.tsv
│       └── idea_history/         # 各代idea.md快照
└── cross_evaluation/
    └── comparison_report.md      # [综合] 双轨对比报告
```

---

## 2. 方案A: Agent驱动 — 改造规范

### 2.1 program.md 改造要点

原始 `program.md` 的核心契约需要修改以下部分：

```
原始: "Input features must be derived from chemical formulas only."
改造: "Input features must be derived from CIF crystal structures via 
      the registered descriptors in descriptors/__init__.py."

原始: "Each run uses the pre-split local data declared in run_info.yaml."
改造: "Each run uses the full dataset declared in run_info.yaml. 
      Cross-validation strategies (anion-stratified, LOSO, within-system) 
      replace simple train/test splits."

原始: "Descriptor keep/discard decisions use only train-set CV, normally cv_mae."
改造: "Descriptor keep/discard decisions use deconfounded Spearman correlation 
      as the primary metric. Raw Spearman and LOSO MAE are secondary metrics. 
      A descriptor is kept only if:
      1. deconfounded_spearman > noise_baseline_95th_percentile, AND
      2. deconfounded_spearman improves over the current best."

原始: "Descriptors may use any deterministic formula-derived information from pymatgen"
改造: "Descriptors must use CIF structure-derived information from pymatgen. 
      Combination operators are restricted to: add (+), multiply (×), 
      and same-dimension ratio (/). Log, square root, power, and arbitrary 
      division are PROHIBITED as they destroy physical interpretability."

新增: "Physical object constraint: descriptors may only be combined if they 
      describe the same physical object (same family) or adjacent families 
      with a documented physical mechanism. Cross-family combinations without 
      a physical explanation are PROHIBITED."

新增: "System deconfounding: the agent MUST run deconfound.py on every 
      proposed descriptor/combination before keep/discard decision. 
      A descriptor labeled as '体系代理' (>70% system proxy ratio) 
      cannot be the primary basis for a keep decision."
```

### 2.2 train.py 改造要点

原始 `train.py` 的核心逻辑是 `featurize(composition) → RF → cv_mae`，需要改为：

```python
# 改造后的 train.py 核心逻辑
def evaluate_descriptor(args):
    # 1. 加载数据（含CIF路径）
    df = load_local_frame(...)
    y = df[args.target_column].values
    system_labels = df[args.system_column].values

    # 2. 计算描述符
    featurize = make_featurizer(args.descriptor_name)
    X = featurize(df[args.cif_column])  # 从CIF计算

    # 3. 去混杂分析
    deconf_result = DeconfoundAnalyzer().analyze_single_descriptor(
        X.flatten(), y, system_labels, args.descriptor_name
    )

    # 4. 多策略CV
    cv_metrics = MultiStrategyCV().anion_stratified_cv(X, y, anion_labels)
    loso_metrics = MultiStrategyCV().loso_cv(X, y, system_labels)

    # 5. 噪声基线
    noise_baseline = compute_noise_baseline(X, y, n_noise=15, seed=42)

    # 6. 综合判定
    metrics = {
        'raw_spearman': deconf_result['raw_spearman'],
        'deconfounded_spearman': deconf_result['deconfounded_spearman'],
        'system_proxy_ratio': deconf_result['system_proxy_ratio'],
        'label': deconf_result['label'],
        'anion_cv_mae': cv_metrics['mean_mae'],
        'loso_mae': loso_metrics['mean_mae'],
        'noise_baseline_95th': noise_baseline['percentile_95'],
        'passes_noise_baseline': abs(deconf_result['raw_spearman']) > noise_baseline['percentile_95'],
    }

    # 7. 打印结果
    print(f"raw_spearman:           {metrics['raw_spearman']:.6f}")
    print(f"deconfounded_spearman:  {metrics['deconfounded_spearman']:.6f}")
    print(f"system_proxy_ratio:     {metrics['system_proxy_ratio']:.6f}")
    print(f"label:                  {metrics['label']}")
    print(f"anion_cv_mae:           {metrics['anion_cv_mae']:.6f}")
    print(f"loso_mae:               {metrics['loso_mae']:.6f}")
    print(f"noise_baseline_95th:    {metrics['noise_baseline_95th']:.6f}")
    print(f"passes_noise_baseline:  {metrics['passes_noise_baseline']}")

    return metrics
```

### 2.3 run_status.py 改造要点

停止条件从 `cv_mae不再改善` 改为：

```python
# 改造后的停止条件
decision = "STOP" if (
    max_iterations_reached or
    patience_reached or
    # 新增: 去混杂Spearman连续N次无改善
    deconf_spearman_patience_reached
) else "CONTINUE"
```

### 2.4 idea.md 模板改造

```markdown
# Descriptor Proposal: <name>

## Problem Knowledge
<!-- 简述Na离子导体电导率问题，可从前次迭代中丰富 -->

## Scientific Insight
<!-- 物理和化学考虑：为什么这个描述符/组合可能有信号？
    必须说明物理机制，不能只说"试试看" -->

## Physical Object Grouping
<!-- 新增：这个描述符属于哪个物理族？如果涉及组合，说明涉及哪些族，
    跨族组合的物理机制是什么 -->

## Deconfounding Check
<!-- 新增：这个描述符是否可能成为体系代理信号？
    如果跨体系差异很大（如氧化物vs硫化物），说明如何区分
    体系效应和体系内物理 -->

## Implementation Strategy
<!-- 自然语言描述实现方案，不含代码 -->

## Dependencies
<!-- 依赖的库和文件 -->
```

### 2.5 automat_utils.py 改造要点

核心改动：`featurize_formula(Composition)` → `featurize_cif(cif_path)`

```python
def make_featurizer(descriptor_name: str):
    """从描述符注册表创建featurizer（改造版）
    原始: 接受 Composition → 计算
    改造: 接受 cif_path → 从CIF读取Structure → 计算
    """
    descriptor_fn = AVAILABLE_STRUCTURE_DESCRIPTORS[descriptor_name]

    @lru_cache(maxsize=None)
    def featurize_cif(cif_path: str) -> tuple[float, ...]:
        struct = Structure.from_file(cif_path)
        features = np.asarray(descriptor_fn(struct), dtype=np.float32)
        if features.ndim != 1:
            raise ValueError(...)
        return tuple(float(x) for x in features)

    def featurize(cif_paths) -> np.ndarray:
        x = np.asarray([featurize_cif(str(p)) for p in cif_paths], dtype=np.float32)
        return x

    return featurize
```

### 2.6 results.tsv 格式改造

```
原始: commit  cv_mae  cv_mae_std  val_mae  status  descriptor_name  description
改造: commit  deconf_spearman  raw_spearman  system_proxy_ratio  anion_cv_mae  loso_mae  status  descriptor_name  description
```

### 2.7 Agent 运行时的限制

Agent 驱动模式下，agent 需要遵守以下额外规则（写入 program.md）：

1. **不能使用禁止算符**：log、√、幂次、任意除法。只能用 +、×、同量纲比值
2. **不能做无机制的跨族组合**：每次提出组合时必须在 idea.md 的"Physical Object Grouping"节说明物理机制
3. **必须先跑去混杂再决定 keep/discard**：去混杂分析不是可选项，而是每次迭代的必做步骤
4. **不能使用 RF importance 做特征筛选**：RF importance 不等于因果效应
5. **keep 判定用 deconfounded_spearman**：不用 cv_mae

---

## 3. 方案B: Python流水线 — 不变

方案B 就是原计划中的 C1-C8，不需要修改。`pipeline.py` 一键跑完4阶段。

---

## 4. 新增 C9: 双轨综合评估（⚠️ 需用户确认后执行）

> **前置条件**：用户必须在检查点③明确决定"做综合评估"。如果用户选择直接采纳某个方案的结果，或要求调整参数重跑，则不执行C9。

### 目标

对比方案A和方案B的搜索结果，回答：
1. 两种方法找到的 top 组合是否一致？
2. 如果不一致，分歧的原因是什么？
3. 哪个结果更可靠？

### 输入

- `results/pipeline/final_report.md`（方案B输出）
- `results/agent/results.tsv` + `ideas.tsv`（方案A输出）
- 特征矩阵 + 目标 + 体系标签（共用数据）

### 输出

- `cross_evaluation/comparison_report.md`

### 实现细节

```python
"""cross_evaluate.py: 双轨综合评估"""

class CrossEvaluator:
    """对比方案A（agent驱动）和方案B（流水线）的搜索结果"""

    def compare_top_combinations(self, agent_top5, pipeline_top5,
                                  feature_df, y, system_labels):
        """对比两个方案的 Top-5 组合"""

        # 1. 找交集和差异
        agent_formulas = set(agent_top5['formula'])
        pipeline_formulas = set(pipeline_top5['formula'])
        overlap = agent_formulas & pipeline_formulas
        agent_only = agent_formulas - pipeline_formulas
        pipeline_only = pipeline_formulas - agent_formulas

        # 2. 对 agent 发现的组合做方案B的完整验证
        # （agent 无法做去混杂+噪声基线+Factor Spanning，这里补上）
        agent_validated = []
        for formula in agent_formulas:
            combo_values = compute_combo_values(formula, feature_df)
            validation = CombinationValidator().full_validation(
                combo_values, y, system_labels, known_factors, noise_cols_data
            )
            agent_validated.append({
                'formula': formula,
                'source': 'agent',
                **validation,
            })

        # 3. 对 pipeline 发现的组合也统一验证（确保对比公平）
        pipeline_validated = []
        for formula in pipeline_formulas:
            combo_values = compute_combo_values(formula, feature_df)
            validation = CombinationValidator().full_validation(
                combo_values, y, system_labels, known_factors, noise_cols_data
            )
            pipeline_validated.append({
                'formula': formula,
                'source': 'pipeline',
                **validation,
            })

        # 4. 合并排序
        all_validated = agent_validated + pipeline_validated
        all_df = pd.DataFrame(all_validated)
        all_df = all_df.sort_values('deconfounded_spearman', key=abs, ascending=False)

        return {
            'overlap': overlap,
            'agent_only': agent_only,
            'pipeline_only': pipeline_only,
            'all_validated': all_df,
            'concordance': len(overlap) / max(len(agent_formulas), 1),
        }

    def analyze_divergence(self, agent_only, pipeline_only,
                           feature_df, y, system_labels):
        """分析两个方案结果分歧的原因"""

        reasons = {}

        for formula in agent_only:
            # Agent发现了但Pipeline没发现 → 为什么？
            # 可能原因:
            # a. Agent的组合违反了Pipeline的物理约束（跨了不该跨的族）
            # b. Agent的组合用了禁止算符
            # c. Agent的组合在Pipeline的穷举范围内但排序靠后
            combo_info = parse_formula(formula)
            violation = check_physical_constraints(combo_info)
            if violation:
                reasons[formula] = f"Agent组合违反物理约束: {violation}"
            else:
                # 检查是否在Pipeline的候选列表中
                in_pipeline_space = check_in_search_space(combo_info)
                if in_pipeline_space:
                    reasons[formula] = "Agent组合在Pipeline搜索空间内但排序靠后"
                else:
                    reasons[formula] = "Agent组合超出Pipeline搜索空间（Pipeline约束过严？）"

        for formula in pipeline_only:
            # Pipeline发现了但Agent没发现 → 为什么？
            # 可能原因:
            # a. Agent没探索到这个方向（随机性）
            # b. Agent迭代次数不够
            # c. Agent的keep/discard逻辑提前淘汰了相关描述符
            reasons[formula] = "Pipeline穷举发现但Agent未探索到"

        return reasons

    def generate_comparison_report(self, comparison, divergence, 
                                    agent_top5, pipeline_top5) -> str:
        """生成双轨对比报告"""
        lines = [
            "# 双轨搜索结果综合对比\n",
            f"## 概览\n",
            f"- 方案A (Agent驱动) 发现 {len(agent_top5)} 个候选组合",
            f"- 方案B (Python流水线) 发现 {len(pipeline_top5)} 个候选组合",
            f"- 交集: {len(comparison['overlap'])} 个",
            f"- 一致率: {comparison['concordance']:.0%}\n",
        ]

        if comparison['concordance'] > 0.6:
            lines.append("### 判定: 两个方案高度一致 ✅\n")
            lines.append("两种完全不同的搜索策略收敛到相似的答案，")
            lines.append("表明 top 组合是数据中的真实信号，非方法依赖的假象。\n")
        elif comparison['concordance'] > 0.2:
            lines.append("### 判定: 两个方案部分一致 ⚠️\n")
            lines.append("共享的组合更可靠；独有组合需要额外验证。\n")
        else:
            lines.append("### 判定: 两个方案高度不一致 ❌\n")
            lines.append("需要深入分析分歧原因，可能提示搜索策略偏倚或数据信号弱。\n")

        lines.append("## 分歧分析\n")
        for formula, reason in divergence.items():
            lines.append(f"- **{formula}**: {reason}\n")

        lines.append("\n## 统一验证结果\n")
        lines.append(comparison['all_validated'].to_markdown(index=False))

        lines.append("\n## 最终推荐\n")
        # 推荐逻辑: 交集 > 方案B独有 > 方案A独有（因为方案B有去混杂保护）
        shared = comparison['overlap']
        if shared:
            lines.append(f"**最高推荐**: 两个方案共同发现的组合 {shared}\n")
            lines.append("这些组合经过了两种搜索策略的独立验证，可靠性最高。\n")
        lines.append("**次推荐**: 方案B流水线独有但通过4重验证的组合\n")
        lines.append("这些组合通过了去混杂+噪声基线+Factor Spanning+Bootstrap CI验证。\n")
        lines.append("**需谨慎**: 方案A Agent独有但通过4重验证的组合\n")
        lines.append("这些组合可能发现了Pipeline约束空间外的合理组合，")
        lines.append("但也可能受益于Agent的过拟合偏倚。\n")

        return "\n".join(lines)
```

### 验收标准

- [ ] 双轨对比报告包含一致率、分歧分析、统一验证表
- [ ] Agent 发现的所有组合都补跑了去混杂+4重验证
- [ ] Pipeline 发现的所有组合也在统一条件下重新验证（公平对比）
- [ ] 分歧原因分析能区分"违反物理约束""搜索空间内但排序低""超出搜索空间"
- [ ] 最终推荐有明确的优先级：交集 > Pipeline独有 > Agent独有

---

## 5. 执行策略

### 5.1 顺序（含用户检查点）

```
C1(数据层) → C2(描述符) → C3(特征矩阵)
                                │
                ┌───────────────┼───────────────┐
                │               │               │
          C4(CV策略)      C5(去混杂)       C6(Stability+分组)
                │               │               │
                └───────────────┼───────────────┘
                                │
                          C7(组合搜索)
                                │
                          C8(组合验证)
                                │
                                ▼
                    ┌───────────────────────┐
                    │  🔍 检查点①: 方案B结果  │
                    │  给用户看 final_report │
                    │  用户确认/提意见       │
                    └───────────┬───────────┘
                                │ 用户确认后
                                ▼
                    方案A: Agent启动
                    (用改造后的program.md
                     驱动agent迭代)
                                │
                                ▼
                    ┌───────────────────────┐
                    │  🔍 检查点②: 方案A结果  │
                    │  给用户看 results.tsv  │
                    │  用户确认/提意见       │
                    └───────────┬───────────┘
                                │ 用户确认后
                                ▼
                    ┌───────────────────────┐
                    │  🔍 检查点③: 用户决策   │
                    │  是否做C9综合评估？     │
                    │  是否调整参数重跑？     │
                    │  是否直接选一个方案？    │
                    └───────────┬───────────┘
                          ┌─────┴─────┐
                          │           │
                     做C9综合评估   其他选择
```

**三个检查点的具体内容**：

| 检查点 | 时机 | 展示内容 | 用户要判断什么 |
|--------|------|---------|--------------|
| ① 方案B结果 | C8完成后 | `final_report.md`: Top-5组合的公式、去混杂ρ、物理解释、4重验证结果 | 这些组合物理上说得通吗？去混杂比例合理吗？有没有明显遗漏的合法组合？ |
| ② 方案A结果 | Agent迭代结束后 | `results.tsv` + 历代 `idea.md`: keep的组合、agent的推理过程 | Agent有没有跑偏？有没有发现方案B遗漏的有趣组合？keep的组合物理机制是否成立？ |
| ③ 用户决策 | 看完两个方案结果后 | 两个方案的对比摘要 | 是否需要C9？还是直接选一个方案的结果？还是需要调整参数重跑某个方案？ |

**重要：C9不是自动执行的，必须等用户在检查点③明确说"做综合评估"才启动。**

### 5.2 方案A的启动方式

Agent 驱动有两种操作模式：

**模式1: 在 OpenCode 中启动**
```
你在 OpenCode 对话中说:
"请按照 automat-naconductor/program.md 的规范，开始 Na 导体描述符搜索的 autoresearch 运行"
→ build agent 读取 program.md，按实验循环执行
```

**模式2: 在 Codex 中启动**
```
将 automat-naconductor/ 目录上传到 Codex，
在 Codex 会话中说:
"Read program.md and start the autoresearch experiment loop"
→ Codex agent 按契约执行迭代
```

**模式3: 手动模拟**
```
你自己读 program.md，手动执行每一步：
1. 想一个新描述符/组合
2. 写 idea.md
3. 实现 idea.py
4. 运行 train.py
5. 判断 keep/discard
6. 记录到 results.tsv
7. 运行 run_status.py 判断是否继续
```

### 5.3 时间估算

| 任务 | 估算时间 |
|------|---------|
| C1-C8 (共享基础设施 + 方案B) | 2-3天 |
| 方案A (Agent迭代，~20-30次) | 1-2天 |
| C9 (双轨综合评估) | 0.5天 |
| **合计** | **3.5-5.5天** |

---

## 6. 两种方案结果的综合解读框架

```
情况1: 两个方案的 Top-3 高度重叠（一致率 > 60%）
  → 结论: 重叠的组合是数据中的真实信号
  → 论文写法: "两种独立搜索策略收敛到相同的描述符组合，
               表明该组合与电导率的关系不受搜索方法偏倚的影响"

情况2: 两个方案的 Top-3 完全不重叠（一致率 < 20%）
  → 可能原因:
    a. 数据信号太弱，两种方法都在拟合噪声 → 需要更多样本
    b. 方案A的约束太松，找到了过拟合组合 → 检查去混杂后是否仍显著
    c. 方案B的约束太严，遗漏了合法组合 → 检查被排除的组合
  → 论文写法: 诚实报告两种方法的分歧，分析原因

情况3: 两个方案部分重叠（一致率 20-60%）
  → 重叠部分: 高置信度信号
  → 独有部分: 标记为"方法依赖"，需额外验证
  → 论文写法: 分别报告高置信和需验证的组合
```

---

*增补结束。此文件与 automat-reform.md 和 automat-reform-errata.md 共同构成完整计划。*
