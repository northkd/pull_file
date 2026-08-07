"""将 Claude 的 research-review 回复写入标准输出文件。
生成 RESEARCH_REVIEW.md 和 RESEARCH_REVIEW.json。
"""
import json
import pathlib
from datetime import datetime, timezone, timedelta

project_root = pathlib.Path(
    r"E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main"
    r"\experiments\02_组合描述符搜索\automat-naconductor"
)

# 读取 Claude 回复（用户粘贴的全文已保存在这个变量里）
# 由于回复很长，我们直接内联
response_text = pathlib.Path(project_root / ".omo" / "manual-review-bridge" / "claude_response_round1.md").read_text(encoding="utf-8") if (project_root / ".omo" / "manual-review-bridge" / "claude_response_round1.md").exists() else ""

# 时区
tz_shanghai = timezone(timedelta(hours=8))
now = datetime.now(tz_shanghai)
date_str = now.strftime("%Y-%m-%d")
timestamp_iso = now.isoformat()

print(f"Date: {date_str}")
print(f"Timestamp: {timestamp_iso}")
print(f"Response length: {len(response_text)} chars")
