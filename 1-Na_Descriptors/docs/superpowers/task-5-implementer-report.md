# Task 5 实施报告：最终集成验证与修改记录

日期：2026-08-03

## 完成范围

完成了最终的 Pipeline/Agent 集成验证、两处由端到端测试发现的最小修复，以及详细中文
修改记录。没有修改 raw CSV、CIF、已特征化数据或项目内研究结果目录；所有有写入的
集成运行均使用 pytest 的临时 `results/pipeline` 目录。

新增文件：

- `ARIS_Experiments/new_descriptors/automat-naconductor/tests/test_pipeline_integration.py`
- `ARIS_Experiments/new_descriptors/automat-naconductor/修复记录_2026-08-03.md`

修改文件：

- `ARIS_Experiments/new_descriptors/automat-naconductor/run_pipeline.py`

## 端到端 RED → GREEN

### RED 1：三元式在真实 Stage 2→3 路径中不可达

新的合成回归构造了覆盖八个物理族的数值特征，其中 A 族有两个独立稳定特征、B 族有一个
稳定特征。旧 `runStage2` 没有 `max_descriptors` 契约，并且无论三元模式与否都使用
`PhysicalGrouper(max_per_family=1)`。因此当八族均有代表时，Stage 3 无法获取同族两个候选。

初始命令：

```text
pytest -q tests/test_pipeline_integration.py
```

初始结果：

```text
TypeError: runStage2() got an unexpected keyword argument 'max_descriptors'
```

这对应了更深层的行为缺口：Stage 2 没有接收 Stage 3 的二元/三元容量配置，不能保证
计划允许的 A/A/B 等三元公式实际可达。

### GREEN 1：三元模式下每族保留至多两个稳定候选

`runStage2(..., max_descriptors=2|3)` 现在遵守以下最小联动：

- pair-only（2）时每族最多 1 个稳定代表，保留原有筛选语义；
- triple（3）时每族最多 2 个稳定候选；第二个名额仅用于受限的三元公式候选池，不能当作
  第二项独立科学发现；
- `main()` 将冻结的 `args.max_descriptors` 同时传入 Stage 2 和 Stage 3；
- 最终报告显示每族候选池容量及其解释边界。

回归顺序执行 Stage 1、Stage 2、Stage 3、Stage 4，确认：

- Stage 1 的 9 个有效结构描述符进入受控候选池；
- Stage 2 在 max=3 下保留两个 A 和一个 B；
- Stage 3 产生 `n_components=3` 候选；
- Stage 3 CSV 的 `components`、`operators`、`formula_provenance` 严格 JSON 往返；
- 重新读入该三元 CSV 后，Stage 4 保持三元式而不降级为 pair；
- Stage 4 CSV 保存 V1–V4 的各个 JSON evidence block；
- 一例 iodide 使 anion CV 明确 `skipped`，但 LOSO 与 repeated subsample 仍可用。

结果：

```text
pytest -q tests/test_pipeline_integration.py
...                                                                      [100%]
3 passed in 2.65s
```

### Follow-up：容量必须是硬上限

最终复核发现旧 `PhysicalGrouper` 的“缺族补额”会让名义
`max_per_family=2` 的三元候选池实际选中 4 个 A 族特征。新增回归构造四个稳定 A 特征和
一个 B 特征，并故意缺少其余族；旧代码 RED 为：

```text
assert 4 == 2
```

现已删除补额扩容路径，并在模块/类文档中明确 `max_per_family` 是硬上限。该修复确保
pair-only 模式至多 1 个、triple 模式至多 2 个稳定候选，不会因缺少其它物理族而扩大搜索面。

### RED 2：默认缺 CIF Pipeline 有 traceback

第二个 subprocess 回归用临时 raw CSV 指向不存在的 CIF，要求：exit 2、清晰的
`ERROR: CIF preflight failed`、没有 traceback、且没有 `results/pipeline`。

旧行为：

```text
AssertionError: assert 1 == 2
```

原因是顶层只捕获全缺失特征错误，`FileNotFoundError` 从 Stage 0 冒泡为 Python traceback。

### GREEN 2：输入完整性失败是受控 CLI 错误

`run_pipeline.py` 顶层现在把 `FileNotFoundError` 与
`InsufficientFeatureDataError` 都打印为 `ERROR` 并以 exit 2 退出。输出目录仍在 Stage 0
成功后才创建，因此该修复没有扩大写入面。

## 最终验证

从 `automat-naconductor/` 执行：

```text
pytest -q                                      # 70 passed
python -m compileall -q .                      # exit 0
python run_pipeline.py --help                  # exit 0
python train.py --help                         # exit 0
python run_status.py --help                    # exit 0
python test_descriptors.py --help              # exit 0
python plot_run_results.py --help              # exit 0
git diff --check                               # exit 0
```

还在独立临时目录调用真实默认配置：

- Pipeline（未跳过特征化）检出 84 个缺失 CIF，exit 2、无 traceback、未创建
  `results/pipeline`；
- Pipeline `--skip-featurize` 检出入库特征表没有有效结构值，exit 2、未创建结果；
- Agent `train.py --descriptor-name a2_max_dist` 在写 `results/agent` 前检出相同 CIF 问题，
  exit 2、未创建 Agent 结果。

## 交付物与限制

详细逐项记录位于
`ARIS_Experiments/new_descriptors/automat-naconductor/修复记录_2026-08-03.md`，覆盖：

- charged Species 的 Na/阴离子/占位识别和 Wyckoff API；
- CIF strict preflight、路径解析、周期 Voronoi；
- inactive/alias registry、fold-local 预处理、CV skip、rank-aware controls、Lasso stability；
- 原始物理值组合、ratio/triple/CSV provenance、V1–V4；
- config 对齐、Composition+RF Agent 迁移、双轨冻结输入与 C9 隔离；
- 本数据集 NASICON/oxide、sulfide/sulfide 的统计共线性解释，以及“非因果、非普适物理等式”的边界。

当前 CIF 缺失依旧阻止真实研究运行；V1–V4 仍是探索性关联证据，尚未实现 nested outer-group
selection。没有创建 commit 或暂存任何文件。
