"""K7(e): 统计受闭包截断影响的描述符条数。"""
import sys, io, ast, yaml
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

sys.path.insert(0, ".")
from descriptors.registry import compute_helper_closures, _get_all_functions, _get_called_names

registry = yaml.safe_load(Path("descriptor_registry.yaml").read_text(encoding="utf-8"))
closures = compute_helper_closures(registry, Path("descriptors"))

# Build a correct func_map that ALWAYS includes _base.py
descriptors_dir = Path("descriptors")
module_functions = {}
for entry in registry["descriptors"]:
    mod = entry["module"]
    if mod not in module_functions:
        path = descriptors_dir / mod
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_functions[mod] = _get_all_functions(tree)

base_path = descriptors_dir / "_base.py"
base_ast = ast.parse(base_path.read_text(encoding="utf-8"), filename=str(base_path)
)
module_functions["_base.py"] = _get_all_functions(base_ast)

# Correct closure: always merge _base.py
from descriptors.registry import _compute_transitive_closure

missing_funcs = {"_anion_cutoff", "_major_species", "site_occupancies_by_symbol"}
affected = []
for entry in registry["descriptors"]:
    name = entry["name"]
    symbol = entry["implementation_symbol"]
    mod = entry["module"]
    # Current (buggy) closure
    current = set(closures.get(name, []))
    # Correct closure: always include _base.py
    correct_func_map = {**module_functions.get(mod, {}), **module_functions.get("_base.py", {})}
    correct = _compute_transitive_closure(symbol, correct_func_map)
    correct.discard(symbol)
    
    missing_from_current = correct - current
    extra_in_current = current - correct  # should be empty
    
    if missing_from_current:
        affected.append((name, sorted(missing_from_current)))

print(f"受影响描述符条数: {len(affected)} / 41")
print()
for name, missing in affected:
    print(f"  {name}: 缺失 {missing}")
