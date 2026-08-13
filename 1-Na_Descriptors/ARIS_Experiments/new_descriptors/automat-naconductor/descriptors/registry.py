"""描述符注册表加载与闸门校验。

提供 load_registry 和 assert_registry_complete 两个函数。
assert_registry_complete 实现三条校验：
1. 双向覆盖：代码中每个注册描述符必须在 registry 有条目，反之亦然；
2. 符号可解析：每条的 implementation_symbol 必须通过定义位置整词匹配；
3. 无 TODO 残留：任一字段值为字面量 TODO 时抛错。
"""
from __future__ import annotations

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
) -> None:
    """三条校验，任一不过即抛 ValueError。

    参数:
        registry: load_registry 返回的字典
        live_py_contents: {文件标签: 文件内容}，用于符号解析
        code_descriptor_names: 代码中实际存在的描述符名集合；
            若提供则做双向覆盖检查，若为 None 则跳过双向覆盖
    """
    entries = registry.get("descriptors", [])
    if not entries:
        raise ValueError("registry has no descriptor entries")

    errors: list[str] = []

    # --- 校验 1: 双向覆盖 ---
    if code_descriptor_names is not None:
        registry_names = {e["name"] for e in entries}
        in_code_not_registry = code_descriptor_names - registry_names
        in_registry_not_code = registry_names - code_descriptor_names
        if in_code_not_registry:
            errors.append(
                f"双向覆盖失败：代码中存在但 registry 中缺失: "
                f"{sorted(in_code_not_registry)}"
            )
        if in_registry_not_code:
            errors.append(
                f"双向覆盖失败：registry 中存在但代码中缺失: "
                f"{sorted(in_registry_not_code)}"
            )

    # --- 校验 2: 符号可解析 ---
    for entry in entries:
        symbol = entry.get("implementation_symbol", "")
        if not symbol:
            errors.append(
                f"符号解析失败：描述符 {entry.get('name', '?')} 的 implementation_symbol 为空"
            )
            continue
        if not any(
            _symbol_has_definition(symbol, body)
            for body in live_py_contents.values()
        ):
            errors.append(
                f"符号解析失败：描述符 {entry.get('name', '?')} 的符号 "
                f"'{symbol}' 在所有活源码中无定义位置"
            )

    # --- 校验 3: 无 TODO 残留 ---
    for entry in entries:
        for field in REQUIRED_FIELDS:
            value = entry.get(field)
            if value == "TODO":
                errors.append(
                    f"TODO 残留：描述符 {entry.get('name', '?')} 的字段 '{field}' 仍为 TODO"
                )

    if errors:
        raise ValueError(
            "registry 闸门校验失败，共 " + str(len(errors)) + " 条：\n  "
            + "\n  ".join(errors)
        )
