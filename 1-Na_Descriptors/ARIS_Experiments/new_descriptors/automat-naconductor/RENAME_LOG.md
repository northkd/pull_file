# 主指标改名日志

**改动日期**: 2026-08-10
**改动原因**: 旧名 `deconfounded_spearman` / `partial_spearman` 暗示该量是文献意义上的 partial Spearman 或满足去混杂（deconfounded）的可识别性条件，实际并非如此。保留实现，改为诚实命名。

## 1. 列名对照

| 旧列名 | 新列名 | 出现位置 |
|---|---|---|
| `deconfounded_spearman` | `rank_corr_of_linear_residuals` | CSV 列头、DataFrame 列名、`DECONFOUND_RESULT_COLUMNS` 常量、`BASELINE_RESULT_COLUMNS` 常量、`PHYSICAL_GROUP_RESULT_COLUMNS` 常量、`REQUIRED_AGENT_RESULT_COLUMNS` 常量、`REQUIRED_AGENT_PLOT_COLUMNS` 常量、报表模板、run_info.yaml `primary_metric` 字段 |
| `combined_deconf_spearman` | `combined_rank_corr_of_linear_residuals` | CSV 列头、DataFrame 列名、`COMBINATION_RESULT_COLUMNS` 常量、`FULL_VALIDATION_RESULT_COLUMNS` 常量、报表模板 |
| `best_abs_deconfounded_spearman` | `best_abs_rank_corr_of_linear_residuals` | `plot_run_results.py` 派生列名 |
| `best_deconfounded_spearman` | `best_rank_corr_of_linear_residuals` | `run_status.py` 打印输出 |

## 2. 方法名对照

| 旧方法名 | 新方法名 | 所在类 | 调用点 |
|---|---|---|---|
| `DeconfoundAnalyzer.partial_spearman` | `DeconfoundAnalyzer.rank_corr_of_linear_residuals` | `DeconfoundAnalyzer` | `deconfound.py` 内部 `analyze_all` 方法；原 `deconfounded_spearman` 便捷方法 |
| `DeconfoundAnalyzer.deconfounded_spearman` | `DeconfoundAnalyzer.rank_corr_of_linear_residuals_rho` | `DeconfoundAnalyzer` | `combination.py` 第 304、676、679 行 |

**类名 `DeconfoundAnalyzer` 保留不改。**

## 3. 改动文件清单（代码与配置）

| 文件 | 改动内容 |
|---|---|
| `descriptors/deconfound.py` | 函数名 `partial_spearman` → `rank_corr_of_linear_residuals`；方法名 `deconfounded_spearman` → `rank_corr_of_linear_residuals_rho`；列名常量；docstring 更新 |
| `descriptors/combination.py` | 列名 `combined_deconf_spearman` → `combined_rank_corr_of_linear_residuals`；3 处方法调用点同步 |
| `descriptors/stability.py` | 列名引用与 docstring 同步 |
| `run_pipeline.py` | 11 处列名引用同步 |
| `run_info.yaml` | 3 处列名引用同步；新增 `estimand` 段 |
| `automat_utils.py` | 3 处列名引用同步 |
| `plot_run_results.py` | 列名与派生列名同步 |
| `run_status.py` | 列名引用与校验信息同步 |
| `program.md` | 列名引用与诚实命名说明 |
| `README.md` | 列名引用同步 |
| `tests/test_combinations.py` | 5 处列名引用同步 |
| `tests/test_evaluation_core.py` | 8 处列名引用同步 |
| `tests/test_pipeline_integration.py` | 1 处列名引用同步 |
| `tests/test_agent_track.py` | 8 处列名引用同步 |

## 4. 未改动的文件（历史产物，不得事后编辑）

以下文件在本次改名中**未被修改**，保留其原始历史内容：

- `RESEARCH_REVIEW.md` — 审稿记录，引用旧名 `partial_spearman`、`deconfounded_spearman`、`combined_deconf_spearman`
- `RESEARCH_REVIEW.json` — 同上
- `修复记录_2026-08-03.md` — 修复记录，引用旧名 `deconfounded_spearman`

## 5. 计算逻辑

**未做任何改动。** 残差化方法（Ridge）、alpha（1.0）、秩变换顺序（先残差化再 Spearman）全部保持原样。

## 6. estimand 声明

`run_info.yaml` 新增 `estimand` 段，明确声明：

- 本量不是文献意义上的 partial Spearman（标准做法先秩变换再偏出，本实现顺序相反）
- 本量对 x 的单调变换不不变（线性残差化不保秩）
- `decision_date: "2026-08-10"`
- `decision_precedes_dataset_finalization: true`
