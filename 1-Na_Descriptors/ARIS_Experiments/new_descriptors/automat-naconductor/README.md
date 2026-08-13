# automat-naconductor

`automat-naconductor` 用 CIF 晶体结构计算 Na 离子导体描述符，并提供两条
**可同时运行、彼此隔离**的研究轨道：

| 轨道 | 入口 | 产物 | 作用 |
| --- | --- | --- | --- |
| Pipeline | `run_pipeline.py` | `results/pipeline/` | 受物理规则约束的组合搜索与 V1–V4 探索性验证 |
| Agent | `train.py` | `results/agent/` | 对 Agent 明确提出的单个结构描述符进行独立审计 |

两条轨道只共享 `run_info.yaml: shared_input` 中冻结的原始 CSV 和描述符注册表。
它们可以无顺序依赖地并发启动；在用户授权的 C9 之前，Agent 不读取
`results/pipeline/`，Pipeline 也不读取 `results/agent/`。

## 数据与统计契约

- 输入是 `data/naconductor_raw.csv` 中的 `cif_path`。相对路径以该 CSV 所在
  目录为准解析。
- 每次 Agent 评估都对全部 CIF 做存在性和可解析性预检。预检失败会在创建
  任何 Agent 输出前失败退出；全 NaN 描述符同样会失败，不会产生假阳性结果。
- `log_sigma` 已是目标变量。主指标是控制以 `system` 为主、仅保留秩增量
  `anion_type` 对比项后的 `rank_corr_of_linear_residuals`。
- Ridge 的填补和标准化均在每一个 CV 训练折内拟合。阴离子分层、留一体系和
  重复分层子采样中，任何不可行的策略会显式记录为 `skipped`，而不是被当作零分
  或导致整个评估崩溃。
- 当前检出的是关联性/预测稳健性证据，不建立因果关系。

当前工作区若缺少原始 CSV 指向的 CIF，两个入口都会给出清晰的预检错误；不要把
旧的全缺失特征化文件当作研究结果。

## 并发启动

在项目根目录 `automat-naconductor/` 中，以下命令可以在两个终端并发运行：

```bash
python run_pipeline.py
python train.py --descriptor-name a2_max_dist --run-id agent-001
```

Pipeline 的默认输出目录是 `results/pipeline/`。Agent 的结果、描述符值审计和图
分别位于 `results/agent/results.tsv`、`results/agent/descriptor_features.csv` 和
`results/agent/figures/`；CLI 会拒绝将 Agent 工件写入 Pipeline 路径。

Agent 的独立结构审计（历史 `test_descriptors.py` 的兼容入口）为：

```bash
python test_descriptors.py --descriptor-name a2_max_dist
```

它不是预拆分的 held-out 测试，而是对同一冻结 CIF 数据进行可复核的结构审计。

## Agent 轨道

`train.py` 不选择隐式默认描述符。每次运行必须显式给出
`--descriptor-name`，其键来自 `descriptors.AVAILABLE_STRUCTURE_DESCRIPTORS` 的
活跃描述符。一次成功评估会：

1. 严格加载 raw CSV 与 CIF `Structure`；
2. 计算该结构描述符；
3. 使用 `DeconfoundAnalyzer` 的秩感知控制设计；
4. 使用共享 `MultiStrategyCV` 的 Ridge 管线；
5. 将审计 CSV 和一行 TSV 指标写入 `results/agent/`。

停止判断和绘图也只读取 Agent 产物：

```bash
python run_status.py
python plot_run_results.py
```

`run_status.py` 只以有限的 `rank_corr_of_linear_residuals` 记录判断改善；`crash` 行和
不可用 CV 策略不会制造“没有改善”的证据。具体的最大迭代数与耐心值在
`tracks.agent.status` 中配置。

## Pipeline 轨道

```bash
python run_pipeline.py --top-k 10
```

Pipeline 依次完成描述符审计、稳定性选择、受约束的二/三元组合搜索和 V1–V4
探索性验证。它默认写入 `results/pipeline/`，也不将 Agent 的候选或结果作为输入。
如需在测试中指定另一个输出目录，可显式传 `--output-dir`。

## C9：仅在用户授权后进行只读比较

当且仅当用户明确要求 C9，并且两边的输出都已经完成、冻结后，才可对
`results/agent/` 和 `results/pipeline/` 做只读对比。两轨发现相同的候选只代表独立
三角验证或应优先复核的线索；不代表“非常可靠”的定论，更不构成因果证据。两轨
结果不一致同样是需要追溯搜索空间、混杂和数据支持度的研究信息。

## 主要文件

- `run_info.yaml`：冻结输入、CV/去混杂设置、两条轨道的输出隔离契约。
- `descriptors/`：CIF 结构描述符注册、特征化、CV、去混杂、稳定性和组合验证。
- `train.py`、`automat_utils.py`：Agent 的结构描述符评估器。
- `test_descriptors.py`：Agent 的独立结构审计入口。
- `run_status.py`、`plot_run_results.py`：只针对 Agent TSV 的停止判断与可视化。
- `program.md`：Agent 研究纪律与可审计记录格式。
