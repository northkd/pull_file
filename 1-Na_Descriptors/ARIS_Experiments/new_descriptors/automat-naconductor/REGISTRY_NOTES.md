# REGISTRY_NOTES.md

## 两个描述符清单常量的差集

代码中存在两个描述符清单常量：

- `AVAILABLE_STRUCTURE_DESCRIPTORS`（41 条）：全部已实现的描述符，定义在 `descriptors/__init__.py:106`。
- `SEARCHABLE_STRUCTURE_DESCRIPTORS`（38 条）：从 AVAILABLE 中排除 `_INACTIVE_FOR_AUTOMATIC_SEARCH` 后的子集，定义在 `descriptors/__init__.py:232`。

### 差集

`AVAILABLE - SEARCHABLE`（3 条，即被排除的）：
- `max_bond_length`：`a2_max_dist` 的兼容性别名（`alias_of`）
- `bottleneck_anisotropy`：实现永久不可用
- `bvse_barrier_estimate`：无 BVSE 后端时永久不可用

`SEARCHABLE - AVAILABLE`：空集（SEARCHABLE 是 AVAILABLE 的真子集）。

### 差异原因

`_INACTIVE_FOR_AUTOMATIC_SEARCH`（`descriptors/__init__.py:213-217`）显式排除了以上 3 个描述符，使其不进入自动搜索管线（Stage 1-3），但仍在 `AVAILABLE_STRUCTURE_DESCRIPTORS` 中保留以供 Agent 轨道和兼容性引用。

### 闸门处置

注册表闸门（`descriptors/registry.py`）对 `AVAILABLE_STRUCTURE_DESCRIPTORS` 的 41 条做双向覆盖（并集 = AVAILABLE，因 SEARCHABLE ⊂ AVAILABLE）。每条新增字段 `in_searchable` 标记是否在 SEARCHABLE 中，机械可填，不算 TODO。
