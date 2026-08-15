# PIPELINE_DEFERRED.md

统计管线封版文档。记录本轮（W4-2/W4-3/W1-1/报表层清理/阈值冻结）之后，
RESEARCH_REVIEW.md 24 项中未实现的项目、已完成的项目、以及已发生的能力回归。

---

## 6a 延后清单

以下项目在 RESEARCH_REVIEW.md 24 项中本轮未实现。

| 项目号 | 一句话内容 | 延后理由（引用源表数据依赖列原文） | 解冻条件 |
|---|---|---|---|
| W0-1 | 配置单一真值源 + seed 派生 + y 掩码契约统一 | 数据依赖列："无"——属配置体例改动，非退化值问题 | 待确认当前 seed 传播链路后实施 |
| W1-2 | 控制基在实际分析行子集上重算 | 数据依赖列："无"——depends on W1-1（已完成），属算法精度改进 | 可在下一轮实施 |
| W1-3 | 残差方差占比作为一等列 | 数据依赖列："无"——属新增列，非退化值问题 | 可在下一轮实施 |
| W1-4 | 族代表改为 y-无关的族内 medoid | 数据依赖列："无"——属算法改动 | 可在下一轮实施 |
| W2-1 | Stage 1-3 重构为纯函数 | 数据依赖列："无"——**blocking for W3-1 / W3-2 / W5-1**，工作量 L | 整个路线图的关键路径，需专项投入 |
| W3-1 | 外层体系内联合置换 maxT | 数据依赖列："无"——depends on W2-1 | 待 W2-1 完成 |
| W3-2 | 影子列替换高斯噪声列 | 数据依赖列："无"——depends on W2-1 | 待 W2-1 完成 |
| W3-3 | Stage 1 用固定基数替代阈值 | 数据依赖列："**取值须数据前冻结**"——取值已冻结（top_k=10），实现待做 | 可在下一轮实施（取值已冻结） |
| W3-4 | V1 共享置换 + p 值定义修正 | 数据依赖列："无"——属算法改动 | 可在下一轮实施 |
| W3-5 | 组合增量有效性闸门 | 数据依赖列："无"——属算法改动 | 可在下一轮实施 |
| W3-6 | random-k / bottom-k 对照验证集 | 数据依赖列："无"——属新增功能 | 可在下一轮实施 |
| W4-1 | V2 改为双侧折外残差化（DML 正交得分） | 数据依赖列："无"——属算法改动 | 可在下一轮实施 |
| W4-4 | V4 自举主指标 + BCa | 数据依赖列："无"——depends on W1-1（已完成） | 可在下一轮实施 |
| W4-5 | CV 层瘦身 | 数据依赖列："可行性判断需要数据"——LOSO 之外是否还需 anion 分组 CV 取决于阴离子类计数 | 待数据集到位后判断可行性 |
| W4-6 | 稳定性选择加 λ 路径 + q 记录 + E[V] 上界 | 数据依赖列："网格可自动"——λ 路径范围需要数据（可用 lasso_path 自动网格规避） | 可在下一轮实施（网格可自动） |
| W5-1 | 外层嵌套 LOSO | 数据依赖列："无"——depends on W2-1 | 待 W2-1 完成 |
| W5-2 | 相关簇分组选择 | 数据依赖列："**阈值须数据前冻结**"——阈值已冻结（cluster_threshold=0.8），实现待做 | 可在下一轮实施（阈值已冻结） |

延后共计 **17** 项。

### W0-1 已证实的死键

以下 `run_info.yaml` 中的键不被任何代码读取（实际生效来源为 CLI argparse）：

