# Task 4 实施报告：Agent 轨道迁移与双轨并发隔离

日期：2026-08-03

## 完成的契约

Agent 与 Pipeline 现在可从同一份冻结 `run_info.yaml` 并发启动。二者只共享
`shared_input` 中的 raw CSV、结构描述符注册表路径和注册表修订号；C9 前不会读取
对方的结果目录。

| 轨道 | 输入 | 可写输出 | 明确禁止 |
| --- | --- | --- | --- |
| Agent | `shared_input.raw_file` + 注册表 | `results/agent/` | `results/pipeline/` 与任意非 Agent 相对路径 |
| Pipeline | 同一冻结 raw CSV + 注册表元数据 | `results/pipeline/` | `results/agent/` 与任意非 Pipeline 相对路径 |

`shared_input.frozen` 必须为 `true`。`data.raw_file` 和 `shared_input.raw_file` 都会
解析为相对于选定 `--run-info` 的路径，并且必须相等；不匹配会在 CLI 参数解析阶段失败。
`shared_input.descriptor_registry` 还必须存在，并解析为运行中实际导入的
`descriptors/__init__.py`，而非仅仅记录一个字符串。Agent 不再提供 raw 文件、CIF 列或
目标列的命令行覆盖，因此不能把不同数据批次静默写入相同 Agent 目录。

## 代码改动

### Agent 结构评估器

- `automat_utils.py`
  - 用 `AVAILABLE_STRUCTURE_DESCRIPTORS`、CIF `Structure` 加载和单描述符结构特征化
    替换旧栈。
  - 对完整 raw CSV 实施 CIF 路径存在性和可解析性预检；预检发生在任何输出目录创建前。
  - 描述符全 NaN、有限值少于 5，或目标/描述符交集少于 5 行时失败关闭。
  - 使用共享 `DeconfoundAnalyzer`（system 主控制、秩增量 anion 控制）和共享
    `MultiStrategyCV` 的折内填补/标准化/Ridge。
  - 三种 CV 策略独立执行；如 LOSO 在单体系数据中不可行，记录显式 `skipped` 与原因，
    不会杀死整次结构评估。
  - 结果 TSV 与结构审计 CSV 均记录 canonical `shared_raw_file`、实际导入的
    `descriptor_registry`、`registry_revision`。
  - 在写入任何 Agent 工件前，统一校验已有 TSV 和已有审计 CSV 的三项身份列：必须
    完整、单一且等于本次冻结输入；写入函数也会重复校验以防止绕过入口。

- `train.py`
  - 新公开接口：`parse_agent_args(argv=None)`；`--descriptor-name` 必填，默认结构列
    来自 `data.structure_column`（当前为 `cif_path`）。
  - 仅在成功完成预检和评估后写 `results/agent/results.tsv` 与
    `results/agent/descriptor_features.csv`。
  - 结果和审计均通过身份预检后才写入；冲突会清晰输出 `ERROR` 并以 exit 2 退出，
    不会先覆盖审计再发现 TSV 冲突。
  - 移除了旧的预拆分数据、公式特征化和随机森林配置依赖。

- `test_descriptors.py`
  - 保留文件名作为兼容入口，但现在只运行独立结构审计；不再做 held-out split 评估，
    不写 Pipeline 结果。

- `run_status.py`、`plot_run_results.py`
  - `resolve_results_file(config)` 返回 `tracks.agent.results_file`，不再读取 legacy
    logging/autoresearch 配置。
  - 停止条件只基于状态为 `evaluated`、`keep`、`discard` 的有限
    `deconfounded_spearman`；`crash` 和不可用策略不消耗耐心。
  - 两个读取端都要求冻结 raw/registry 标识列，并验证 TSV 中每一列仅有一个值且等于
    当前 `run_info` 解析出的 canonical 身份；拒绝未版本化、混合或外来批次结果。
  - 绘图只读取 Agent TSV，展示 raw/deconfounded Spearman 与最佳绝对去混杂相关历史。

