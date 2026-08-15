"""G0a: impl_return_exprs / impl_literals 的格式类/实质类分类。

对每个注册 compute_*，机器抽取 return 表达式与数值字面量，与 YAML 对比：
- 格式类 = 归一化引号+排序后表达式集合相同（差异来自行号漂移/遍历顺序/引号/空白）
- 实质类 = 表达式本身不同、或 YAML 记录的字面量在代码中不存在

本脚本是 F0a 分类分析的正式入库版本（上一轮用临时脚本 `_tmp_f0a_classify.py`
执行后删除，违反"任何为本轮分析写的脚本一律入库"，故恢复为正式脚本）。

H3: 支持 `--yaml-from-commit <commit>`，用 `git show <commit>:descriptor_registry.yaml`
取 YAML 快照（只读，不落盘到工作区），对旧提交的 impl_* 手工值重跑分类，复现 F0a。

输出: 41 条逐条对照 + 两类的条数与逐条名单。

用法:
    python scripts/impl_facts_classify.py
    python scripts/impl_facts_classify.py --yaml-from-commit <commit>
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DESCRIPTORS_DIR = REPO_ROOT / "descriptors"
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"


def _load_registry(yaml_text: str | None = None):
    if yaml_text is None:
        raw = REGISTRY_PATH.read_text(encoding="utf-8")
    else:
        raw = yaml_text
    return yaml.safe_load(raw)["descriptors"]


def git_show_registry_from_commit(commit: str) -> str:
    """只读取 `git show <commit>:descriptor_registry.yaml` 的原文快照，不落盘到工作区。"""
    proc = subprocess.run(
        ["git", "show", f"{commit}:descriptor_registry.yaml"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"git show {commit}:descriptor_registry.yaml 失败: {proc.stderr.strip()}")
    return proc.stdout


def git_show_source_from_commit(commit: str, rel_path: str) -> str:
    """读取 `git show <commit>:<rel_path>` 的源码快照，不落盘到工作区。"""
    proc = subprocess.run(
        ["git", "show", f"{commit}:{rel_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"git show {commit}:{rel_path} 失败: {proc.stderr.strip()}")
    return proc.stdout


def _parse_module(name, source_commit=None):
    if source_commit:
        src = git_show_source_from_commit(source_commit, f"descriptors/{name}")
    else:
        path = DESCRIPTORS_DIR / name
        src = path.read_text(encoding="utf-8")
    return ast.parse(src), src


def _get_funcs(mod_ast):
    return {n.name: n for n in mod_ast.body if isinstance(n, ast.FunctionDef)}


def _extract_returns(func_node, source):
    out = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Return):
            seg = ast.get_source_segment(source, node)
            if seg is None:
                seg = ast.unparse(node)
            out.append((seg.strip(), node.lineno))
    out.sort(key=lambda x: x[1])
    return out


def _extract_literals(func_node):
    out = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Constant):
            v = node.value
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                out.append((v, node.lineno))
    out.sort(key=lambda x: x[1])
    return out


def _norm_quote(s):
    """归一化引号风格：单引号→双引号，便于比较表达式本身。"""
    return s.replace("'", '"')


def _parse_yaml_return(item):
    m = re.match(r"^(.*?)\s*\(L(\d+)\)$", item.strip())
    if m:
        return m.group(1).strip(), int(m.group(2))
    return item.strip(), None


def _parse_yaml_literal(item):
    m = re.match(r"^(.*?)\s*\(L([\d,\-]+).*?\)$", item.strip())
    if m:
        return m.group(1).strip(), m.group(2)
    return item.strip(), None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="impl_return_exprs / impl_literals 格式/实质分类")
    parser.add_argument(
        "--yaml-from-commit",
        dest="yaml_commit",
        default=None,
        help="用 `git show <commit>:descriptor_registry.yaml` 的快照做 YAML 侧，复现 F0a",
    )
    parser.add_argument(
        "--source-from-commit",
        dest="source_commit",
        default=None,
        help="用 `git show <commit>:descriptors/<path>` 的快照做源码侧（K4 新增）",
    )
    args = parser.parse_args(argv)

    if args.yaml_commit is not None:
        yaml_text = git_show_registry_from_commit(args.yaml_commit)
        registry = _load_registry(yaml_text)
        print(f"# YAML 来源: git show {args.yaml_commit}:descriptor_registry.yaml（只读快照）")
    else:
        registry = _load_registry()
        print("# YAML 来源: 工作区 descriptor_registry.yaml")

    if args.source_commit is not None:
        print(f"# 源码来源: git show {args.source_commit}:descriptors/*（只读快照）")

    mod_asts = {}
    mod_srcs = {}
    mod_funcs = {}
    for e in registry:
        m = e["module"]
        if m not in mod_asts:
            mod_asts[m], mod_srcs[m] = _parse_module(m, args.source_commit)
            mod_funcs[m] = _get_funcs(mod_asts[m])
    if args.source_commit:
        bs = git_show_source_from_commit(args.source_commit, "descriptors/_base.py")
    else:
        bp = DESCRIPTORS_DIR / "_base.py"
        if bp.exists():
            bs = bp.read_text(encoding="utf-8")
        else:
            bs = ""
    if bs:
        mod_asts["_base.py"] = ast.parse(bs)
        mod_srcs["_base.py"] = bs
        mod_funcs["_base.py"] = _get_funcs(mod_asts["_base.py"])

    return_format = []
    return_substantive = []
    lit_format = []
    lit_substantive = []

    for e in registry:
        name = e["name"]
        sym = e["implementation_symbol"]
        mod = e["module"]
        fm = mod_funcs.get(mod, {})
        if sym not in fm:
            fm = {**fm, **mod_funcs.get("_base.py", {})}
        src = mod_srcs.get(mod, "")
        fn = fm.get(sym)
        if fn is None:
            print(f"=== {name} === 警告: 符号 {sym} 未找到")
            continue

        machine_returns = _extract_returns(fn, src)
        machine_lits = _extract_literals(fn)

        yaml_returns = [_parse_yaml_return(x) for x in e.get("impl_return_exprs", [])]
        yaml_lits = [_parse_yaml_literal(x) for x in e.get("impl_literals", [])]

        print(f"=== {name} ({sym}) ===")

        # --- return_exprs ---
        y_srcs = [r[0] for r in yaml_returns]
        m_srcs = [r[0] for r in machine_returns]
        y_lines = [r[1] for r in yaml_returns]
        m_lines = [r[1] for r in machine_returns]

        y_srcs_nq = [_norm_quote(s) for s in y_srcs]
        m_srcs_nq = [_norm_quote(s) for s in m_srcs]

        y_srcs_sorted = sorted(y_srcs_nq)
        m_srcs_sorted = sorted(m_srcs_nq)

        match = (y_srcs == m_srcs and y_lines == m_lines)
        if match:
            print(f"  return_exprs: 一致 ({len(machine_returns)} 条)")
        else:
            if y_srcs_sorted == m_srcs_sorted:
                cat = "格式类"
                return_format.append(name)
            else:
                cat = "实质类"
                return_substantive.append(name)
            print(f"  return_exprs: 不一致 [{cat}]")
            print(f"    YAML  ({len(yaml_returns)}): {yaml_returns}")
            print(f"    机器  ({len(machine_returns)}): {[(s, l) for s, l in machine_returns]}")

        # --- literals ---
        y_lit_lines = [l[1] for l in yaml_lits]
        m_lit_lines = [str(l[1]) for l in machine_lits]

        lit_match = (len(yaml_lits) == len(machine_lits) and y_lit_lines == m_lit_lines)
        if lit_match:
            print(f"  literals: 一致 ({len(machine_lits)} 条)")
        else:
            y_vals = set()
            for yv, _ in yaml_lits:
                for tok in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', yv):
                    try:
                        y_vals.add(float(tok))
                    except ValueError:
                        pass
            m_vals = set(float(v) for v, _ in machine_lits)

            y_in_m = y_vals.issubset(m_vals) if y_vals else True
            if y_in_m:
                cat = "格式类"
                lit_format.append(name)
            else:
                cat = "实质类"
                lit_substantive.append(name)
            print(f"  literals: 不一致 [{cat}]")
            print(f"    YAML  ({len(yaml_lits)}): {yaml_lits}")
            print(f"    机器  ({len(machine_lits)}): {[(str(v), l) for v, l in machine_lits]}")

        print()

    print("=" * 70)
    print("return_exprs 分类汇总:")
    print(f"  格式类: {len(return_format)} 条 → {return_format}")
    print(f"  实质类: {len(return_substantive)} 条 → {return_substantive}")
    print()
    print("literals 分类汇总:")
    print(f"  格式类: {len(lit_format)} 条 → {lit_format}")
    print(f"  实质类: {len(lit_substantive)} 条 → {lit_substantive}")
    return 0


if __name__ == "__main__":
    sys.exit(main())