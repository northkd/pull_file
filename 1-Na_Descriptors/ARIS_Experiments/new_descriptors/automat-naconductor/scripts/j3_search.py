"""J3: W4-5 删除授权补检索脚本（入库，非临时文件）。"""
import sys, io, os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

keywords = [
    "W4-5", "W0-2", "W5-1", "嵌套 LOSO", "并入", "三条修正",
    "修正 1", "恒等操作", "不可实现",
]

for root, dirs, files in os.walk("."):
    if ".git" in root:
        continue
    for fn in files:
        if not (fn.endswith(".md") or fn.endswith(".py") or fn.endswith(".yaml") or fn.endswith(".json")):
            continue
        fp = os.path.join(root, fn)
        try:
            text = Path(fp).read_text(encoding="utf-8")
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines, start=1):
            for kw in keywords:
                if kw in line:
                    print(f"{fp}:{i}: [{kw}] {line.strip()[:200]}")
