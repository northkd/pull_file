"""J1: 为 registry 的 estimand_math 准备唯一合法底料。

从 descriptor_registry.yaml 派生描述符名单，抽取每条描述符的 compute_* 函数完整源码、
AST 传递闭包中的仓内 helper、以及函数体引用的模块级常量。

闭包计算复用 descriptors/registry.py:compute_helper_closures（与闸门校验 5 同一套 AST
传递闭包实现，scripts/helper_closure.py 也委托给它）。本脚本不另写第二套闭包。

产物中只抄源码，不做评价、不做总结、不做推断。

用法:
    python scripts/extract_descriptor_sources.py --batch 1
    python scripts/extract_descriptor_sources.py --batch 1 --commit 440ce1f
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# 复用闸门校验 5 的同一套闭包实现
sys.path.insert(0, str(REPO_ROOT))
from descriptors.registry import compute_helper_closures  # noqa: E402


# ============================================================
# 文件读取：支持 git show 快照
# ============================================================

def _git_show(commit: str, repo_path: str) -> str:
    """用 git show <commit>:<repo_path> 读取历史快照文件内容（只读，不落盘到工作区）。"""
    result = subprocess.run(
        ["git", "show", f"{commit}:{repo_path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git show {commit}:{repo_path} 失败 (exit={result.returncode}): {result.stderr}"
        )
    return result.stdout


def _read_file(commit: str | None, repo_path: str) -> str:
    """读取文件：指定 commit 则走 git show，否则从工作区读。"""
    if commit:
        return _git_show(commit, repo_path)
    return (REPO_ROOT / repo_path).read_text(encoding="utf-8")


# ============================================================
# 名单派生与断言
# ============================================================

def _load_registry(commit: str | None) -> dict:
    """加载 descriptor_registry.yaml。"""
    source = _read_file(commit, "descriptor_registry.yaml")
    return yaml.safe_load(source)


def _extract_available_names_from_init(source: str) -> set[str]:
    """从 descriptors/__init__.py 源码中解析 AVAILABLE_STRUCTURE_DESCRIPTORS 的键集合。

    用 AST 提取字典字面量的字符串键，不执行代码。
    """
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        target_name = None
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "AVAILABLE_STRUCTURE_DESCRIPTORS":
                    target_name = t.id
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "AVAILABLE_STRUCTURE_DESCRIPTORS":
                target_name = node.target.id

        if target_name and isinstance(node.value, ast.Dict):
            names = set()
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)
            return names

    raise RuntimeError("未在 descriptors/__init__.py 中找到 AVAILABLE_STRUCTURE_DESCRIPTORS 字典")


def _derive_and_assert_names(
    registry: dict,
    commit: str | None,
) -> list[str]:
    """从 registry 派生描述符名单，断言条数与双向差集。"""
    names = [entry["name"] for entry in registry["descriptors"]]

    # 断言条数 == 41
    if len(names) != 41:
        raise RuntimeError(f"描述符条数 != 41: 实际 {len(names)}")

    # 从 __init__.py 解析 AVAILABLE_STRUCTURE_DESCRIPTORS 的键
    init_source = _read_file(commit, "descriptors/__init__.py")
    available_names = _extract_available_names_from_init(init_source)

    yaml_set = set(names)
    only_yaml = yaml_set - available_names
    only_init = available_names - yaml_set

    if only_yaml or only_init:
        raise RuntimeError(
            f"名单双向差集非空:\n"
            f"  仅 YAML 有: {sorted(only_yaml)}\n"
            f"  仅 __init__ 有: {sorted(only_init)}"
        )

    return names


# ============================================================
# dimension / unit 提取
# ============================================================

def _extract_dim_unit_map(source: str) -> dict[str, tuple[str, str]]:
    """从 descriptors/__init__.py 源码解析 _DESCRIPTOR_UNITS_AND_DIMENSIONS。"""
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        is_target = False
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_DESCRIPTOR_UNITS_AND_DIMENSIONS":
                    is_target = True
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "_DESCRIPTOR_UNITS_AND_DIMENSIONS":
                is_target = True

        if is_target and node.value is not None:
            return ast.literal_eval(node.value)

    raise RuntimeError("未找到 _DESCRIPTOR_UNITS_AND_DIMENSIONS")


# ============================================================
# 函数源码提取
# ============================================================

def _extract_function_source(
    source: str,
    func_name: str,
) -> tuple[str, int, int] | None:
    """从模块源码中提取指定函数的完整源码（含 decorator 与 docstring）。

    返回 (source_text, start_line, end_line) 或 None（未找到）。
    """
    tree = ast.parse(source)
    lines = source.splitlines()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            # 起始行：含 decorator
            start = node.lineno
            if node.decorator_list:
                start = min(d.lineno for d in node.decorator_list)
            end = node.end_lineno
            func_source = "\n".join(lines[start - 1:end])
            return func_source, start, end

    return None


# ============================================================
# 闭包计算（复用 compute_helper_closures）
# ============================================================

def _compute_closures(
    commit: str | None,
    registry: dict,
) -> dict[str, list[str]]:
    """计算 helper 传递闭包。

    复用 descriptors/registry.py:compute_helper_closures（与闸门校验 5、
    scripts/helper_closure.py 同一套 AST 传递闭包实现）。

    若指定 commit，将模块文件写入临时目录后调用（只读快照，不修改工作区）。
    """
    if commit is None:
        return compute_helper_closures(registry, REPO_ROOT / "descriptors")

    # commit 模式：写临时目录
    with tempfile.TemporaryDirectory(prefix="j1_closure_") as tmpdir:
        tmp_desc = Path(tmpdir)
        modules_needed = set()
        for entry in registry["descriptors"]:
            modules_needed.add(entry["module"])
        modules_needed.add("_base.py")

        for mod in modules_needed:
            source = _git_show(commit, f"descriptors/{mod}")
            (tmp_desc / mod).write_text(source, encoding="utf-8")

        return compute_helper_closures(registry, tmp_desc)


# ============================================================
# 仓内 helper 识别与源码提取
# ============================================================

def _collect_in_repo_function_names(
    commit: str | None,
    module_files: list[str],
) -> dict[str, str]:
    """收集所有描述符模块中定义的函数名 → 所在模块文件名。

    返回 {func_name: module_file}。
    """
    result: dict[str, str] = {}
    for mod_file in module_files:
        rel_path = f"descriptors/{mod_file}"
        source = _read_file(commit, rel_path)
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name not in result:
                    result[node.name] = mod_file
    return result


def _extract_helper_sources(
    commit: str | None,
    module_files: list[str],
    helper_names: set[str],
) -> dict[str, tuple[str, str, int, int]]:
    """提取仓内 helper 的源码。

    返回 {helper_name: (rel_path, source_text, start_line, end_line)}。
    """
    result: dict[str, tuple[str, str, int, int]] = {}
    for mod_file in module_files:
        rel_path = f"descriptors/{mod_file}"
        source = _read_file(commit, rel_path)
        lines = source.splitlines()
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name in helper_names:
                if node.name not in result:
                    start = node.lineno
                    if node.decorator_list:
                        start = min(d.lineno for d in node.decorator_list)
                    end = node.end_lineno
                    func_source = "\n".join(lines[start - 1:end])
                    result[node.name] = (rel_path, func_source, start, end)
    return result


# ============================================================
# 模块级常量提取
# ============================================================

def _collect_module_level_constants(
    commit: str | None,
    module_files: list[str],
) -> dict[str, tuple[str, str, int, int]]:
    """收集所有描述符模块中的模块级常量定义。

    返回 {const_name: (rel_path, definition_line_text, start_line, end_line)}。
    """
    result: dict[str, tuple[str, str, int, int]] = {}
    for mod_file in module_files:
        rel_path = f"descriptors/{mod_file}"
        source = _read_file(commit, rel_path)
        lines = source.splitlines()
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id not in result:
                            start = node.lineno
                            end = node.end_lineno
                            def_line = "\n".join(lines[start - 1:end])
                            result[target.id] = (rel_path, def_line, start, end)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name not in result:
                    start = node.lineno
                    end = node.end_lineno
                    def_line = "\n".join(lines[start - 1:end])
                    result[name] = (rel_path, def_line, start, end)
    return result


def _get_names_referenced_in_function(func_source: str) -> set[str]:
    """获取函数体内引用的所有 Name 标识符。"""
    tree = ast.parse(func_source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
    return names


# ============================================================
# 产物生成
# ============================================================

BATCH_SIZES = [11, 10, 10, 10]


def _build_output(
    commit: str | None,
    actual_sha: str,
    batch_num: int,
    entries: list[dict],
    dim_unit_map: dict[str, tuple[str, str]],
    closures: dict[str, list[str]],
    in_repo_funcs: dict[str, str],
    all_module_files: list[str],
    all_helper_sources: dict[str, tuple[str, str, int, int]],
    all_const_defs: dict[str, tuple[str, str, int, int]],
    not_found_symbols: list[tuple[str, str]],
) -> str:
    """生成单批次 Markdown 产物。"""
    lines: list[str] = []

    # 首行写 sha
    lines.append(f"<!-- sha: {actual_sha} -->")
    lines.append("")

    lines.append(f"# 描述符源码抽取 — 批次 {batch_num}")
    lines.append("")

    total = sum(BATCH_SIZES)
    start_idx = sum(BATCH_SIZES[:batch_num - 1])
    end_idx = start_idx + BATCH_SIZES[batch_num - 1]
    lines.append(f"本批覆盖第 {start_idx + 1}–{end_idx} 条（共 {total} 条，分 4 批）。")
    lines.append("")

    # 收集本批用到的 helper 和常量（去重）
    batch_helpers: dict[str, tuple[str, str, int, int]] = {}
    batch_consts: dict[str, tuple[str, str, int, int]] = {}

    for entry in entries:
        name = entry["name"]
        family = entry["family"]
        module = entry["module"]
        symbol = entry["implementation_symbol"]
        in_searchable = entry["in_searchable"]
        unit, dimension = dim_unit_map.get(name, ("", ""))

        lines.append(f"## {name}")
        lines.append("")

        # 1. 七个字段
        lines.append("### 字段")
        lines.append("")
        lines.append(f"- name: `{name}`  (source: descriptor_registry.yaml)")
        lines.append(f"- family: `{family}`  (source: descriptor_registry.yaml)")
        lines.append(f"- module: `{module}`  (source: descriptor_registry.yaml)")
        lines.append(f"- implementation_symbol: `{symbol}`  (source: descriptor_registry.yaml)")
        lines.append(f"- dimension: `{dimension}`  (source: STRUCTURE_DESCRIPTOR_METADATA)")
        lines.append(f"- unit: `{unit}`  (source: STRUCTURE_DESCRIPTOR_METADATA)")
        lines.append(f"- in_searchable: `{in_searchable}`  (source: descriptor_registry.yaml)")
        lines.append("")

        # 2. compute_* 函数源码
        module_source = _read_file(commit, f"descriptors/{module}")
        func_result = _extract_function_source(module_source, symbol)

        if func_result is None:
            # 也尝试 _base.py
            base_source = _read_file(commit, "descriptors/_base.py")
            func_result = _extract_function_source(base_source, symbol)

        if func_result is None:
            not_found_symbols.append((name, symbol))
            lines.append("### compute_* 函数源码")
            lines.append("")
            lines.append(f"**未找到定义: `{symbol}`**")
            lines.append("")
        else:
            func_source, start_line, end_line = func_result
            lines.append("### compute_* 函数源码")
            lines.append("")
            rel_path = f"descriptors/{module}" if _symbol_in_module(commit, module, symbol) else "descriptors/_base.py"
            lines.append(f"文件: `{rel_path}:{start_line}-{end_line}`")
            lines.append("")
            lines.append("```python")
            lines.append(func_source)
            lines.append("```")
            lines.append("")

            # 3. 闭包中的仓内 helper
            closure = closures.get(name, [])
            in_repo_helpers = sorted(
                h for h in closure if h in in_repo_funcs
            )
            lines.append("### 仓内 helper（AST 传递闭包）")
            lines.append("")
            if in_repo_helpers:
                for h in in_repo_helpers:
                    lines.append(f"- `{h}` → [附录: helper 源码](#helper-{h})")
                    if h in all_helper_sources:
                        batch_helpers[h] = all_helper_sources[h]
            else:
                lines.append("（无仓内 helper）")
            lines.append("")

            # 4. 模块级常量
            referenced_names = _get_names_referenced_in_function(func_source)
            const_names_in_repo = set(all_const_defs.keys())
            referenced_consts = sorted(
                n for n in referenced_names if n in const_names_in_repo
            )
            lines.append("### 引用的模块级常量")
            lines.append("")
            if referenced_consts:
                for c in referenced_consts:
                    lines.append(f"- `{c}` → [附录: 常量定义](#const-{c})")
                    if c in all_const_defs:
                        batch_consts[c] = all_const_defs[c]
            else:
                lines.append("（无模块级常量引用）")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 附录
    lines.append("## 附录")
    lines.append("")

    # 附录 A: helper 源码
    if batch_helpers:
        lines.append("### A. helper 源码")
        lines.append("")
        for h in sorted(batch_helpers):
            rel_path, source, start, end = batch_helpers[h]
            lines.append(f"<a id=\"helper-{h}\"></a>")
            lines.append(f"#### `{h}` — `{rel_path}:{start}-{end}`")
            lines.append("")
            lines.append("```python")
            lines.append(source)
            lines.append("```")
            lines.append("")

    # 附录 B: 常量定义
    if batch_consts:
        lines.append("### B. 模块级常量定义")
        lines.append("")
        for c in sorted(batch_consts):
            rel_path, def_line, start, end = batch_consts[c]
            lines.append(f"<a id=\"const-{c}\"></a>")
            lines.append(f"#### `{c}` — `{rel_path}:{start}-{end}`")
            lines.append("")
            lines.append("```python")
            lines.append(def_line)
            lines.append("```")
            lines.append("")

    # 未找到的 symbol
    if not_found_symbols:
        lines.append("### C. 未找到定义位置的 implementation_symbol")
        lines.append("")
        for name, symbol in not_found_symbols:
            lines.append(f"- 描述符 `{name}`: `{symbol}` 在模块文件及 _base.py 中均未找到定义")
        lines.append("")

    return "\n".join(lines)


def _symbol_in_module(commit: str | None, module: str, symbol: str) -> bool:
    """检查 symbol 是否定义在指定模块中。"""
    source = _read_file(commit, f"descriptors/{module}")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == symbol:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="抽取描述符 compute_* 函数源码、闭包 helper、模块级常量"
    )
    parser.add_argument(
        "--commit",
        default=None,
        help="git commit sha，走 git show <sha>:<path> 读快照（默认 HEAD/工作区）",
    )
    parser.add_argument(
        "--batch",
        type=int,
        required=True,
        choices=[1, 2, 3, 4],
        help="批次号 1-4（分别 11/10/10/10 条）",
    )
    args = parser.parse_args()

    # 确定 sha
    if args.commit:
        actual_sha = args.commit
    else:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        actual_sha = result.stdout.strip()

    # 加载 registry
    registry = _load_registry(args.commit)

    # 派生名单并断言
    names = _derive_and_assert_names(registry, args.commit)

    # 提取 dimension/unit
    init_source = _read_file(args.commit, "descriptors/__init__.py")
    dim_unit_map = _extract_dim_unit_map(init_source)

    # 确定模块文件列表
    module_files = sorted({
        entry["module"] for entry in registry["descriptors"]
    })
    module_files.insert(0, "_base.py")

    # 收集仓内函数名
    in_repo_funcs = _collect_in_repo_function_names(args.commit, module_files)

    # 计算闭包
    closures = _compute_closures(args.commit, registry)

    # 预提取所有 helper 源码和常量定义
    all_helper_names: set[str] = set()
    for name, closure in closures.items():
        for h in closure:
            if h in in_repo_funcs:
                all_helper_names.add(h)

    all_helper_sources = _extract_helper_sources(
        args.commit, module_files, all_helper_names
    )
    all_const_defs = _collect_module_level_constants(args.commit, module_files)

    # 分批
    start_idx = sum(BATCH_SIZES[:args.batch - 1])
    end_idx = start_idx + BATCH_SIZES[args.batch - 1]
    batch_entries = registry["descriptors"][start_idx:end_idx]

    not_found_symbols: list[tuple[str, str]] = []

    output = _build_output(
        args.commit,
        actual_sha,
        args.batch,
        batch_entries,
        dim_unit_map,
        closures,
        in_repo_funcs,
        module_files,
        all_helper_sources,
        all_const_defs,
        not_found_symbols,
    )

    # 写入产物
    output_dir = REPO_ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"descriptor_sources_batch{args.batch}_J1.md"
    output_path.write_text(output, encoding="utf-8")

    print(f"产物已写入: {output_path}")
    print(f"  本批 {len(batch_entries)} 条描述符")

    if not_found_symbols:
        print(f"  警告: {len(not_found_symbols)} 个 implementation_symbol 未找到定义位置")

    return 0


if __name__ == "__main__":
    sys.exit(main())
