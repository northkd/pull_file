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

## CIF 落地约定

- CIF 放置于 `data/cif/`；
- `materials.csv` 的 `cif_relpath` 一律为相对仓库根的路径（如 `data/cif/1.cif`）；
- `cif_sha256` 由脚本计算（`data_contract/ingest_cif.py`），不手填；
- `material_id` 按 CIF 文件名 UTF-8 字节序排序依次分配 `MAT-0001`…，编号不可复用；
- 编号清单文件：`data_contract/material_id_manifest.csv`，
  列为 `material_id, cif_filename, cif_sha256`；
- **该文件是状态文件，不是空白模板**：记录已分配的真实编号，不可重生成、
  不可就地编辑、丢失即编号不可恢复。放在 `data_contract/` 下而非 `templates/`，
  避免被当作空白模板误清；
- 只追加不重排：若清单文件已存在，已有 CIF 保持原号，新增 CIF 从最大号 +1 继续；
- 完整性检查：若清单中某 `cif_filename` 的 `cif_sha256` 与当前文件不符，
  `ingest_cif.py` 以退出码 2 拒绝继续（不得保号、不得静默重算）；
  若清单中的 `cif_filename` 在 `data/cif/` 已不存在，不抛错但 stdout 列出。

## 待用户填定

`raw_schema_v1.yaml` 中 `system` 与 `system_coarse` 两列的 `allowed` 值域仍为
`__TODO_USER_FILL__`（体系划分待用户填定）。填定前 `validate_raw.py` 检测到
占位符时以退出码 2 拒绝校验（已实现）。

填定属 schema v1 的最后一处修订，之后一律走 v2。

## 不可逆约束：值域冻结早于数据落地（K3c 新增）

system 与 system_coarse 的值域必须在任何数据落地之前冻结。理由：值域、schema、
壳层敏感性设定、p 值自由度口径这四项若晚于第一批数据确定，预注册即失效，
且此失效不可逆。本约束不因"需要看数据才知道有哪些体系"而放宽——
未见体系的处置走 exit 2 强 fail-loud 加预注册修订程序（新值走 v2，
并在 SCHEMA_FREEZE 记录新值、影响行数、k_used 是否变化、需重算哪些冻结项）。
