# Agent 结构描述符研究协议

本文件只规定 `results/agent/` 轨道。它与 `run_pipeline.py` 可以同时启动，
但在 C9 前必须独立运行和记录。

## 不可变契约

1. 先读取 `run_info.yaml` 的 `shared_input`、`data` 与 `tracks.agent`。原始 CSV
   和描述符注册表在一次研究批次中视为冻结输入。
2. 输入特征必须由注册的 CIF `Structure` 描述符计算；使用
   `train.py --descriptor-name <key>` 显式选择键。
3. 不预拆分训练、验证或测试集合。所有可用行通过共享的阴离子分层、留一体系和
   重复分层子采样 CV 接受审计。
4. 主指标是 `rank_corr_of_linear_residuals`（线性残差秩相关，非文献意义的
   partial Spearman；详见 run_info.yaml 的 estimand 段）。控制设计以 `system`
   为主，仅在秩上提供增量信息时再加入 `anion_type` 对比项。
5. 只写入 `results/agent/`。不得读取、修改、引用或根据 `results/pipeline/` 的
   中间/最终结果改变候选选择。

严格 CIF 预检和有限值检查是运行的一部分。若 CIF 缺失、不可解析，或描述符没有
足够的有效值，记录该次失败原因并停止该候选；不可用结果不能被写成成功指标。

## 单次 Agent 迭代

1. 在 `descriptors/idea.md` 说明候选的物理机制、涉及的物理族和预期混杂风险。
2. 仅在有新的、可说明的结构假设时修改/注册描述符；不得从标签反推特征。
3. 运行：

   ```bash
   python train.py --descriptor-name <descriptor-key> --run-id <iteration-id>
   ```
4. 审阅 TSV 中的 `raw_spearman`、`rank_corr_of_linear_residuals`。
   被标为 `skipped` 的策略应保持显式，不可补零或当作支持证据。
5. 在人工复核后，可用下一次命令的 `--status keep|discard|crash` 标记结果；默认
   状态是 `evaluated`。不要只因原始相关高或单一 CV 好看就标记为保留。
6. 运行 `python run_status.py`。它只根据 Agent 的有限线性残差秩相关记录和
   `tracks.agent.status` 停止条件输出 `CONTINUE` 或 `STOP`。

## 结果记录

`results/agent/results.tsv` 由评估器追加。其关键列是：

```text
run_id  descriptor_name  source_rows  finite_structural_values  analysis_rows
raw_spearman  rank_corr_of_linear_residuals  status
```

完整表还保留各策略 `skipped`/`reason`、MAE、折数和预处理可用性，以便追溯。
`results/agent/descriptor_features.csv` 是该次描述符值与 CIF 路径的审计副本；
`test_descriptors.py` 提供同样的独立结构审计，而非 held-out split 评估。

## 描述符纪律

- 不使用 `log`、`sqrt`、`power` 或任意无量纲依据的除法构造新特征。
- 组合必须有明确物理对象/族间机制；结果应标明探索性，不作因果陈述。
- 不使用非结构输入、结果文件或其他轨道的候选作为隐蔽信息来源。
- 某描述符与体系标签高度共线时，先报告它是体系代理的可能性，而不是宣称普适机制。

## C9 边界

C9 不是 Agent 的下一步自动操作。只有用户明确授权、Agent 和 Pipeline 两边均完成
并冻结后，才可对两个目录作**只读**比较。共同出现的候选只是独立三角验证或优先
复核线索；两轨都不建立因果关系。若结果不同，应报告搜索空间、混杂、缺失数据与
统计支持度的差异，而不是自动选择任一方。
