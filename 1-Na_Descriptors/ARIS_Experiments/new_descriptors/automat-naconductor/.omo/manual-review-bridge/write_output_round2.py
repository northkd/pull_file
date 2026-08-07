"""写入第 2 轮 research-review 回复到所有标准输出文件。"""
import json
import pathlib
from datetime import datetime, timezone, timedelta

project_root = pathlib.Path(
    r"E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main"
    r"\experiments\02_组合描述符搜索\automat-naconductor"
)

tz = timezone(timedelta(hours=8))
now = datetime.now(tz)
date_str = now.strftime("%Y-%m-%d")
ts = now.isoformat(timespec="seconds")

# 第 2 轮回复全文从单独文件读取
response_file = project_root / ".omo" / "manual-review-bridge" / "round2_response_full.md"
response_text = response_file.read_text(encoding="utf-8")
print(f"Response length: {len(response_text)} chars")

# 1. 保存 response 追踪
trace_dir = project_root / ".aris" / "traces" / "research-review" / "2026-08-07_run01"
trace_dir.mkdir(parents=True, exist_ok=True)
(trace_dir / "002-research-review.response.md").write_text(response_text, encoding="utf-8")
print(f"Response trace saved")

# 2. 读取现有 RESEARCH_REVIEW.md，追加 Round 2
review_md = project_root / "RESEARCH_REVIEW.md"
existing = review_md.read_text(encoding="utf-8")

round2_section = f"""

## Round 2: 修复路线图 + 架构草图

**追问主题**：基于第 1 轮的 15 步骤评估 + 9 条跨步骤问题 + Top 3 建议，请求修复路线图和修复后管线架构。

{response_text}
"""

review_md.write_text(existing + round2_section, encoding="utf-8")
print(f"RESEARCH_REVIEW.md updated ({len(existing + round2_section)} chars total)")

# 3. 更新 RESEARCH_REVIEW.json
review_json = project_root / "RESEARCH_REVIEW.json"
existing_json = json.loads(review_json.read_text(encoding="utf-8"))

existing_json["rounds"].append({
    "round": 2,
    "purpose": "fix-roadmap-and-architecture",
    "prompt_summary": "请求修复路线图（24项,含阻塞性/工作量/数字方向/数据依赖）+ 修复后管线架构（Mermaid流程图+估计量绑定表+对照体系）",
    "prompt_path": ".omo/manual-review-bridge/prompt_research-review_round2.md",
    "response_path": "RESEARCH_REVIEW.md#round-2",
    "trace_path": ".aris/traces/research-review/2026-08-07_run01/",
    "response_length_chars": len(response_text),
    "deliverables": [
        "24-item fix roadmap across 6 waves (W0-W5)",
        "7-item minimum viable fix set (MVP)",
        "Post-fix pipeline architecture (3 Mermaid diagrams)",
        "Estimand-to-column-name binding table (16 columns)",
        "Control arm matching checklist (4 control arms)",
        "Diff annotation: keep/modify/new/delete"
    ],
    "mvp_items": [
        "W0-2: Delete list (remove 6 estimand-less numbers)",
        "W0-3: Estimand naming schema binding",
        "W0-4: NaN discipline (no favorable defaults)",
        "W1-1: alpha=0 projection replaces Ridge shrinkage",
        "W2-1: Pure function refactoring (the only L)",
        "W3-1: Outer maxT permutation loop",
        "W3-5: Incremental validity gate for combinations"
    ],
    "wave_structure": {
        "W0": "Freeze foundation (4 items, all pre-data, 2 blocking)",
        "W1": "Adjustment layer correctness (5 items, parallel with W0)",
        "W2": "Pure function refactoring (1 item, the only L, blocking for W3/W5)",
        "W3": "Null distribution and controls (6 items, Top 3 main body)",
        "W4": "Evidence block estimand alignment (6 items, fully parallel)",
        "W5": "Selection uncertainty ceiling (2 items, last)"
    },
    "key_insight": "Data not yet ready = rare window to freeze all thresholds before seeing results. Once data arrives, any threshold set post-hoc permanently loses credibility (run01 F failure mode).",
    "critical_path": "W2-1 (L) determines total timeline; all W3/W5 items depend on it",
    "number_direction": "23 of 24 items predict weaker headline numbers; 1 item (W4-6 stability lambda path) may strengthen frequency but exposes true error rate"
})

existing_json["final_consensus"] = {
    "core_claims": [
        "Current pipeline has 3 design-level problems: estimand identity crisis, shrinkage-where-projection-needed, mismatched control arms",
        "24 fix items across 6 waves; 7 items form minimum viable fix set",
        "Pure function refactoring (W2-1) is the sole L and the critical path bottleneck",
        "All thresholds must be frozen before data arrives (irreversible credibility window)"
    ],
    "evidence_requirements": [
        "Outer maxT permutation (W3-1) is the only tool that can validate the headline max statistic",
        "Shadow columns must walk identical Stage 1 path as real descriptors (W3-2)",
        "random-k / bottom-k control validation set (W3-6) is cheapest supporting evidence available"
    ],
    "experiment_plan": [
        "Wave 0+1: can start immediately, all pre-data, ~1 week",
        "Wave 2: the L item, ~1-2 weeks, blocks Wave 3 and 5",
        "Wave 3+4: parallel during/after W2-1, ~1 week each",
        "Wave 5: last, ~0.5 week"
    ],
    "narrative_structure": "Post-fix claims are weaker but defensible: 'descriptor X shows within-system monotonic association at maxT percentile Y, with BCa interval Z (excluding selection uncertainty)'"
}

existing_json["timestamp"] = ts

review_json.write_text(json.dumps(existing_json, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"RESEARCH_REVIEW.json updated")

# 4. 更新 run.meta.json
meta_path = trace_dir / "run.meta.json"
meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
meta_data["rounds"] = meta_data.get("rounds", [])
meta_data["rounds"].append({
    "round": 2,
    "purpose": "fix-roadmap-and-architecture",
    "prompt_chars": 1194,
    "response_chars": len(response_text),
    "timestamp": ts
})
meta_path.write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"run.meta.json updated")
print("\n=== Round 2 output files written successfully ===")
