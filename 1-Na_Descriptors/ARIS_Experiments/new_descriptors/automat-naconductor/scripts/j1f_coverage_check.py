"""J1f 覆盖自检脚本（入库，非临时文件）。"""
import sys, io, ast, yaml
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

# 1. registry 名单 vs 产物名单 差集
registry = yaml.safe_load(Path("descriptor_registry.yaml").read_text(encoding="utf-8"))
registry_names = set(e["name"] for e in registry["descriptors"])

product_names = set()
for i in range(1, 5):
    text = Path(f"reports/descriptor_sources_batch{i}_J1.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("## 附录") and not line.startswith("### "):
            name = line[3:].strip()
            if name and not name.startswith("#"):
                product_names.add(name)

only_registry = registry_names - product_names
only_product = product_names - registry_names
print(f"registry 名单条数: {len(registry_names)}")
print(f"产物名单条数: {len(product_names)}")
print(f"registry - 产物: {sorted(only_registry) if only_registry else '(empty)'}")
print(f"产物 - registry: {sorted(only_product) if only_product else '(empty)'}")

# 2. 附录 helper 去重并集 vs helper_closure 全库闭包并集
from descriptors.registry import compute_helper_closures
closures = compute_helper_closures(registry, Path("descriptors"))

module_files = sorted({e["module"] for e in registry["descriptors"]})
module_files.insert(0, "_base.py")
in_repo_funcs = {}
for mod_file in module_files:
    source = Path(f"descriptors/{mod_file}").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name not in in_repo_funcs:
                in_repo_funcs[node.name] = mod_file

expected_helpers = set()
for name, closure in closures.items():
    for h in closure:
        if h in in_repo_funcs:
            expected_helpers.add(h)

found_helpers = set()
for i in range(1, 5):
    text = Path(f"reports/descriptor_sources_batch{i}_J1.md").read_text(encoding="utf-8")
    in_appendix_a = False
    for line in text.splitlines():
        if line.strip().startswith("### A. helper"):
            in_appendix_a = True
            continue
        if in_appendix_a and line.strip().startswith("### B."):
            break
        if in_appendix_a and line.startswith("#### `"):
            name = line.split("`")[1]
            found_helpers.add(name)

print()
print(f"附录 helper 去重条数: {len(found_helpers)}")
print(f"闭包仓内 helper 去重条数: {len(expected_helpers)}")
diff = found_helpers.symmetric_difference(expected_helpers)
print(f"对称差集: {sorted(diff) if diff else '(empty)'}")

# 3. 未找到的 implementation_symbol
not_found = []
for i in range(1, 5):
    text = Path(f"reports/descriptor_sources_batch{i}_J1.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if "未找到定义" in line:
            not_found.append(line.strip())
print()
print(f"未找到定义的 symbol: {not_found if not_found else '(none)'}")
