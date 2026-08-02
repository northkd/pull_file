# automat-naconductor

Na 离子固态导体局域结构描述符搜索框架。
基于 automat 改造，核心变化：CIF 输入 → 结构描述符，去混杂 Spearman 为主指标。

## 核心契约

`automat-naconductor` 搜索 Na 离子固态导体的局域结构描述符组合，
使其与 log₁₀(σ/S·cm⁻¹) 的去混杂 Spearman 秩相关性最大化。

- **输入来源**：CIF 结构文件（不是化学式）。描述符从 pymatgen 解析的
  `Structure` 对象计算，而非 `Composition`。
- **目标变量**：`log_sigma` = log₁₀(σ/S·cm⁻¹)，已在数据集中预计算。
- **主要评价指标**：`deconfounded_spearman` —— 控制 `system` 和 `anion_type`
  混杂因素后的偏 Spearman 秩相关系数。不再以 `cv_mae` 为主要判据。
- **模型固定**：使用 `run_info.yaml` 中声明的模型和参数，中途不调参。
- **描述符选择**：结合去混杂相关性和稳定性选择（stability selection），
  仅有在 ≥60% 自举样本中被选中的描述符才进入最终组合。
- **物理约束**：描述符必须满足物理可解释性——
  - 与离子尺寸的单调性一致
  - 与空位浓度正相关
  - 禁止使用 `log`、`√`、`power` 运算符构造新特征
- **`run_info.yaml` 不可变**：除非用户明确指示修改，否则视为常量。

## 必读文件

启动或恢复运行前，必须阅读：

- `run_info.yaml` — 任务定义、数据路径、列名、CV 策略、去混杂配置、
  稳定性选择参数、组合搜索策略、评价指标和输出路径。
- `train.py` — 训练-交叉验证评估器。
- `run_status.py` — 停止/继续判断器。
- `automat_utils.py` — 数据加载、特征化、模型和指标辅助函数。
- `descriptors/featurizer.py` — 结构描述符计算入口。
- `descriptors/cv_strategies.py` — 交叉验证策略实现。
- `descriptors/deconfound.py` — 去混杂计算实现。
- `descriptors/idea.md` — 当前描述符方案。
- `descriptors/idea.py` — 当前描述符实现。
- `descriptors/__init__.py` — 注册表。

## 数据格式

输入数据为 `data/naconductor_raw.csv`，包含以下列：

| 列名 | 含义 |
|------|------|
| `material_id` | 材料编号，如 `MAT-001` |
| `cif_path` | CIF 文件相对路径（相对于 CSV 文件位置） |
| `formula` | pymatgen 约化式 |
| `space_group` | 空间群 |
| `system` | 体系分类：`NASICON` / `sulfide` / `halide` |
| `anion_type` | 阴离子类型：`oxide` / `sulfide` / `chloride` / `iodide` 等 |
| `log_sigma` | log₁₀(σ/S·cm⁻¹)，目标变量 |

**不做 train/val/test 预拆分**——使用 `run_info.yaml` 中声明的多种 CV 策略
（分层 K 折、留一体系、重复子采样）评估稳健性。

## 设置流程

1. 读取 `run_info.yaml`。
2. 验证必要输入：
   - `run_info.yaml` 存在。
   - `task.name` 和 `task.description` 非空。
   - `data.raw_file` 指向存在的 CSV 文件。
   - `data.target_column` 和 `data.structure_column` 存在于 CSV 中。
   - `cif_path` 列指向的 CIF 文件可解析。
   - CV 策略、去混杂配置、稳定性选择参数和模型配置完整。
3. 创建 `results.tsv` 和 `ideas.tsv`（如缺失）。
4. 从空白 `descriptors/idea.py` 开始。`descriptors/idea.md` 可包含
   通用模板，指导 agent 从 `run_info.yaml` 创建基线。
5. 在 `descriptors/idea.md` 中文档化基线方案，再实现于
   `descriptors/idea.py`。
6. 在 `descriptors/__init__.py` 中注册基线。
7. 运行烟雾测试，验证导入和注册无错。
8. 运行基线实验，记录为根节点。

## 本地日志

`results.tsv` 和 `ideas.tsv` 为必要本地产物，不提交。

`results.tsv` 表头：

```text
commit	deconfounded_spearman	cv_spearman	cv_mae	cv_rmse	stability_score	status	descriptor_name	description
```

`ideas.tsv` 表头：

```text
commit	parent_commit	root_commit	descriptor_name	change_kind	risk_level
```

`results.tsv` 各列：

