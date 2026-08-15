"""G4: registry 机器字段一键重算（shared_intermediates + impl_* + known_invariance_defects）。

任何修改 descriptors/ 下源码的提交，必须在**同一个提交内**跑本脚本并纳入 YAML
变更（见 REGISTRY_FIELD_DOMAINS.md 的 G4 规则）；禁止事后 --amend 到别的提交上。

本脚本串行执行三个重算：
  1. known_invariance_defects   ← fill_invariance_field.compute_defects_from_report
  2. impl_return_exprs/literals/guards ← impl_facts_audit 提取
  3. shared_intermediates        ← compute_helper_closures

用 ruamel round-trip 保留其他字段格式。

用法:
    python scripts/registry_refresh.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"
DESCRIPTORS_DIR = REPO_ROOT / "descriptors"
REPORT_PATH = REPO_ROOT / "scripts" / "registry_invariance_report.csv"

sys.path.insert(0, str(REPO_ROOT))


def _load_impl_helpers():
    """加载 scripts/impl_facts_audit.py（importlib，避免包路径依赖）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "impl_facts_audit", REPO_ROOT / "scripts" / "impl_facts_audit.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    # 1. 不变性缺陷聚合（需 CSV 存在）
    if not REPORT_PATH.exists():
        print(f"ERROR: 不变性报告不存在: {REPORT_PATH}，请先跑 descriptor_invariance_probe.py",
              file=sys.stderr)
        return 2
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from fill_invariance_field import compute_defects_from_report
    defects_by_desc = compute_defects_from_report(REPORT_PATH)

    # K6: extensivity 派生
    from fill_extensivity_field import derive_extensivity
    ext_by_desc = derive_extensivity(REPORT_PATH)

    # 2. impl_* 提取
    impl_mod = _load_impl_helpers()
    from descriptors.registry import load_registry, compute_helper_closures

    ryaml = YAML()
    ryaml.preserve_quotes = True
    ryaml.width = 4096
    data = ryaml.load(REGISTRY_PATH.read_text(encoding="utf-8"))

    # 3. shared_intermediates 闭包
    closures = compute_helper_closures(data, DESCRIPTORS_DIR)

    # 加载 impl 提取所需
    impl_reg = data.get("descriptors", [])
    mod_funcs, mod_srcs = impl_mod.get_all_module_functions(impl_reg)

    changed_si = 0
    changed_defects = 0
    changed_impl = 0
    changed_ext = 0
    for entry in data["descriptors"]:
        name = entry["name"]
        # shared_intermediates
        new_si = closures[name]
        if entry.get("shared_intermediates") != new_si:
            changed_si += 1
        entry["shared_intermediates"] = new_si

        # known_invariance_defects
        new_defects = defects_by_desc.get(name, ["none_found"])
        if entry.get("known_invariance_defects") != new_defects:
            changed_defects += 1
        entry["known_invariance_defects"] = new_defects

        # K6: extensivity
        new_ext = ext_by_desc.get(name, "undetermined")
        if entry.get("extensivity") != new_ext:
            changed_ext += 1
        entry["extensivity"] = new_ext

        # impl_*
        symbol = entry["implementation_symbol"]
        mod = entry["module"]
        fm = mod_funcs.get(mod, {})
        if symbol not in fm:
            fm = {**fm, **mod_funcs.get("_base.py", {})}
        src = mod_srcs.get(mod, "")
        fn = fm.get(symbol)
        if fn is None:
            print(f"WARNING: {name} 符号 {symbol} 未找到，跳过 impl_*")
            continue
        new_returns = [f"{s} (L{l})" for s, l in impl_mod.extract_return_exprs(fn, src)]
        new_literals = [f"{v} (L{l})" for v, l in impl_mod.extract_literals(fn)]
        new_guards = [f"{c} (L{l})" for c, l in impl_mod.extract_guards(fn, src)]
        if (entry.get("impl_return_exprs") != new_returns
                or entry.get("impl_literals") != new_literals
                or entry.get("impl_guards") != new_guards):
            changed_impl += 1
        entry["impl_return_exprs"] = new_returns
        entry["impl_literals"] = new_literals
        entry["impl_guards"] = new_guards

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        ryaml.dump(data, f)

    print(f"共 {len(data['descriptors'])} 条")
    print(f"  shared_intermediates 更新: {changed_si}")
    print(f"  known_invariance_defects 更新: {changed_defects}")
    print(f"  extensivity 更新: {changed_ext}")
    print(f"  impl_return_exprs/literals/guards 更新: {changed_impl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())