"""F4: 机器生成 impl_return_exprs / impl_literals / impl_guards 写入 YAML。

口径（写进 REGISTRY_FIELD_DOMAINS.md）：
  impl_return_exprs — ast.Return 节点的 get_source_segment，按源码行号升序
  impl_literals     — 全部数值 ast.Constant，按行号升序，含平凡值
  impl_guards       — 全部 ast.If 的条件源码 + 行号

impl_nan_paths 改为显式人工字段（从原 impl_guards_and_nan_paths 字符串中提取
nan_paths 部分），不可机器派生。

用法:
    python scripts/fill_impl_fields.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.impl_facts_audit import (
    _load_registry,
    get_all_module_functions,
    extract_return_exprs,
    extract_literals,
    extract_guards,
)

REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"


def _format_return_expr(exprs: list[tuple[str, int]]) -> list[str]:
    """格式：'源码 (L行号)'。"""
    return [f"{src} (L{line})" for src, line in exprs]


def _format_literals(lits: list[tuple[object, int]]) -> list[str]:
    """格式：'数值 (L行号)'。"""
    return [f"{val} (L{line})" for val, line in lits]


def _format_guards(guards: list[tuple[str, int]]) -> list[str]:
    """格式：'条件源码 (L行号)'。"""
    return [f"{cond} (L{line})" for cond, line in guards]


def _extract_nan_paths_from_old(old_str: str) -> str:
    """从旧 impl_guards_and_nan_paths 字符串中提取 nan_paths 部分。"""
    if "nan_paths:" in old_str:
        idx = old_str.index("nan_paths:")
        return old_str[idx:].strip()
    return "nan_paths: 无"


def main() -> int:
    registry = _load_registry()
    module_functions, module_sources = get_all_module_functions(registry)

    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096
    data = ryaml.load(REGISTRY_PATH.read_text(encoding="utf-8"))

    changed = 0
    for entry in data["descriptors"]:
        name = entry["name"]
        symbol = entry["implementation_symbol"]
        mod = entry["module"]

        func_map = module_functions.get(mod, {})
        if symbol not in func_map:
            func_map = {**func_map, **module_functions.get("_base.py", {})}
        source = module_sources.get(mod, "")
        func_node = func_map.get(symbol)

        if func_node is None:
            print(f"WARNING: {name} 符号 {symbol} 未找到，跳过")
            continue

        # 机器生成三个字段
        machine_returns = extract_return_exprs(func_node, source)
        machine_lits = extract_literals(func_node)
        machine_guards = extract_guards(func_node, source)

        new_return_exprs = _format_return_expr(machine_returns)
        new_literals = _format_literals(machine_lits)
        new_guards = _format_guards(machine_guards)

        # 从旧字段提取 nan_paths
        old_combined = entry.get("impl_guards_and_nan_paths", "")
        nan_paths = _extract_nan_paths_from_old(str(old_combined))

        old_return = entry.get("impl_return_exprs")
        old_lits = entry.get("impl_literals")

        if (old_return != new_return_exprs or old_lits != new_literals
                or "impl_guards" not in entry or "impl_nan_paths" not in entry):
            changed += 1

        entry["impl_return_exprs"] = new_return_exprs
        entry["impl_literals"] = new_literals
        entry["impl_guards"] = new_guards
        entry["impl_nan_paths"] = nan_paths

        # 删除旧字段
        if "impl_guards_and_nan_paths" in entry:
            del entry["impl_guards_and_nan_paths"]

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)

    print(f"共 {len(data['descriptors'])} 条，其中 {changed} 条被更新")
    print("  impl_return_exprs / impl_literals / impl_guards: 机器生成")
    print("  impl_nan_paths: 从旧字段提取，人工字段")
    return 0


if __name__ == "__main__":
    sys.exit(main())
