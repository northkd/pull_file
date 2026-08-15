"""E2: 对每个注册 compute_* 用 ast 机器抽取 impl 事实，与 YAML 做 diff。

抽取：
① 全部 Return 节点的源码原文（ast.get_source_segment）+ 行号
② 全部数值 Constant 节点（int/float，排除 bool/str）的值 + 行号

与 YAML 的 impl_return_exprs / impl_literals 比对，只报告不修改。
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DESCRIPTORS_DIR = REPO_ROOT / "descriptors"
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"


def _load_registry() -> list[dict]:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data["descriptors"]


def _parse_module_with_source(module_name: str) -> tuple[ast.Module, str]:
    path = DESCRIPTORS_DIR / module_name
    source = path.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(path)), source


def _get_all_functions(module_ast: ast.Module) -> dict[str, ast.FunctionDef]:
    return {
        node.name: node
        for node in module_ast.body
        if isinstance(node, ast.FunctionDef)
    }


def extract_return_exprs(func_node: ast.FunctionDef, source: str) -> list[tuple[str, int]]:
    """抽取全部 Return 节点的源码原文 + 行号，按行号升序。"""
    results: list[tuple[str, int]] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return):
            seg = ast.get_source_segment(source, node)
            if seg is None:
                seg = ast.unparse(node)
            results.append((seg.strip(), node.lineno))
    results.sort(key=lambda x: x[1])
    return results


def extract_literals(func_node: ast.FunctionDef) -> list[tuple[object, int]]:
    """抽取全部数值 Constant（int/float，排除 bool）的值 + 行号，按行号升序。"""
    results: list[tuple[object, int]] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Constant):
            val = node.value
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                results.append((val, node.lineno))
    results.sort(key=lambda x: x[1])
    return results


def extract_guards(func_node: ast.FunctionDef, source: str) -> list[tuple[str, int]]:
    """抽取全部 ast.If 的条件源码 + 行号，按行号升序。"""
    results: list[tuple[str, int]] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.If):
            seg = ast.get_source_segment(source, node.test)
            if seg is None:
                seg = ast.unparse(node.test)
            results.append((seg.strip(), node.lineno))
    results.sort(key=lambda x: x[1])
    return results


def get_all_module_functions(registry: list[dict]):
    """解析 registry 涉及的全部模块 + _base.py，返回 (模块函数映射, 模块源码映射)。"""
    module_asts: dict[str, ast.Module] = {}
    module_sources: dict[str, str] = {}
    module_functions: dict[str, dict[str, ast.FunctionDef]] = {}
    for entry in registry:
        mod = entry["module"]
        if mod not in module_asts:
            module_asts[mod], module_sources[mod] = _parse_module_with_source(mod)
            module_functions[mod] = _get_all_functions(module_asts[mod])

    base_path = DESCRIPTORS_DIR / "_base.py"
    if base_path.exists():
        base_source = base_path.read_text(encoding="utf-8")
        base_ast = ast.parse(base_source, filename=str(base_path))
        module_asts["_base.py"] = base_ast
        module_sources["_base.py"] = base_source
        module_functions["_base.py"] = _get_all_functions(base_ast)

    return module_functions, module_sources


def _parse_yaml_return_exprs(yaml_list: list[str]) -> list[tuple[str, str]]:
    """解析 YAML 的 impl_return_exprs，返回 (源码, 行号标记) 列表。

    格式如 'return _safe_mean(data["per_site_max"]) (L105)'
    源码 = 去掉 (Lxxx) 后缀的部分，行号标记 = Lxxx 字符串。
    """
    parsed = []
    for item in yaml_list:
        m = re.match(r"^(.*?)\s*\(L(\d+)\)$", item.strip())
        if m:
            parsed.append((m.group(1).strip(), f"L{m.group(2)}"))
        else:
            parsed.append((item.strip(), "?"))
    return parsed


def _parse_yaml_literals(yaml_list: list[str]) -> list[tuple[str, str]]:
    """解析 YAML 的 impl_literals，返回 (数值描述, 行号标记) 列表。

    格式多样，如 '1e-12 (L196)'、'2 (L197, len(eigenvalues)>=2)'、
    '氧化态字典1,2,3,4,5,-1,-2 (L55-63)'。
    """
    parsed = []
    for item in yaml_list:
        m = re.match(r"^(.*?)\s*\(L([\d,\-]+).*?\)$", item.strip())
        if m:
            parsed.append((m.group(1).strip(), f"L{m.group(2)}"))
        else:
            parsed.append((item.strip(), "?"))
    return parsed


def main() -> int:
    registry = _load_registry()

    module_asts: dict[str, ast.Module] = {}
    module_sources: dict[str, str] = {}
    module_functions: dict[str, dict[str, ast.FunctionDef]] = {}
    for entry in registry:
        mod = entry["module"]
        if mod not in module_asts:
            module_asts[mod], module_sources[mod] = _parse_module_with_source(mod)
            module_functions[mod] = _get_all_functions(module_asts[mod])

    base_path = DESCRIPTORS_DIR / "_base.py"
    if base_path.exists():
        base_source = base_path.read_text(encoding="utf-8")
        base_ast = ast.parse(base_source, filename=str(base_path))
        module_asts["_base.py"] = base_ast
        module_sources["_base.py"] = base_source
        module_functions["_base.py"] = _get_all_functions(base_ast)

    n_return_mismatch = 0
    n_literal_mismatch = 0
    n_return_match = 0
    n_literal_match = 0

    for entry in registry:
        name = entry["name"]
        symbol = entry["implementation_symbol"]
        mod = entry["module"]

        func_map = module_functions.get(mod, {})
        if symbol not in func_map:
            func_map = {**func_map, **module_functions.get("_base.py", {})}
        source = module_sources.get(mod, "")

        func_node = func_map.get(symbol)
        if func_node is None:
            print(f"=== {name} === 警告: 符号 {symbol} 未找到，跳过")
            continue

        # 机器抽取
        machine_returns = _extract_return_exprs(func_node, source)
        machine_literals = _extract_literals(func_node)

        # YAML 值
        yaml_returns = _parse_yaml_return_exprs(entry.get("impl_return_exprs", []))
        yaml_literals = _parse_yaml_literals(entry.get("impl_literals", []))

        print(f"=== {name} ({symbol}) ===")

        # --- return_exprs 比对 ---
        # 比对源码（去行号）和行号
        yaml_return_sources = [r[0] for r in yaml_returns]
        machine_return_sources = [r[0] for r in machine_returns]
        yaml_return_lines = [r[1] for r in yaml_returns]
        machine_return_lines = [f"L{r[1]}" for r in machine_returns]

        return_match = (yaml_return_sources == machine_return_sources
                        and yaml_return_lines == machine_return_lines)
        if return_match:
            n_return_match += 1
            print(f"  return_exprs: 一致 ({len(machine_returns)} 条)")
        else:
            n_return_mismatch += 1
            print(f"  return_exprs: 不一致")
            print(f"    YAML  ({len(yaml_returns)} 条): {yaml_returns}")
            print(f"    机器  ({len(machine_returns)} 条): {list(zip(machine_return_sources, machine_return_lines))}")

        # --- literals 比对 ---
        # 只比对数值个数与行号（YAML 的人工注释无法机器重现）
        yaml_lit_values = [l[0] for l in yaml_literals]
        yaml_lit_lines = [l[1] for l in yaml_literals]
        machine_lit_values = [str(l[0]) for l in machine_literals]
        machine_lit_lines = [f"L{l[1]}" for l in machine_literals]

        literal_match = (len(yaml_literals) == len(machine_literals)
                         and yaml_lit_lines == machine_lit_lines)
        if literal_match:
            n_literal_match += 1
            print(f"  literals: 一致 ({len(machine_literals)} 条)")
        else:
            n_literal_mismatch += 1
            print(f"  literals: 不一致")
            print(f"    YAML  ({len(yaml_literals)} 条): {yaml_literals}")
            print(f"    机器  ({len(machine_literals)} 条): {list(zip(machine_lit_values, machine_lit_lines))}")

        print()

    print("=" * 70)
    print("汇总:")
    print(f"  return_exprs: 一致 {n_return_match} / 不一致 {n_return_mismatch} / 总 {n_return_match + n_return_mismatch}")
    print(f"  literals:     一致 {n_literal_match} / 不一致 {n_literal_mismatch} / 总 {n_literal_match + n_literal_mismatch}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
