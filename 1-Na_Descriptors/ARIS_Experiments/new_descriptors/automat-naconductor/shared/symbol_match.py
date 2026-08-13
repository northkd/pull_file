"""符号定义位置匹配器。

从 .omo/manual-review-bridge/build_prompt.py 和 descriptors/registry.py 中
提取的共享实现，两处都 import 此模块，不保留独立副本。

匹配逻辑：对带点符号取末段，整词用 re.escape 加 \\b 边界，
以多行模式命中 def / class / 模块级赋值 之一即视为存在。
"""
from __future__ import annotations

import re


def symbol_has_definition(symbol: str, body: str) -> bool:
    """检查符号是否在源码正文中存在定义位置。

    对带点符号取末段（如 ``SomeClass.run`` -> ``run``），对不带点符号取整串。
    整词用 re.escape 加 \\b 边界，以多行模式命中下列任一模式即视为存在——
      ^\\s*(?:async\\s+)?def\\s+NAME\\b
      ^\\s*class\\s+NAME\\b
      ^\\s*NAME\\s*[:=]
    """
    name = symbol.rsplit(".", 1)[-1]
    name_b = r"\b" + re.escape(name) + r"\b"
    patterns = (
        rf"^\s*(?:async\s+)?def\s+{name_b}",
        rf"^\s*class\s+{name_b}",
        rf"^\s*{name_b}\s*[:=]",
    )
    return any(re.search(p, body, re.MULTILINE) for p in patterns)