| 键 | run_info.yaml 位置 | 实际生效来源 | 判据 |
|---|---|---|---|
| `evaluation.model.alpha` | `evaluation.model.alpha: 1.0` | CLI `--alpha`（`run_pipeline.py` argparse，默认 1.0） | `DeconfoundAnalyzer(alpha=...)` 与 `CombinationValidator(alpha=...)` 的实参来自 `args.alpha`，不读取 `run_info.yaml` |
| `selection_alpha` | `stability_selection.selection_alpha: 0.05` | CLI `--selection-alpha`（`run_pipeline.py` argparse，默认 0.05） | grep 全仓无代码以 `config_get` 或等价方式读取 `run_info.yaml` 的 `selection_alpha`；`stability.py` 的 `self.alpha` 来自构造函数参数，`run_pipeline.py` 传 `args.selection_alpha` |

这是路线图 W0-1（配置单一真值源）"改配置不改行为"的第一个已证实实例。

---

## 6b 已完成清单

| 项目号 | 内容 | 完成轮次 | commit |
|---|---|---|---|
| W0-2 | 一次性删除清单 | W0-2 + W0-4 系列 | fc68317, f4031ee, 5f4cd0f |
| W0-3 | 估计量命名与 schema 绑定 | W0-4 prep + close | 3c5e921, f4031ee, 5f4cd0f |
| W0-4 | 未执行的计算一律 NaN | W0-4 系列 | fc68317, f4031ee, 5f4cd0f |
| W1-1 | alpha=0 投影替代 Ridge 收缩 | 本轮 | ddcc5d7, 69667a3 |
| W1-5 | 秩顺序约定：改名 | W0-4 prep | 3c5e921 |
| W4-2 | V2 未见类别显式处理 | 本轮 | 88e35fd |
| W4-3 | V3 最小 n 闸门 + 小 n 精确置换 p + Fisher-z 合并 | 本轮 | aaddc48, 0971742 |

已完成共计 **7** 项。

---

## 6c 已发生的能力回归：W4-5 前提失效——管线中不存在 LOSO

W4-5 条目原文（RESEARCH_REVIEW.md 第 377-384 行）写："删 anion_stratified_cv 与 repeated_subsample；只保留 LOSO，改在折内残差化目标上计算，报折间离散度"。

实际状态：管线中不存在 LOSO。`cv_strategies.py` 从未进入版本控制（b65cd96 文件列表无此路径，`git log --diff-filter=D` 全库无该文件的删除记录）；LOSO 的移除若曾发生，发生在版本控制之前，无 commit 级证据；受控文件中亦不存在移除授权（J3 检索）。当前 V2（`_factor_spanning`）用按 system 分层的 `StratifiedKFold`（每折含全部体系），方向与跨体系外推正相反。

**结论**：管线现无任何跨体系外推证据。W4-5 的实际内容已从"瘦身"变为"恢复 LOSO"。这意味着 W4-5 从"可延后"升级为"恢复管线核心能力的必要修复"，应在下一轮优先处理。

---

## 6d noise_baseline 生产端未撤下

`above_noise_baseline` 已按 W0-2 删除（待 W3-2 完成后恢复），但 `noise_baseline` 仍被计算、写入 `stability_df.attrs`、并由 `noise_baseline_available` 标为可用，当前无任何消费者。

**现状记录**：
- `stability.py` 的 `StabilitySelector.run` 仍计算 `noise_baseline`（噪声列选中频率的 95 分位数）并写入 attrs
- `combination.py` 的 `CombinationValidator._noise_baseline` 是另一个不同估计量（体系内分量置换零分布），共用 "noise_baseline" 一名
- `above_noise_baseline` 在活代码中零出现（已在 W0-2 中删除）
- `noise_baseline` 不进入任何选择判据（`is_stable` 用 `freq > self.threshold`，不比较 `noise_baseline`）

**本轮不改**。待 W3-2（影子列替换高斯噪声列）完成时一并处理。

---

## 6e 管线内并存两套残差化

W1-1 将单描述符层的残差化从 `Ridge(alpha=1.0)` 收缩改为正交投影（显式截距列 + `np.linalg.lstsq`），但组合层 `_factor_spanning` 的折内残差化仍为 `Ridge(alpha=self.alpha)` 收缩，未随 W1-1 改动。

