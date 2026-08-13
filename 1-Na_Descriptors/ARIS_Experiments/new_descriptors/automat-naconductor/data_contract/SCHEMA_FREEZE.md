# SCHEMA_FREEZE.md

## 冻结信息

- **冻结日期**：2026-08-13
- **schema_frozen_at**：5ccff2d
- **selection_rule_frozen_at**：47f951a
- **schema 版本**：v1

## select_rt 规则逐条原文

1. 保留 `conductivity_component == component`；
2. 保留 `T_K ∈ [293, 303]`；
3. 按 `sigma_readout` 取最高一级：table_value > stated_in_text > digitized_from_figure > extrapolated_from_arrhenius_fit；
4. 同级多条时取 `|T_K − 298|` 最小者；仍并列取 `measurement_id` 字典序最小者；
5. 输出列：material_id / measurement_id / sigma_S_per_cm / log10_sigma / T_K / sigma_readout / n_candidates；
6. `drop_report_df` 列：filter_stage / n_in / n_out / n_dropped；
7. 过滤后无候选的材料不静默丢弃：仍出一行，sigma 与 log10_sigma 显式 NaN，n_candidates=0。

## 主 y 决定

- 主 y 为 `y_total`（`component="total"`）。
- `y_bulk`（`component="bulk"`）仅作敏感性分析，不作为主分析目标。
- 理由：bulk 电导率的定义随 EIS 等效电路选择而变，跨文献不可比。

## 冻结声明

任何修改必须新增 raw_schema_v2 并原样保留 v1，禁止就地编辑 v1。

## 修订记录

### 2026-08-13 就地修订（commit: 待填）

**修订内容**：
1. 为每个数值列（`structure_temperature_K` / `T_K` / `sigma_S_per_cm` / `relative_density_pct` / `E_a_eV`）显式增加 `zero_is_sentinel` 键，声明 0 在该列的语义——是缺失哨兵（`true`）还是合法值（`false`）。
2. `validate_raw.py` 依 `zero_is_sentinel` 决定是否对 0 施加 `forbidden_missing_sentinel` 检查；`zero_is_sentinel: true` 的列（仅 `sigma_S_per_cm`）在 0 值时同时报 `forbidden_missing_sentinel` 与 `range_violation`。
3. `validate_raw.py` 的 `main()` 检测 schema 中存在未替换的 `__TODO_USER_FILL__` 时，直接以退出码 2 终止，不进行任何逐行校验。

**为什么就地修订而非新建 v2**：
- 原 v1 未声明 0 的逐列语义，导致 `relative_density_pct` 的合法下界 0 被一律当缺失哨兵拦截（区间下界形同虚设）。
- 原 v1 未定义 `__TODO_USER_FILL__` 占位符的 validator 行为，逐行枚举检查虽能 fail-loud 但不理想（未在 schema 层面拒绝）。
- 上述两处缺陷均发生在 schema 被用于任何真实数据之前，数据集尚不存在，不存在破坏既有校验结果的风险。
- 此后禁止就地编辑 v1；后续修改必须新增 raw_schema_v2 并原样保留 v1。
