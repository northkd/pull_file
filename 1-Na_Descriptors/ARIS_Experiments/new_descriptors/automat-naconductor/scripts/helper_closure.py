"""D6: 用 ast 对每个注册的 compute_* 求 helper 调用的传递闭包。

输出两份产物：
1. per-descriptor 的 helper 列表（传递闭包）
2. 每个 helper 的依赖者计数表

闭包计算逻辑已统一到 descriptors/registry.py:compute_helper_closures，
本脚本只做 I/O 与格式化输出，不持有独立 AST 实现。

用法:
    python scripts/helper_closure.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DESCRIPTORS_DIR = REPO_ROOT / "descriptors"
REGISTRY_PATH = REPO_ROOT / "descriptor_registry.yaml"

sys.path.insert(0, str(REPO_ROOT))
from descriptors.registry import compute_helper_closures  # noqa: E402


def _load_registry() -> dict:
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    return data


def main() -> int:
    registry = _load_registry()

    # 闭包计算委托给 registry.py 的唯一实现
    per_descriptor = compute_helper_closures(registry, DESCRIPTORS_DIR)

    # 反向索引：helper → dependents
    helper_dependents: dict[str, list[str]] = defaultdict(list)
    for name, helpers in per_descriptor.items():
        for h in helpers:
            helper_dependents[h].append(name)

    # 输出 per-descriptor
    print("=" * 70)
    print("Per-descriptor helper closure (transitive):")
    print("=" * 70)
    for name in sorted(per_descriptor):
        helpers = per_descriptor[name]
        print(f"  {name}: {helpers if helpers else '[]'}")

    # 输出 helper → dependents count
    print()
    print("=" * 70)
    print("Helper → dependents count:")
    print("=" * 70)
    for helper in sorted(helper_dependents):
        deps = helper_dependents[helper]
        print(f"  {helper}: {len(deps)} dependents → {sorted(deps)}")

    # 写 JSON 产物
    output_path = REPO_ROOT / "scripts" / "helper_closure_output.json"
    output_path.write_text(
        json.dumps(
            {"per_descriptor": per_descriptor, "helper_dependents": dict(helper_dependents)},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nJSON 产物已写入: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