### Pipeline 与配置隔离

- `run_pipeline.py`
  - 添加 `--run-info`，其默认 `--output-dir` 从 `tracks.pipeline.output_dir` 读取。
  - Pipeline 输出目录必须是相对 `results/pipeline/...`，因此命令行覆盖不能指向
    `results/agent/...`。
  - Stage 0 从冻结配置解析的 raw/featurized 文件和列名读取，而不再静默硬编码路径。
  - 在开始任何特征化前验证 `shared_input.frozen: true`、
    `data.raw_file == shared_input.raw_file`、实际注册表路径绑定和注册表修订元数据。

- `run_info.yaml`
  - 添加 `data.featurized_file`、`shared_input`、`tracks.pipeline`、`tracks.agent` 与
    `c9_cross_track_review`。
  - C9 记录为必须用户授权、两边完成并冻结、仅只读输入的后续步骤。

### 文档与依赖

- `README.md`、`program.md` 与 `.omo/plans/automat-reform-dual-track.md` 更新为实际的
  双轨并发/隔离契约。
- 文档明确：两轨一致只是独立三角验证或优先复核线索；两轨都不建立因果关系。
- `pyproject.toml` 更新项目描述，并显式加入 `scipy`、`matplotlib`。
- 删除不再使用的组合旧注册表别名，避免误用为非结构路径。

## 测试（先红后绿）

新增 `tests/test_agent_track.py`，覆盖：

1. 显式结构 Agent CLI，没有旧的列/数据切分属性；
2. `resolve_results_file` 只使用 `tracks.agent.results_file`；
3. 状态读取拒绝缺少冻结批次标识的旧结果 TSV；
4. Agent 和 Pipeline 的跨轨输出路径覆盖被拒绝；
5. Agent 与 Pipeline 都拒绝未冻结或不匹配的 raw CSV 配置；
6. Agent 与 Pipeline 都拒绝不存在或不等于活动模块的注册表路径；
7. 缺 CIF 在 Agent 输出目录建立前失败；
8. 单体系下不可行 LOSO 显式 `skipped` 而总体评估仍返回；
9. Pipeline 默认输出从 `tracks.pipeline.output_dir` 取得；
10. 外来/混合身份 TSV 被 status 与 plot 拒绝；
11. 外来结果 TSV 或外来审计 CSV 均在任何新 Agent 工件写入前被拒绝，sentinel 审计
    内容保持不变。

实际 RED 证据包括：缺失 `evaluate_structural_descriptor` 导入、单体系
`LeaveOneGroupOut` 的 `ValueError`、未拒绝的 Pipeline 输出覆盖，以及未拒绝的冻结
输入不匹配、注册表路径未绑定、审计先覆盖后才发现 TSV 冲突，以及读取端接受外来/混合
批次。随后都变为 GREEN。

最终验证（在 `automat-naconductor/`）：

```text
pytest -q                                      # 67 passed
python -m compileall -q ...                    # exit 0
python train.py --help                         # exit 0
python train.py --run-info run_info.yaml --help # exit 0
python run_status.py --help / --run-info ...   # exit 0
python run_pipeline.py --help / --run-info ... # exit 0
python train.py --descriptor-name a2_max_dist  # exit 2：84 个缺 CIF 的清晰预检错误
```

最后一条 smoke test 后确认 `results/agent/` 与 `results/pipeline/` 均未创建，证明失败
发生在写入前。

## 有意保留的研究限制

当前 checkout 中 raw CSV 所指的 CIF 文件不可用。真实 Agent/Pipeline 运行因此会在
严格预检处清晰失败，且不会把全缺失特征或伪结果写成科学发现；本任务没有修改 raw、
CIF 或现有 featurized 数据。只有在补齐并冻结这些 CIF 后，才应运行真实研究评估。
