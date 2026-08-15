"""K7(c): 直接调用 compute_helper_closures 打印 compute_a2_max_dist 的闭包全集。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import yaml
from pathlib import Path
from descriptors.registry import compute_helper_closures

registry = yaml.safe_load(Path("descriptor_registry.yaml").read_text(encoding="utf-8"))
closures = compute_helper_closures(registry, Path("descriptors"))

closure_a2 = closures.get("a2_max_dist", [])
print(f"compute_a2_max_dist 闭包 ({len(closure_a2)} 条):")
for name in closure_a2:
    print(f"  {name}")

print()
# Check if the three missing functions are present
missing = ["_anion_cutoff", "_major_species", "site_occupancies_by_symbol"]
for m in missing:
    present = m in closure_a2
    print(f"  {m} in closure: {present}")

# Also show what _shell_neighbors and get_na_sites call
print()
print("--- Manual recursion check ---")
import ast
base_src = Path("descriptors/_base.py").read_text(encoding="utf-8")
base_tree = ast.parse(base_src)
base_funcs = {n.name: n for n in base_tree.body if isinstance(n, ast.FunctionDef)}

for fname in ["_shell_neighbors", "get_na_sites"]:
    if fname in base_funcs:
        called = set()
        for node in ast.walk(base_funcs[fname]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called.add(node.func.id)
        print(f"  {fname} directly calls: {sorted(called)}")
