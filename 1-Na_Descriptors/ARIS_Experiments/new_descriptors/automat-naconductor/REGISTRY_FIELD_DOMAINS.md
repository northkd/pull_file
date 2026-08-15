# REGISTRY_FIELD_DOMAINS.md

本文件逐字冻结 `descriptor_registry.yaml` 中六个剩余字段的值域。
闸门校验 6（`descriptors/registry.py:assert_registry_complete`）对这些字段做条件必填校验。
校验 6 对仍为 `TODO` 的字段跳过（`TODO` 由校验 3 负责）。

## estimand_math

- **类型**：单行表达式
- **约束**：禁止自然语言。非空、不含 `TODO`。表达式中出现的每个标识符必须属于：
  - 已注册 helper 名（`_` 开头的函数名，由 `compute_helper_closures` 派生）
  - `_base.py` 模块级常量名
  - 冻结白名单：`mean, std, sum, min, max, abs, sqrt, exp, ln, n, i, j, k`
- **校验实现**：复用 `shared/symbol_match.py`，不得另写正则

## name_matches_estimand

- **类型**：枚举
- **值域**：`yes` / `no` / `partial`
- **条件约束**：
  - `no` 或 `partial` ⇒ `name_mismatch_note` 非空
  - `yes` ⇒ `name_mismatch_note` 必须为空字符串（禁止两头下注）

## name_mismatch_note

- **类型**：自由文本
- **约束**：由 `name_matches_estimand` 的值决定（见上条）

## known_invariance_defects

- **类型**：列表
- **每项格式**：`<transform>:<verdict>`
  - `transform` 取 F1/G1 的 7 个之一：`site_permutation` / `origin_shift` / `lattice_rotation` / `supercell` / `isotropic_scale` / `occupancy_split` / `geometry_jitter`
  - `verdict` 取 G1 重做后的词表之一：`invariant` / `numerical_noise` / `changed` / `collapsed_to_zero` / `nan_both` / `nan_introduced` / `not_applicable`
    （G1 重做取消了 `scaled_<k>` 枚举与 `dimension_mismatch` verdict；`dimension_declaration_conflict` 移出 verdict 为 CSV 独立列）
  - **H2 引入两个例外**（不再走普通 transform:verdict 词表，但在校验 6 单独枚举放行）：
    - `geometry_jitter:no_geometry_response` —— geometry_jitter 变换下 verdict ∈ {invariant, numerical_noise}（原子位置被扰动而返回值不动，说明该量不依赖几何）；verdict 仍属 `geometry_jitter` 变换但码名换为 `no_geometry_response`
    - `all_transforms:permanently_nan` —— 描述符在全部 7 变换 × 5 结构上恒为 nan_both（无条件返回 NaN）；transform 槽为 `all_transforms`，verdict 槽为 `permanently_nan`
  - **K6 新增三个码**：
    - `supercell:extensive_but_invariant` —— extensivity=extensive 但 supercell 变换下 ratio≈1（广延量不随超胞增长，漏报侧）
    - `supercell:undetermined_scaling` —— extensivity=undetermined 时 supercell 变换的默认码
    - `isotropic_scale:dimension_declaration_conflict` —— isotropic_scale 变换下反推幂次 k 与声明 dimension 对应幂次 k_decl 不符（|k−k_decl|>1e-6）
  - **K6 dimension → 幂次映射表**（用于 isotropic_scale 规则）：
    - dimensionless→0, length→1, area→2, volume→3, count→0, number_density→−3, angle→0, energy→0, electronegativity→0, charge→0, electron_count→0, categorical_index→0
