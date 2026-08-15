"""描述符注册表加载与闸门校验。

提供 load_registry 和 assert_registry_complete 两个函数。
assert_registry_complete 实现六条校验：
1. 双向覆盖：代码中每个注册描述符必须在 registry 有条目，反之亦然；
2. 符号可解析：每条的 implementation_symbol 必须通过定义位置整词匹配；
3. 无 TODO 残留：任一字段值为字面量 TODO 时抛错；
4. in_searchable 派生比对：YAML 的 in_searchable 必须与代码中
   STRUCTURE_DESCRIPTOR_METADATA[name]["active_for_search"] 一致；
5. shared_intermediates 传递闭包比对：YAML 的 shared_intermediates
   必须等于 compute_helper_closures 的 AST 重算值；
6. 字段值域条件必填：estimand_math / name_matches_estimand /
   name_mismatch_note / known_invariance_defects / parameter_provenance /
   status 六个字段的值域与条件约束（对 TODO 跳过，见 REGISTRY_FIELD_DOMAINS.md）；
7. known_invariance_defects 探针重算比对：YAML 的 known_invariance_defects
   必须等于 fill_invariance_field.compute_defects_from_report 的重算值。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml

# 复用 shared/symbol_match.py 中的符号定义位置匹配器
from shared.symbol_match import symbol_has_definition as _symbol_has_definition


# ============================================================
# 注册表加载
# ============================================================

def load_registry(path: str | Path) -> dict:
    """读 YAML 并返回结构化对象。"""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "descriptors" not in data:
        raise ValueError(f"registry YAML must have 'descriptors' key: {path}")
    return data


# ============================================================
# helper 传递闭包计算（校验 5 的底料）
# ============================================================
# 口径：对每个注册的 compute_*，用 ast 求其函数体中全部 ast.Call(Name) 被调用名
# 的传递闭包（含 float/len/max 等内置与 pymatgen 类名），排除描述符自身，
# 按字典序排序。此口径与 scripts/helper_closure.py 完全一致，由 REGISTRY_NOTES.md
# 声明为 shared_intermediates 字段的唯一真相源。


def _get_all_functions(module_ast: ast.Module) -> dict[str, ast.FunctionDef]:
    """返回模块中所有顶层函数名 → FunctionDef。"""
    return {
        node.name: node
        for node in module_ast.body
        if isinstance(node, ast.FunctionDef)
    }


def _get_called_names(func_node: ast.FunctionDef) -> set[str]:
    """提取函数体中所有 ast.Call + ast.Name 的被调用名（不含属性链）。"""
    called: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)
    return called


def _compute_transitive_closure(
    func_name: str,
    func_map: dict[str, ast.FunctionDef],
    visited: set[str] | None = None,
) -> set[str]:
    """求 func_name 调用的所有函数名的传递闭包。

    递归遇到不在 func_map 中的被调用名时停止该分支（返回空集），
    但该被调用名本身仍计入上一层的结果集。
    """
    if visited is None:
        visited = set()
    if func_name in visited or func_name not in func_map:
        return set()
    visited.add(func_name)

    called = _get_called_names(func_map[func_name])
    result = set(called)
    for callee in called:
        result |= _compute_transitive_closure(callee, func_map, visited)
    return result


def compute_helper_closures(
    registry: dict,
    descriptors_dir: Path,
) -> dict[str, list[str]]:
    """对 registry 中每个描述符求 helper 调用的传递闭包。

    返回 {descriptor_name: sorted_closure_list}。
    闭包含全部被调用名（含内置），排除描述符自身，按字典序排序。
    """
    entries = registry.get("descriptors", [])

    module_asts: dict[str, ast.Module] = {}
    module_functions: dict[str, dict[str, ast.FunctionDef]] = {}
    for entry in entries:
        mod = entry["module"]
        if mod not in module_asts:
            path = descriptors_dir / mod
            source = path.read_text(encoding="utf-8")
            module_asts[mod] = ast.parse(source, filename=str(path))
            module_functions[mod] = _get_all_functions(module_asts[mod])

    # _base.py 也要解析（helper 在那里定义）
    base_path = descriptors_dir / "_base.py"
    if base_path.exists():
        base_ast = ast.parse(
            base_path.read_text(encoding="utf-8"), filename=str(base_path)
        )
        module_functions["_base.py"] = _get_all_functions(base_ast)

    per_descriptor: dict[str, list[str]] = {}
    for entry in entries:
        name = entry["name"]
        symbol = entry["implementation_symbol"]
        mod = entry["module"]

        func_map = module_functions.get(mod, {})
        if symbol not in func_map:
            # 也可能在 _base.py
            func_map = {**func_map, **module_functions.get("_base.py", {})}

        closure = _compute_transitive_closure(symbol, func_map)
        closure.discard(symbol)
        per_descriptor[name] = sorted(closure)

    return per_descriptor


# ============================================================
# 闸门
# ============================================================

REQUIRED_FIELDS = [
    "name",
    "family",
    "module",
    "implementation_symbol",
    "in_searchable",
    "estimand_math",
    "name_matches_estimand",
    "name_mismatch_note",
    "shared_intermediates",
    "known_invariance_defects",
    "parameter_provenance",
    "status",
]


def assert_registry_complete(
    registry: dict,
    live_py_contents: dict[str, str],
    code_descriptor_names: set[str] | None = None,
    code_active_for_search: dict[str, bool] | None = None,
    descriptors_dir: Path | None = None,
    invariance_report_path: Path | None = None,
) -> None:
    """五条校验全部执行，聚成列表后一次性抛出。

    错误信息按校验分节列出（每节标明校验名 + 违规条目 + 条数）。

    参数:
        registry: load_registry 返回的字典
        live_py_contents: {文件标签: 文件内容}，用于符号解析
        code_descriptor_names: 代码中实际存在的描述符名集合；
            若提供则做双向覆盖检查，若为 None 则跳过双向覆盖
        code_active_for_search: {描述符名: active_for_search 真值}，
            若提供则做 in_searchable 派生比对（校验 4），若为 None 则跳过
        descriptors_dir: descriptors 目录路径，**必传**（None 时抛错）；
            用于 shared_intermediates 传递闭包比对（校验 5）

    异常:
        ValueError: descriptors_dir 为 None 时抛错（校验 5 不可跳过）
    """
    if descriptors_dir is None:
        raise ValueError(
            "descriptors_dir 不可为 None：校验 5（shared_intermediates "
            "传递闭包比对）必须执行，调用者必须传入 descriptors 目录路径"
        )

    entries = registry.get("descriptors", [])
    if not entries:
        raise ValueError("registry has no descriptor entries")

    # 每条校验独立收集违规，最后分节汇总
    errors_1_coverage: list[str] = []
    errors_2_symbol: list[str] = []
    errors_3_todo: list[str] = []
    errors_4_in_searchable: list[str] = []
    errors_5_shared_intermediates: list[str] = []
    errors_6_field_domains: list[str] = []
    errors_7_invariance_defects: list[str] = []
    errors_8_impl_fields: list[str] = []

    # --- 校验 1: 双向覆盖 ---
    if code_descriptor_names is not None:
        registry_names = {e["name"] for e in entries}
        in_code_not_registry = code_descriptor_names - registry_names
        in_registry_not_code = registry_names - code_descriptor_names
        if in_code_not_registry:
            errors_1_coverage.append(
                f"代码中存在但 registry 中缺失: {sorted(in_code_not_registry)}"
            )
        if in_registry_not_code:
            errors_1_coverage.append(
                f"registry 中存在但代码中缺失: {sorted(in_registry_not_code)}"
            )

    # --- 校验 2: 符号可解析 ---
    for entry in entries:
        symbol = entry.get("implementation_symbol", "")
        if not symbol:
            errors_2_symbol.append(
                f"描述符 {entry.get('name', '?')} 的 implementation_symbol 为空"
            )
            continue
        if not any(
            _symbol_has_definition(symbol, body)
            for body in live_py_contents.values()
        ):
            errors_2_symbol.append(
                f"描述符 {entry.get('name', '?')} 的符号 "
                f"'{symbol}' 在所有活源码中无定义位置"
            )

    # --- 校验 3: 无 TODO 残留 ---
    for entry in entries:
        for field in REQUIRED_FIELDS:
            value = entry.get(field)
            if value == "TODO":
                errors_3_todo.append(
                    f"描述符 {entry.get('name', '?')} 的字段 '{field}' 仍为 TODO"
                )

    # --- 校验 4: in_searchable 派生比对 ---
    if code_active_for_search is not None:
        for entry in entries:
            name = entry.get("name", "?")
            yaml_in_searchable = entry.get("in_searchable")
            code_active = code_active_for_search.get(name)
            if code_active is None:
                errors_4_in_searchable.append(
                    f"描述符 '{name}' 不在 code_active_for_search 中"
                )
                continue
            if yaml_in_searchable != code_active:
                errors_4_in_searchable.append(
                    f"描述符 '{name}' "
                    f"YAML in_searchable={yaml_in_searchable} "
                    f"!= 代码 active_for_search={code_active}"
                )

    # --- 校验 5: shared_intermediates 传递闭包比对 ---
    expected_closures = compute_helper_closures(registry, descriptors_dir)
    for entry in entries:
        name = entry.get("name", "?")
        yaml_si = entry.get("shared_intermediates")
        exp = expected_closures.get(name, [])
        if yaml_si != exp:
            errors_5_shared_intermediates.append(
                f"描述符 '{name}' shared_intermediates 与 AST 闭包不符: "
                f"YAML={yaml_si} 期望={exp}"
            )

    # --- 校验 6: 字段值域条件必填（六字段） ---
    # 对仍为 TODO 的字段跳过（TODO 由校验 3 负责）。
    # 冻结白名单（estimand_math 中允许的标识符）
    _ESTIMAND_WHITELIST = {"mean", "std", "sum", "min", "max", "abs", "sqrt", "exp", "ln", "n", "i", "j", "k"}
    # _base.py 模块级常量名（从源码派生）
    _base_source = ""
    _base_path = descriptors_dir / "_base.py"
    if _base_path.exists():
        _base_source = _base_path.read_text(encoding="utf-8")
    import re as _re
    _base_constants = set()
    for m in _re.finditer(r"^\s*([A-Z_][A-Z0-9_]*)\s*[:=]", _base_source, _re.MULTILINE):
        _base_constants.add(m.group(1))

    # 已注册 helper 名（从闭包结果派生）
    _all_helpers = set()
    for hs in expected_closures.values():
        _all_helpers.update(hs)

    _VALID_NAME_MATCHES = {"yes", "no", "partial"}
    _VALID_STATUS = {"confirmed_match", "rename_required", "redefine_required", "retire", "unavailable_implementation"}
    _VALID_TRANSFORMS = {"site_permutation", "origin_shift", "lattice_rotation", "supercell",
                         "isotropic_scale", "occupancy_split", "geometry_jitter", "all_transforms"}
    _VALID_VERDICTS = {"invariant", "scaled_0.0", "scaled_1.0", "scaled_2.0", "scaled_3.0",
                       "scaled_-1.0", "scaled_-2.0", "scaled_-3.0",
                       "collapsed_to_zero",
                       "changed", "nan_both", "nan_introduced", "not_applicable", "dimension_mismatch",
                       "no_geometry_response", "permanently_nan",
                       # K6 新增码
                       "extensive_but_invariant", "undetermined_scaling", "dimension_declaration_conflict"}
    _VALID_EXTENSIVITY = {"extensive", "intensive", "undetermined"}
    # H2c：status=confirmed_match 时这些缺陷码一律禁止（与 value 表里的永久 NaN / 无几何响应冲突）
    _CONFIRMED_MATCH_FORBIDDEN_DEFECT_TOKENS = ("permanently_nan", "no_geometry_response")
    _TRIVIAL_LITERALS = {0, 1, 2, -1, 0.0, 1.0, 2.0}
    _VALID_PROVENANCE_PREFIXES = ("literature:", "inherited:", "no_provenance_found", "n_a")

    for entry in entries:
        name = entry.get("name", "?")
        estimand = entry.get("estimand_math")
        nme = entry.get("name_matches_estimand")
        note = entry.get("name_mismatch_note")
        defects = entry.get("known_invariance_defects")
        provenance = entry.get("parameter_provenance")
        status = entry.get("status")

        # estimand_math: 非空、不含 TODO、标识符白名单
        if estimand != "TODO":
            if not estimand or not str(estimand).strip():
                errors_6_field_domains.append(f"描述符 '{name}' estimand_math 为空")
            elif "TODO" in str(estimand):
                errors_6_field_domains.append(f"描述符 '{name}' estimand_math 含 TODO")
            else:
                # 检查标识符
                import ast as _ast
                try:
                    tree = _ast.parse(str(estimand), mode="eval")
                    for node in _ast.walk(tree):
                        if isinstance(node, _ast.Name):
                            ident = node.id
                            if (ident not in _ESTIMAND_WHITELIST
                                    and ident not in _all_helpers
                                    and ident not in _base_constants):
                                errors_6_field_domains.append(
                                    f"描述符 '{name}' estimand_math 含未注册标识符 '{ident}'"
                                )
                except SyntaxError:
                    errors_6_field_domains.append(
                        f"描述符 '{name}' estimand_math 不是合法表达式: {estimand}"
                    )

        # name_matches_estimand: 枚举 + 条件约束
        if nme != "TODO":
            if nme not in _VALID_NAME_MATCHES:
                errors_6_field_domains.append(
                    f"描述符 '{name}' name_matches_estimand='{nme}' 不在枚举 {sorted(_VALID_NAME_MATCHES)}"
                )
            else:
                note_str = str(note) if note is not None else ""
                if nme == "yes" and note_str.strip() != "":
                    errors_6_field_domains.append(
                        f"描述符 '{name}' name_matches_estimand=yes 但 name_mismatch_note 非空（禁止两头下注）"
                    )
                if nme in ("no", "partial") and note_str.strip() == "":
                    errors_6_field_domains.append(
                        f"描述符 '{name}' name_matches_estimand={nme} 但 name_mismatch_note 为空"
                    )

        # known_invariance_defects: 列表，每项 transform:verdict
        if defects != "TODO":
            if not isinstance(defects, list):
                errors_6_field_domains.append(
                    f"描述符 '{name}' known_invariance_defects 不是列表: {type(defects)}"
                )
            elif defects == ["none_found"]:
                pass  # 合法
            else:
                for item in defects:
                    parts = str(item).split(":", 1)
                    if len(parts) != 2:
                        errors_6_field_domains.append(
                            f"描述符 '{name}' known_invariance_defects 项 '{item}' 格式不是 transform:verdict"
                        )
                        continue
                    t, v = parts[0], parts[1]
                    if t not in _VALID_TRANSFORMS:
                        errors_6_field_domains.append(
                            f"描述符 '{name}' known_invariance_defects 项 '{item}' transform '{t}' 不在枚举"
                        )
                    if v not in _VALID_VERDICTS:
                        errors_6_field_domains.append(
                            f"描述符 '{name}' known_invariance_defects 项 '{item}' verdict '{v}' 不在枚举"
                        )

        # parameter_provenance: 列表，前缀校验 + 条数约束
        if provenance != "TODO":
            if not isinstance(provenance, list):
                errors_6_field_domains.append(
                    f"描述符 '{name}' parameter_provenance 不是列表: {type(provenance)}"
                )
            else:
                for item in provenance:
                    item_str = str(item)
                    if not any(item_str.startswith(p) for p in _VALID_PROVENANCE_PREFIXES):
                        errors_6_field_domains.append(
                            f"描述符 '{name}' parameter_provenance 项 '{item}' 前缀不在枚举"
                        )
                    if item_str.startswith("no_provenance_found") and "searched:" not in item_str:
                        errors_6_field_domains.append(
                            f"描述符 '{name}' parameter_provenance 项 '{item}' 缺 searched: 后缀"
                        )
                # 条数约束：≥ impl_literals 中非平凡字面量个数
                impl_lits = entry.get("impl_literals", [])
                if isinstance(impl_lits, list):
                    nontrivial_count = 0
                    for lit in impl_lits:
                        # 提取数值
                        for tok in _re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', str(lit)):
                            try:
                                if float(tok) not in _TRIVIAL_LITERALS:
                                    nontrivial_count += 1
                                    break
                            except ValueError:
                                pass
                    if len(provenance) < nontrivial_count:
                        errors_6_field_domains.append(
                            f"描述符 '{name}' parameter_provenance 条数 {len(provenance)} "
                            f"< 非平凡字面量个数 {nontrivial_count}"
                        )

        # status: 枚举 + 条件约束
        if status != "TODO":
            if status not in _VALID_STATUS:
                errors_6_field_domains.append(
                    f"描述符 '{name}' status='{status}' 不在枚举 {sorted(_VALID_STATUS)}"
                )
            elif status == "confirmed_match":
                if nme != "yes":
                    errors_6_field_domains.append(
                        f"描述符 '{name}' status=confirmed_match 但 name_matches_estimand={nme}（应为 yes）"
                    )
                if defects != ["none_found"]:
                    errors_6_field_domains.append(
                        f"描述符 '{name}' status=confirmed_match 但 known_invariance_defects={defects}（应为 ['none_found']）"
                    )
                if isinstance(defects, list):
                    for _item in defects:
                        if any(_tok in str(_item) for _tok in _CONFIRMED_MATCH_FORBIDDEN_DEFECT_TOKENS):
                            errors_6_field_domains.append(
                                f"描述符 '{name}' status=confirmed_match 但 known_invariance_defects "
                                f"含 {_CONFIRMED_MATCH_FORBIDDEN_DEFECT_TOKENS} 之一（H2c 禁止）: {_item}"
                            )
                            break
                if isinstance(provenance, list):
                    for item in provenance:
                        if str(item).startswith("no_provenance_found"):
                            errors_6_field_domains.append(
                                f"描述符 '{name}' status=confirmed_match 但 parameter_provenance 含 no_provenance_found"
                            )
                            break

    # --- 校验 7: known_invariance_defects 必须等于探针重算值 ---
    if invariance_report_path is not None:
        if not invariance_report_path.exists():
            raise ValueError(
                f"校验 7 不可跳过：不变性报告不存在: {invariance_report_path}"
            )
        import importlib.util as _ilu
        _fill_path = descriptors_dir.parent / "scripts" / "fill_invariance_field.py"
        _spec = _ilu.spec_from_file_location("_fill_invariance", _fill_path)
        _fill_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_fill_mod)
        expected_defects = _fill_mod.compute_defects_from_report(invariance_report_path)
        for entry in entries:
            name = entry.get("name", "?")
            yaml_defects = entry.get("known_invariance_defects")
            exp_defects = expected_defects.get(name, [])
            if yaml_defects != exp_defects:
                errors_7_invariance_defects.append(
                    f"描述符 '{name}' known_invariance_defects 与探针重算不符: "
                    f"YAML={yaml_defects} 期望={exp_defects}"
                )

    # --- 校验 8: impl_return_exprs / impl_literals / impl_guards 机器派生比对 ---
    import importlib.util as _ilu2
    _audit_path = descriptors_dir.parent / "scripts" / "impl_facts_audit.py"
    if _audit_path.exists():
        _spec2 = _ilu2.spec_from_file_location("_impl_audit", _audit_path)
        _audit_mod = _ilu2.module_from_spec(_spec2)
        _spec2.loader.exec_module(_audit_mod)
        _reg_list = registry.get("descriptors", [])
        _mod_funcs, _mod_srcs = _audit_mod.get_all_module_functions(_reg_list)
        for entry in entries:
            name = entry.get("name", "?")
            symbol = entry.get("implementation_symbol", "")
            mod = entry.get("module", "")
            _fm = _mod_funcs.get(mod, {})
            if symbol not in _fm:
                _fm = {**_fm, **_mod_funcs.get("_base.py", {})}
            _src = _mod_srcs.get(mod, "")
            _fn = _fm.get(symbol)
            if _fn is None:
                continue
            # 比对 impl_return_exprs
            _exp_returns = [f"{s} (L{l})" for s, l in _audit_mod.extract_return_exprs(_fn, _src)]
            if entry.get("impl_return_exprs") != _exp_returns:
                errors_8_impl_fields.append(
                    f"描述符 '{name}' impl_return_exprs 与机器重算不符: "
                    f"YAML={entry.get('impl_return_exprs')} 期望={_exp_returns}"
                )
            # 比对 impl_literals
            _exp_lits = [f"{v} (L{l})" for v, l in _audit_mod.extract_literals(_fn)]
            if entry.get("impl_literals") != _exp_lits:
                errors_8_impl_fields.append(
                    f"描述符 '{name}' impl_literals 与机器重算不符: "
                    f"YAML={entry.get('impl_literals')} 期望={_exp_lits}"
                )
            # 比对 impl_guards
            _exp_guards = [f"{c} (L{l})" for c, l in _audit_mod.extract_guards(_fn, _src)]
            if entry.get("impl_guards") != _exp_guards:
                errors_8_impl_fields.append(
                    f"描述符 '{name}' impl_guards 与机器重算不符: "
                    f"YAML={entry.get('impl_guards')} 期望={_exp_guards}"
                )

    # --- 校验 9: extensivity 探针重算比对（K6 新增，与校验 7 同型） ---
    errors_9_extensivity: list[str] = []
    if invariance_report_path is not None and invariance_report_path.exists():
        _ext_mod = _fill_mod  # 复用已加载的 fill_invariance_field 模块上下文
        import importlib.util as _ilu2
        _ext_path = descriptors_dir.parent / "scripts" / "fill_extensivity_field.py"
        if _ext_path.exists():
            _ext_spec = _ilu2.spec_from_file_location("_fill_ext", _ext_path)
            _ext_mod2 = _ilu2.module_from_spec(_ext_spec)
            _ext_spec.loader.exec_module(_ext_mod2)
            _expected_ext = _ext_mod2.derive_extensivity(invariance_report_path)
            for entry in entries:
                _name = entry.get("name", "?")
                _yaml_ext = entry.get("extensivity")
                _exp_ext = _expected_ext.get(_name, "undetermined")
                # 值域校验
                if _yaml_ext not in _VALID_EXTENSIVITY:
                    errors_9_extensivity.append(
                        f"描述符 '{_name}' extensivity='{_yaml_ext}' 不在枚举 {sorted(_VALID_EXTENSIVITY)}"
                    )
                elif _yaml_ext != _exp_ext:
                    errors_9_extensivity.append(
                        f"描述符 '{_name}' extensivity='{_yaml_ext}' 与探针重算不符: 期望='{_exp_ext}'"
                    )

    # --- 分节汇总 ---
    sections: list[str] = []
    total = 0

    def _add_section(title: str, items: list[str]) -> None:
        nonlocal total
        if items:
            sections.append(
                f"【{title}】（{len(items)} 条）\n  "
                + "\n  ".join(items)
            )
            total += len(items)

    _add_section("校验 1: 双向覆盖", errors_1_coverage)
    _add_section("校验 2: 符号可解析", errors_2_symbol)
    _add_section("校验 3: 无 TODO 残留", errors_3_todo)
    _add_section("校验 4: in_searchable 派生比对", errors_4_in_searchable)
    _add_section("校验 5: shared_intermediates 传递闭包比对", errors_5_shared_intermediates)
    _add_section("校验 6: 字段值域条件必填", errors_6_field_domains)
    _add_section("校验 7: known_invariance_defects 探针重算比对", errors_7_invariance_defects)
    _add_section("校验 8: impl_return_exprs/literals/guards 机器派生比对", errors_8_impl_fields)
    _add_section("校验 9: extensivity 探针重算比对", errors_9_extensivity)

    if sections:
        raise ValueError(
            f"registry 闸门校验失败，共 {total} 条违规，分 {len(sections)} 节：\n\n"
            + "\n\n".join(sections)
        )
