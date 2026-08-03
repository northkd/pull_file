# 双轨方案补充计划（v1.2，已实施契约）

> 更新日期：2026-08-03。此版本取代早期将轨道结果一致误写成“非常可靠”或因果
> 证据的表述。

## 0. 目的与研究边界

保留两条有意不同的轨道，目的是用独立的搜索偏倚提供三角验证线索：

| 维度 | Agent 轨道 | Pipeline 轨道 |
| --- | --- | --- |
| 入口 | `train.py --descriptor-name <key>` | `run_pipeline.py` |
| 搜索方式 | Agent 提出、逐个审计的结构假设 | 受登记物理规则约束的组合枚举 |
| 统计审计 | 共享的 Ridge CV + 秩感知去混杂 | 去混杂、稳定性、组合及 V1–V4 探索性证据 |
| 输出 | `results/agent/` | `results/pipeline/` |
| 因果结论 | 不建立 | 不建立 |

两轨共同发现候选时，只能称为独立三角验证、优先复核线索或方法一致性证据；它不使
关联变成因果，也不自动证明候选“非常可靠”。两轨分歧同样有价值，可能反映搜索空间、
数据缺失、体系混杂或统计支持度的差异。

## 1. 并发与隔离

Agent 与 Pipeline **可无顺序依赖地同时启动**。它们唯一允许共享的对象写在
`run_info.yaml: shared_input`：冻结的 `data/naconductor_raw.csv` 和描述符注册表
版本。其余规则为：

1. Agent 只写 `results/agent/`，并拒绝将其 CLI 工件指向 Pipeline 目录。
2. Pipeline 默认只写 `results/pipeline/`，不将 Agent 结果当作输入。
3. C9 前两条轨道都不得读取、修改或根据另一方结果调整保留/丢弃决定。
4. 共享实现（描述符、CV、去混杂）可以共同维护，但每次研究运行的原始输入和注册表
   修订必须冻结并记录。

目录契约：

```text
automat-naconductor/
├── data/naconductor_raw.csv       # 冻结共享输入
├── descriptors/                   # 冻结共享注册表与分析实现
├── train.py                       # Agent 结构描述符评估
├── test_descriptors.py            # Agent 独立结构审计
├── run_status.py                  # 仅读 Agent TSV
├── run_pipeline.py                # Pipeline 阶段式搜索
└── results/
    ├── agent/                     # Agent 唯一可写位置
    └── pipeline/                  # Pipeline 默认可写位置
```

## 2. Agent 轨道契约

旧的公式特征、随机森林和预拆分数据逻辑已移除。新流为：

```text
raw CSV + CIF paths
  → 全量 CIF 存在性/解析预检
  → registered Structure descriptor
  → rank-aware DeconfoundAnalyzer
  → fold-local imputation/scaling + Ridge MultiStrategyCV
  → results/agent/results.tsv + structural audit CSV
```

- `--descriptor-name` 必须显式给出；不依赖隐式默认键。
- CIF 相对路径相对 raw CSV 解析。缺失/不可解析 CIF 在写输出前失败；没有足够有限
  描述符值时也失败关闭。
- 阴离子分层、LOSO、重复子采样各自独立运行。不可行时记录 `skipped` 与原因，而非
  整体崩溃或把缺失策略计作零分。
- `run_status.py` 仅读取 `tracks.agent.results_file`，仅使用有限
  `deconfounded_spearman` 判断耐心和停止。`plot_run_results.py` 也只读取该 TSV。

## 3. Pipeline 轨道契约

Pipeline 默认输出为 `results/pipeline/`，并保持 C1–C8 中的筛选和 V1–V4 探索性
验证。它不读取 Agent 的 `results.tsv`、审计 CSV、图或候选。Pipeline 的结果报告必须
将体系/阴离子冗余、缺失 CIF、跳过的 CV 策略和探索性证据状态显式呈现。

## 4. C9：用户授权的只读比较

C9 的前提必须同时满足：

1. 用户明确授权执行 C9；
2. 两条轨道都已完成并冻结相应输出；
3. 比较过程只读 `results/agent/` 和 `results/pipeline/`，不回写或改变任一轨道；
4. 比较报告将一致性表述为三角验证线索，并保持非因果解释。

未满足这些前提时，不创建综合结果、不启动比较，也不要求 Agent 与 Pipeline 按任何
先后顺序执行。
