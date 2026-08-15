"""K2: 极性证据取样——supercell 与 isotropic_scale 全表。"""
import sys, io, math, ast, yaml
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

df = pd.read_csv("scripts/registry_invariance_report.csv")

# 从 __init__.py 读 dimension
init_src = Path("descriptors/__init__.py").read_text(encoding="utf-8")
tree = ast.parse(init_src)
for node in ast.iter_child_nodes(tree):
    is_target = False
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "_DESCRIPTOR_UNITS_AND_DIMENSIONS":
        is_target = True
    if is_target and node.value is not None:
        dim_unit = ast.literal_eval(node.value)

# supercell n=2 (make_supercell([2,1,1]))
N_SUPERCELL = 2
# isotropic_scale s=1.05
S_SCALE = 1.05

# dimension → expected power for isotropic_scale
DIM_TO_POWER = {
    "length": 1, "volume": 3, "dimensionless": 0, "count": 0,
    "number_density": -3, "angle": 0, "energy": 0,
    "electronegativity": 0, "charge": 0, "electron_count": 0,
    "categorical_index": 0,
}

# ============================================================
# K2(b): supercell 全表
# ============================================================
print("=" * 80)
print("K2(b): supercell 全表 (n=2, make_supercell([2,1,1]))")
print("=" * 80)
print(f"{'descriptor':<35} {'verdict':<15} {'ratio':<12} {'dim':<20}")
print("-" * 82)

supercell_df = df[df["transform"] == "supercell"]
# 取第一个非 NaN 的 ratio 和 verdict（每个描述符在 5 个结构上各有一行，取有 ratio 的那行）
group_a = []  # ratio ≈ n
group_b = []  # ratio ≈ 1
group_c = []  # neither

for desc in sorted(supercell_df["descriptor"].unique()):
    sub = supercell_df[supercell_df["descriptor"] == desc]
    # 取第一个有 ratio 的行
    ratio_val = None
    verdict_val = None
    for _, row in sub.iterrows():
        r = row["ratio"]
        if pd.notna(r) and r != "n/a":
            try:
                ratio_val = float(r)
                verdict_val = row["verdict"]
                break
            except:
                pass
    if ratio_val is None:
        # 取 verdict
        verdict_val = sub.iloc[0]["verdict"]
        ratio_str = "n/a"
    else:
        ratio_str = f"{ratio_val:.6g}"

    dim = dim_unit.get(desc, ("?", "?"))[1]
    print(f"{desc:<35} {verdict_val:<15} {ratio_str:<12} {dim:<20}")

    if ratio_val is not None:
        if abs(ratio_val - N_SUPERCELL) / N_SUPERCELL <= 1e-6:
            group_a.append(desc)
        elif abs(ratio_val - 1.0) <= 1e-6:
            group_b.append(desc)
        else:
            group_c.append(desc)
    else:
        group_c.append(desc)  # NaN ratios go to group C

print()
print(f"组 A (ratio ≈ n={N_SUPERCELL}): {group_a}")
print(f"组 B (ratio ≈ 1): {group_b}")
print(f"组 C (两者都不是): {group_c}")

# ============================================================
# K2(c): isotropic_scale 全表
# ============================================================
print()
print("=" * 80)
print(f"K2(c): isotropic_scale 全表 (s={S_SCALE})")
print("=" * 80)
print(f"{'descriptor':<35} {'verdict':<15} {'ratio':<10} {'k_inferred':<12} {'dim':<20} {'k_declared':<12} {'match':<6}")
print("-" * 110)

iso_df = df[df["transform"] == "isotropic_scale"]
mismatch_list = []
k2d_known = ["na_concentration", "framework_bond_rigidity", "target_bond_center"]

for desc in sorted(iso_df["descriptor"].unique()):
    sub = iso_df[iso_df["descriptor"] == desc]
    ratio_val = None
    verdict_val = None
    for _, row in sub.iterrows():
        r = row["ratio"]
        if pd.notna(r) and r != "n/a":
            try:
                ratio_val = float(r)
                verdict_val = row["verdict"]
                break
            except:
                pass
    if ratio_val is None:
        verdict_val = sub.iloc[0]["verdict"]
        ratio_str = "n/a"
        k_inferred = "n/a"
    else:
        ratio_str = f"{ratio_val:.6g}"
        if abs(ratio_val - 1.0) <= 1e-6:
            k_inferred = 0
        elif ratio_val > 0:
            k_inferred = math.log(ratio_val) / math.log(S_SCALE)
        else:
            k_inferred = "n/a"

    dim = dim_unit.get(desc, ("?", "?"))[1]
    k_declared = DIM_TO_POWER.get(dim, "?")

    if isinstance(k_inferred, (int, float)) and isinstance(k_declared, int):
        match = "yes" if abs(k_inferred - k_declared) <= 1e-6 else "NO"
    else:
        match = "?"

    marker = " ← K2(d)" if desc in k2d_known else ""
    print(f"{desc:<35} {verdict_val:<15} {ratio_str:<10} {str(k_inferred):<12} {dim:<20} {str(k_declared):<12} {match:<6}{marker}")

    if match == "NO":
        mismatch_list.append(desc)

print()
print(f"反推 k 与声明幂次不符的描述符: {mismatch_list}")
print(f"K2(d) 三条已知不符:")
for d in k2d_known:
    print(f"  {d}: 在不符名单中 = {d in mismatch_list}")