- **聚合规则（K6 更新，四类分派）**：
  - **类 1: site_permutation / origin_shift / lattice_rotation / occupancy_split**（原规则不动）：`changed` / `collapsed_to_zero` / `nan_introduced` 计入缺陷；其余不计入
  - **类 2: geometry_jitter**（H2a 不动）：`invariant` / `numerical_noise` → `no_geometry_response`；`changed` 不计入；`collapsed_to_zero` / `nan_introduced` 计入
  - **类 3: supercell**（K6 新增，按 extensivity 分派）：
    - extensive: ratio≈n(=2)→干净; ratio≈1→`extensive_but_invariant`; 其他→`changed`
    - intensive: ratio≈1→干净; 其他→`changed`
    - undetermined: →`undetermined_scaling`
  - **类 4: isotropic_scale**（K6 新增）：s=1.05, k=log(ratio)/log(s); |k−k_decl|≤1e-6→干净; 否则→`dimension_declaration_conflict`
  - **H2b 永久 NaN**：若某描述符全部行 verdict == `nan_both`（7×5=35 行），聚合结果为 `["all_transforms:permanently_nan"]`，不得是 `["none_found"]`
- **无缺陷时**：`["none_found"]`
- **生成方式**：由 `scripts/fill_invariance_field.py` 机器生成，禁止手工编辑
- **闸门校验 6 的 status 联动（H2c）**：`status=confirmed_match` 时，`known_invariance_defects` 既不能含 `permanently_nan` 也不能含 `no_geometry_response`（二者均表明描述符实现有结构性缺陷，与"已确认匹配"冲突）

## extensivity（K6 新增，机器派生）

- **类型**：枚举
- **值域**：`extensive` / `intensive` / `undetermined`
- **派生规则**：由 supercell 变换的实测 ratio 与超胞倍数 n=2 决定：
  - |ratio−n|/n ≤ 1e-6 → `extensive`
  - |ratio−1| ≤ 1e-6 → `intensive`
  - 其他（含 NaN） → `undetermined`
- **生成方式**：由 `scripts/fill_extensivity_field.py` 机器生成，纳入 `scripts/registry_refresh.py` 一键重算，禁止手工编辑
- **不计入 TODO 统计**（与 known_invariance_defects 同类）
- **闸门校验 9**：extensivity 必须等于探针重算值（与校验 7 同型）

## parameter_provenance

- **类型**：列表
- **每项前缀**（四选一）：
  - `literature:<引用>`
  - `inherited:<file>:<line>`
  - `no_provenance_found(searched:...)`
  - `n_a`
- **条件约束**：条目数 ≥ 该描述符 `impl_literals` 中非平凡字面量个数
  - 平凡集冻结为：`{0, 1, 2, -1, 0.0, 1.0, 2.0}`
  - 即 `impl_literals` 中的值如果属于平凡集，不计入非平凡字面量个数
- **`no_provenance_found`** 必须带非空 `searched:` 后缀

## status

- **类型**：枚举
- **值域**：`confirmed_match` / `rename_required` / `redefine_required` / `retire` / `unavailable_implementation`
- **条件约束**：`status=confirmed_match` ⇒
  - `name_matches_estimand=yes`
  - `known_invariance_defects==["none_found"]`
  - `parameter_provenance` 中无 `no_provenance_found` 条目

## impl_return_exprs（机器派生）

- **类型**：列表
- **口径**：`ast.Return` 节点的 `get_source_segment`，按源码行号升序
- **格式**：每项 `"源码原文 (L行号)"`
- **生成方式**：`scripts/fill_impl_fields.py` 机器生成，禁止手工编辑
- **校验**：闸门校验 8 强制等于重算值

## impl_literals（机器派生）

- **类型**：列表
- **口径**：全部数值 `ast.Constant`（int/float，排除 bool），按行号升序，含平凡值
- **格式**：每项 `"数值 (L行号)"`
- **生成方式**：`scripts/fill_impl_fields.py` 机器生成，禁止手工编辑
- **校验**：闸门校验 8 强制等于重算值

## impl_guards（机器派生）

- **类型**：列表
- **口径**：全部 `ast.If` 的条件源码（`get_source_segment(node.test)`），按行号升序
- **格式**：每项 `"条件源码 (L行号)"`
- **生成方式**：`scripts/fill_impl_fields.py` 机器生成，禁止手工编辑
- **校验**：闸门校验 8 强制等于重算值

## impl_nan_paths（显式人工字段）