1. `commit`：实验提交的短 git hash。
2. `deconfounded_spearman`：去混杂 Spearman rho，或 `nan`。
3. `cv_spearman`：CV 平均 Spearman rho。
4. `cv_mae`：CV 平均 MAE。
5. `cv_rmse`：CV 平均 RMSE。
6. `stability_score`：稳定性选择得分（0~1），或 `nan`。
7. `status`：`keep`、`discard` 或 `crash`。
8. `descriptor_name`：描述符唯一键。
9. `description`：变更简述。

`ideas.tsv` 各列与原始 automat 相同。

## 描述符设计规则

在修改描述符代码前，必须在 `descriptors/idea.md` 中写出方案。

`descriptors/idea.md` 必须包含以下节：

- **问题知识**：问题摘要，融合前序迭代的发现。
- **科学洞察**：与 Na 离子迁移相关的物理化学考量，
  以及它如何塑造当前描述符。
- **实现策略**：基于 ML 直觉和物理洞察的描述符计划。
  描述须足够清晰，仅凭此文件即可实现。不要包含代码。
- **依赖**：实现所需的 Python 库或文件。

描述符必须：

- 不使用验证标签或外部任务数据
- 从 CIF 结构（`pymatgen.core.Structure`）计算，而非仅化学式
- 为每个结构返回一维有限数值向量
- 有物理或化学论证支持
- **禁止使用** `log`、`sqrt`、`power` 运算符构造新特征
  （目标已是 log 变换；对描述符再取 log 等于双重变换，物理意义不清）
- 满足物理约束（如适用）：
  - 描述符与离子尺寸的关系应与物理直觉一致
  - 与空位浓度应呈正相关

## 评价指标

**主指标**：`deconfounded_spearman` —— 控制 `system` 和 `anion_type` 后的
偏 Spearman 秩相关系数。

为什么用 Spearman 而非 Pearson？
- 小样本（84 个）下秩相关更稳健
- 电导率跨 10 个数量级，Pearson 受极端值影响大

为什么需要去混杂？
- `system`（NASICON/sulfide/halide）是强混杂变量——
  它同时影响描述符取值范围和电导率水平
- 不控制的"高相关"可能是混杂效应，不是因果关系

辅助指标：
- `cv_spearman`：交叉验证 Spearman rho
- `cv_mae`：交叉验证 MAE
- `cv_rmse`：交叉验证 RMSE
- `stability_score`：稳定性选择得分

## 保留/丢弃策略

根基线默认保留。

此后，描述符仅当 `deconfounded_spearman` 严格优于当前最佳时保留。
平局和更差结果丢弃。

- 保留：记录 `status=keep`，成为新最佳
- 丢弃：记录 `status=discard`，回退到前一最佳提交
- 崩溃：修复明显实现错误后重试；若方案根本不可行，
  记录 `status=crash`，计入迭代

稳定性选择结果**不覆盖**主指标判断，但作为辅助参考：
稳定性得分 < 阈值的描述符即使主指标改善也应标注风险。

### 新颖性要求

与原始 automat 相同：不运行与已有描述符功能等价的迭代。
若新方案与先前被丢弃的方案相似，必须在 `descriptors/idea.md` 中
明确解释科学或算法上的区别。

### 简洁性准则

小改进不值得引入不必要复杂性。移除描述符若不降性能，是强结果。
组合中描述符数量上限见 `run_info.yaml` 的 `combination.max_descriptors`。

## 停止策略

每轮迭代结束时运行：

```bash
python run_status.py
```

末行为 `CONTINUE` 则继续，`STOP` 则停止。

## 实验循环

重复直到 `run_status.py` 输出 `STOP`：

1. 确认当前分支、最佳提交、最佳 `deconfounded_spearman`、
   根提交和本地 TSV 状态。
2. 从任务描述和前序结果推理下一个描述符方案。
3. 更新 `descriptors/idea.md`。
4. 在 `descriptors/idea.py` 中实现新描述符。
5. 在 `descriptors/__init__.py` 中注册新描述符键名。
6. 确保选定的描述符键名是 `train.py` 将评估的。
7. 提交实验。
8. 解析短 commit hash，追加 `ideas.tsv` 行。
9. 运行训练-CV。
10. 若崩溃，决定修复重试还是记录 crash。
11. 比较 `deconfounded_spearman` 与当前最佳（严格改善）。
12. 追加 `results.tsv` 行。
13. 保留改进的提交，否则回退到前一最佳。
14. 运行 `run_status.py`。

## 执行纪律

与原始 automat 相同：每轮迭代手动顺序执行，不使用自动化循环。
每个描述符方案必须从当前状态重新推理，不从模板批量生成。