具体并存情况：
- **单描述符层** `rank_corr_of_linear_residuals`：正交投影（显式截距列 + lstsq，alpha=0 等价）
- **组合层折内残差** `_factor_spanning`：`Ridge(alpha=self.alpha)` 收缩（combination.py:811, 823），alpha=1.0
- `system_rho` / `all_rho` 走前者（`rank_corr_of_linear_residuals_rho`），折外残差走后者（`Ridge`），两者同处 V2 证据块

W1-1 条目原文的理由（"所有自称去混杂的数字都是有偏的，偏差方向一致有利于结论"）对折内 Ridge 同样成立——折内残差仍受收缩偏差影响，偏差方向一致指向"物理信号更强"。本轮未处理。

**解冻条件**：与 W4-1（V2 改双侧折外残差化 / DML 正交得分）一并处理。

---

## 6f 主检验自由度与 p 值口径缺陷（H5a，本轮新增，实现延后）

本节记录 G3 已确认但本轮不解冻、不修改管线代码的三条事实及其后果，预注册修复
口径（实现延后至解冻窗口）。

### 已确认事实三条

1. **主检验无置换**：`descriptors/deconfound.py:221`
   `rho, p_val = stats.spearmanr(res_x, res_y)` —— 主检验
   `rank_corr_of_linear_residuals`（deconfound.py:168-222）对残差直接调
   `scipy.stats.spearmanr` 取**渐近 p**（基于 t 分布，自由度 n−2），不做任何置换。
   对比：组合层 `_per_system`（combination.py:928-938）对小 n 走精确/蒙特卡洛置换，
   主检验与组合层口径不一致。

2. **样本量未按控制列数扣减**：`descriptors/deconfound.py:204` `n_samples = len(x)`
   —— 传入 spearmanr 的隐含 n 是**残差化前的** `n_samples`，未按实际进入设计矩阵
   的控制列数 `k_used`（drop_first 后）扣减。残差化消耗 k 个自由度，渐近 p 应以
   `n_effective = n − k_used − 1` 为准，当前实现系统性**反保守**（p 偏小）。

3. **singleton system 组残差恒 (0,0)**：G3(c) 已用合成算例确认——某 system 组只含
   1 个样本时，该行残差精确为 (0, 0)（被 controls 编码精确吸收）。本轮复核注记：
   在 `build_rank_aware_controls` 参考编码 + 多个 singleton 组并存的合成算例下，
   `_projection_residuals`（deconfound.py:134-166）整体会因 `z.shape[1]+1 >= n_samples`
   或秩亏触发 `controls_rank_deficient`/`rank_deficient` 退化返回 NaN；singleton 行
   贡献 (0,0) 的精确场景依赖 controls 编码与退化路径，由 G3(c) 锁定。
   后果：singleton 行抬 n 不抬信号，对 Spearman 还制造两端并列值。

### 后果陈述

- 残差化消耗 k 个自由度，用未扣 k 的 n 算渐近 p → p 系统性**偏小（反保守）**。
- singleton 行残差 (0,0)，对 Spearman 贡献零信号却抬 n，并制造两端并列值。
- 主检验无置换，无法提供小样本下的非渐近 p；与组合层置换口径不一致。

### 解冻条件

与 W4-1（V2 改双侧折外残差化 / DML 正交得分）、W4-3（per-system 置换口径）一并
处理；届时 p 值口径必须遵守 `FROZEN_THRESHOLDS.md` 修订记录中 H5b 冻结的 R1/R2/R3。

### 是否升格为必要修复：升格

升格理由参照 6c 的 W4-5 先例：6c 的 W4-5 因 LOSO 删除导致"恢复管线核心能力的必要
修复"被升格；本节主检验 p 值口径缺陷同样属于"统计推断有效性受损"——当前 p 偏小且
含 singleton 噪声，任何引用主检验 p 的结论都需在此修复后重估。故本节从"可延后"
升格为"统计有效性的必要修复"，仍归入解冻窗口统一处理（不解冻本轮）。