- **类型**：字符串
- **口径**：不可机器派生（涉及跨函数语义，如 "_safe_mean 在空输入下返回 NaN"）
- **来源**：从原 `impl_guards_and_nan_paths` 字段中提取 `nan_paths:` 部分
- **校验**：闸门中豁免机器比对（不参与校验 8）

## 机器字段漂移收口规则（G4）

`shared_intermediates` / `impl_return_exprs` / `impl_literals` / `impl_guards` /
`known_invariance_defects` 五个字段由机器从 `descriptors/` 源码派生，任何改变
源码行号或调用结构的改动都会让 registry 陈旧（已于 F5/G0d 各触发一次）。

**必守规则**：任何修改 `descriptors/` 下源码的提交，必须在**同一个提交内**跑
`python scripts/registry_refresh.py` 并把 YAML 变更一并纳入该提交；禁止事后
`--amend` 到别的提交上。

校验 5（shared_intermediates）、校验 7（known_invariance_defects）、
校验 8（impl_*）在 registry 陈旧时必然失败，作为漂移的自动防线。

## impl_return_exprs / impl_literals 分类口径（G0a）

对机器抽取的 return 表达式与数值字面量，与 YAML 当前值做两类判定（见 `scripts/impl_facts_classify.py`）：

- **格式类**：归一化引号（单→双）并排序后表达式集合相同。差异仅来自行号漂移、AST 遍历顺序、引号风格、空白。
- **实质类**：表达式本身不同（YAML 缺/多一条），或 YAML 记录的字面量在代码中不存在（如 F5 后 `space_group_number` 的 `0.01` symprec 字面量已改为配置读取而消失）。

格式类不构成字段内容错误，不建议回填；实质类需人工裁定是否由 `scripts/fill_impl_fields.py` 重新生成或标记为人工维护。

## impl_* 分类可复现性（H3）

`scripts/impl_facts_classify.py` 支持 `--yaml-from-commit <commit>`，用
`git show <commit>:descriptor_registry.yaml` 取 YAML 快照（只读，不落盘到工作区），
对任意历史 commit 的 impl_* 值重跑格式类/实质类分类：

```bash
python scripts/impl_facts_classify.py --yaml-from-commit <commit>
```

**H3 实测（2026-08-14）**：~~受版本控制的历史中**不存在**能复现 F0a 报告
（return_exprs 格式类 34 / 实质类 1；literals 格式类 21 / 实质类 3）的"手工值
impl_*"状态。~~

> **已证伪（K3a, 2026-08-15）**：H3 原结论错误，根因是 Windows GBK 编码将
> "不一致 [格式类]"截断显示为"一致"。加 `PYTHONUTF8=1` 后在 03d5225/fde0550
> 实测 return_exprs 22/1、literals 21/3，其中 **literals 的 21/3 与 F0a 完全一致**
> （含三条描述符名：charge_balance_deviation, space_group_number, wyckoff_diversity）；
> return_exprs 22 与 F0a 的 34 差 12，根因为 `--yaml-from-commit` 只快照 YAML、
> 源码侧从工作区读取（见 K4）。

既有 `git log` 证据链：

- `ca59547` 及更早（`git show ca59547:descriptor_registry.yaml`）：`impl_return_exprs`
  字段在 YAML 中出现 **0 次**（`rest are TODO`，字段根本不存在）。
- `03d5225` 起：`impl_return_exprs` 出现 41 次，全部为**机器生成值**。
  ~~（对工作区源码跑 `impl_facts_classify.py --yaml-from-commit 03d5225` 得全一致 0/0）。~~
  > **更正（K3a）**：实际得 return_exprs 22/1、literals 21/3（需 `PYTHONUTF8=1`）。

~~即 impl_* 在版本控制内只有"不存在（TODO）/ 机器值"两种状态，从未以"手工值"
被版本控制。F0a 报告（`34/1` 与 `21/3`）对应的是版本控制开始前、未被 git 追踪
的开发状态，**无法在版本控制内复现**；H3 验证了这一点，而非伪造一个 commit 填充。
若日后需要恢复该结论的可复现位点，需先重建一份"手工值 impl_*"的 YAML 快照
再传入 `--yaml-from-commit` 对应的临时树（不属于 HEAD 数据）。
