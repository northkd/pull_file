"""K2(f): verify dimension_mismatch is a dead verdict."""
import sys, io, yaml
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

registry = yaml.safe_load(Path("descriptor_registry.yaml").read_text(encoding="utf-8"))
found = False
for e in registry["descriptors"]:
    for d in e.get("known_invariance_defects", []):
        if "dimension_mismatch" in str(d):
            name = e["name"]
            print(f"Found dimension_mismatch in {name}: {d}")
            found = True
if not found:
    print("dimension_mismatch: not found in any known_invariance_defects")

df = pd.read_csv("scripts/registry_invariance_report.csv")
dm = df[df["verdict"] == "dimension_mismatch"]
print(f"dimension_mismatch in CSV verdict column: {len(dm)} rows")

dc = df[df["dimension_declaration_conflict"] == "true"]
print(f"dimension_declaration_conflict=true in CSV: {len(dc)} rows")
for _, row in dc.iterrows():
    desc = row["descriptor"]
    tr = row["transform"]
    st = row["structure"]
    print(f"  {desc} / {tr} / {st}")
