"""闸门函数 _assert_steps_match_sources 的单元测试。

build_prompt.py 是一个纯顶层执行的脚本（无 main()/if __name__），直接
import 会触发顶层代码（包括闸门对当前过期 algorithm_steps 的检查并抛错）。
因此测试用 ast 从源码中提取 _assert_steps_match_sources 的定义，exec 到
独立命名空间后调用——测试的就是真实源码里的那个函数，不复制实现、不依赖
脚本当前是否处于"清单已更新"状态（因为闸门对 7 个嵌入源的检查依赖运行时
传入的 embedded_sources，与测试构造的字典相互独立）。
"""
import ast
import pathlib
import re
import sys

import pytest

# _symbol_has_definition 现在从 shared/symbol_match.py 导入，不再在 build_prompt.py 中定义。
# 测试通过 AST 提取 build_prompt.py 的函数后，需预注入该函数到命名空间。
_repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
from shared.symbol_match import symbol_has_definition as _imported_symbol_has_definition

BUILD_PROMPT_PATH = pathlib.Path(__file__).with_name("build_prompt.py")

FLAT_SOURCE = {
    "src.py": (
        # 两个符号都存在于正文
        "def alpha() -> float: return 1.0\n"
        "def beta() -> float: return 2.0\n"
    ),
}

FLAT_DOTTED_SOURCE = {
    "src.py": (
        # CombinationValidator._noise_baseline 整串存在，且其最后一段 _noise_baseline 也在
        "class CombinationValidator:\n"
        "    def _noise_baseline(self): pass\n"
    ),
}


def _load_gate_function(steps_text: str, embedded_sources: dict[str, str]) -> "callable":
    """从 build_prompt.py 源码提取 _assert_steps_match_sources 并调用。"""
    tree = ast.parse(BUILD_PROMPT_PATH.read_text(encoding="utf-8"))
    needed = {"_assert_steps_match_sources"}
    func_nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in needed
    ]
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == "_assert_steps_match_sources"
        for n in func_nodes
    ), "build_prompt.py 中未找到 _assert_steps_match_sources 定义"

    # _symbol_has_definition 从 shared 导入，预注入到命名空间
    ns: dict = {"re": re, "_symbol_has_definition": _imported_symbol_has_definition}
    module = ast.Module(body=func_nodes, type_ignores=[])
    exec(compile(module, str(BUILD_PROMPT_PATH), "exec"), ns)
    return ns["_assert_steps_match_sources"](steps_text, embedded_sources)


def _load_anchors_gate(
    run_info_dict: dict, live_py_contents: dict[str, str]
) -> None:
    """从 build_prompt.py 源码提取 _assert_anchors_resolve 并调用。"""
    tree = ast.parse(BUILD_PROMPT_PATH.read_text(encoding="utf-8"))
    needed = {"_assert_anchors_resolve"}
    func_nodes = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in needed
    ]
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == "_assert_anchors_resolve"
        for n in func_nodes
    ), "build_prompt.py 中未找到 _assert_anchors_resolve 定义"

    # _symbol_has_definition 从 shared 导入，预注入到命名空间
    ns: dict = {"re": re, "_symbol_has_definition": _imported_symbol_has_definition}
    module = ast.Module(body=func_nodes, type_ignores=[])
    exec(compile(module, str(BUILD_PROMPT_PATH), "exec"), ns)
    return ns["_assert_anchors_resolve"](run_info_dict, live_py_contents)


# ---------------------------------------------------------------------------
# 正例：steps_text 中的符号都能在 embedded_sources 里找到 -> 不抛异常
# ---------------------------------------------------------------------------

def test_all_symbols_present_does_not_raise() -> None:
    steps = (
        "## 步骤 alpha\n"
        "调用 `alpha` 完成目标。\n"
        "## 步骤 beta\n"
        "调用 `beta` 完成目标。\n"
    )
    # 不应抛异常
    _load_gate_function(steps, FLAT_SOURCE)


def test_dotted_symbol_full_string_or_last_segment_matches() -> None:
    # 整串 CombinationValidator._noise_baseline 在正文中存在
    steps = "步骤 D2: `CombinationValidator._noise_baseline`（V1）"
    _load_gate_function(steps, FLAT_DOTTED_SOURCE)

    # 整串不存在但最后一段 _noise_baseline 存在，也应通过（也允许整串匹配）
    partial = {
        "other.py": (
            "def _noise_baseline(): pass\n"
        ),
    }
    _load_gate_function(steps, partial)


def test_non_identifier_backtick_spans_are_ignored() -> None:
    # 自然语言/含空格的占位不应被当作符号，更不应触发缺失
    steps = (
        "对每个步骤（`跑 CV 验证`、`分折`）逐条给出四问。\n"
        "约束：不评估 `可发表性`。\n"
    )
    _load_gate_function(steps, FLAT_SOURCE)


# ---------------------------------------------------------------------------
# 反例：混入虚构符号 -> 抛 ValueError，且异常消息包含该符号名
# ---------------------------------------------------------------------------

def test_missing_symbol_raises_value_error() -> None:
    steps = (
        "## 步骤 alpha\n"
        "调用 `alpha`。\n"
        "## 幽灵步骤\n"
        "调用 `GhostSymbolNobodyDefines`。\n"
    )
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, FLAT_SOURCE)
    assert "GhostSymbolNobodyDefines" in str(exc.value)


def test_missing_dotted_symbol_reports_full_name_in_message() -> None:
    steps = "步骤 X: `SomeClass.missing_member`"
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, {"src.py": "def unrelated(): pass\n"})
    assert "SomeClass.missing_member" in str(exc.value)


def test_multiple_missing_symbols_all_listed() -> None:
    steps = (
        "A `one_ghost`\n"
        "B `two_ghost`\n"
        "C `three_ghost`\n"
    )
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, {"src.py": "def real(): pass\n"})
    msg = str(exc.value)
    for ghost in ("one_ghost", "two_ghost", "three_ghost"):
        assert ghost in msg


def test_error_message_includes_line_number() -> None:
    steps = (
        "line one\n"
        "line two `GhostAtLineFour`\n"
    )
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, {"src.py": "def real(): pass\n"})
    msg = str(exc.value)
    assert "GhostAtLineFour" in msg
    # 该符号出现在 steps_text 第 2 行
    assert "第 2 行" in msg


def _eval_top_level_assignments(names: list[str], extra_ns: dict | None = None) -> dict:
    """按 build_prompt.py 源码顶层出现顺序提取并求值若干指定赋值。

    预注入 pathlib 与 project_root 桩（测试只关心取值/过滤逻辑，不关心真实路径），
    外部可通过 extra_ns 补充桩变量（如 live_py_contents 依赖的 file_contents）。
    """
    tree = ast.parse(BUILD_PROMPT_PATH.read_text(encoding="utf-8"))
    ns: dict = {"pathlib": pathlib, "project_root": pathlib.Path(".")}
    ns.update(extra_ns or {})
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    module = ast.Module(body=[node], type_ignores=[])
                    exec(compile(module, str(BUILD_PROMPT_PATH), "exec"), ns)
                    break
    return {name: ns[name] for name in names if name in ns}


# ---------------------------------------------------------------------------
# 接线层回归：闸门被喂的语料必须只含活源码（.py），见 build_prompt.py 的
# live_py_contents；历史文档/配置/文档混入会让已删符号被误判为"仍然存在"。
# ---------------------------------------------------------------------------

def test_gate_receives_only_python_live_sources() -> None:
    live_sources = _eval_top_level_assignments(["LIVE_SOURCES"])["LIVE_SOURCES"]
    live_labels = [label for label, _ in live_sources]
    # LIVE_SOURCES 确实包含配置/文档条目（它们会进 file_embed，但绝不该进闸门语料）
    assert "run_info.yaml" in live_labels
    assert "program.md" in live_labels
    py_labels = [label for label, p in live_sources if p.suffix == ".py"]
    assert len(py_labels) >= 4  # deconfound / stability / combination / run_pipeline

    ns = _eval_top_level_assignments(
        ["live_py_contents"],
        {
            "file_contents": {label: "x" for label, _ in live_sources},
            "LIVE_SOURCES": live_sources,
        },
    )
    live_py = ns["live_py_contents"]
    # 传给闸门的语料键集 = LIVE_SOURCES 中仅 .py 的条目
    assert set(live_py) == set(py_labels)
    # 不含 run_info.yaml / program.md
    assert "run_info.yaml" not in live_py
    assert "program.md" not in live_py
    # 不含任何 .aris/ 历史文档
    assert not any(".aris" in label for label in live_py)

    # 接线：闸门调用点必须喂 live_py_contents，绝不喂 file_contents / CONTEXT_DOCS
    tree = ast.parse(BUILD_PROMPT_PATH.read_text(encoding="utf-8"))
    call = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_assert_steps_match_sources"
    )
    assert len(call.args) == 2
    assert isinstance(call.args[1], ast.Name)
    assert call.args[1].id == "live_py_contents"


def test_gate_would_fail_if_context_docs_included() -> None:
    # 若把 .aris/ 历史文档（内含旧代码全文）误当语料喂给闸门，被审计过的
    # 已删符号会因旧代码全文里的定义位置而被误判为"存在"、从而逃逸检查。
    # 这个用例把缺陷钉死为回归：历史文档正文对 partial_spearman 视而不见。
    steps = "步骤 A2: `partial_spearman` — 对残差求 Spearman"
    leaked_corpus = {
        ".aris/EXPERIMENT_AUDIT.md (旧代码全文)": (
            "旧版本审计正文，内含已删除的实现：\n"
            "def partial_spearman(x, y, controls):\n"
            "    return 0.0\n"
            "系统代理比计算……\n"
        ),
    }
    # 不应抛异常：partial_spearman 被历史文档误判为"存在"，闸门放行
    _load_gate_function(steps, leaked_corpus)


def test_substring_does_not_whitewash_symbol() -> None:
    # 语料里只有 not_partial_spearman = 1（相邻键名的模块级赋值），
    # 没有真正的 partial_spearman 定义位置。整词边界必须阻止 partial_spearman
    # 被 not_partial_spearman 洗白，故应判缺失并抛错。
    steps = "步骤 A2: `partial_spearman`"
    corpus = {"src.py": "not_partial_spearman = 1\n"}
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, corpus)
    assert "partial_spearman" in str(exc.value)


def test_generic_last_segment_requires_definition_site() -> None:
    # 末段 run 只作为普通词出现在注释里（"run the pipeline"），没有任何
    # def/class run 或赋值定义位置。泛化末段不得只因为在任意位置出现就判存在。
    steps = "步骤 B1: `StabilitySelector.run`"
    corpus = {"pipeline.py": "# run the pipeline in stage order\n"}
    with pytest.raises(ValueError) as exc:
        _load_gate_function(steps, corpus)
    assert "StabilitySelector.run" in str(exc.value)


# ---------------------------------------------------------------------------
# _assert_anchors_resolve：核验 run_info.yaml estimand.implementation_anchors
# ---------------------------------------------------------------------------

def test_anchors_all_resolve() -> None:
    """① 全部 anchor 解析通过时不抛异常。"""
    run_info = {
        "estimand": {
            "implementation_anchors": {
                "anchor_a": "src.py, MyClass.method_a",
                "anchor_b": "src.py, top_level_func",
                "anchor_c": "src.py, MyClass.method_b (local_var)",
            }
        }
    }
    sources = {
        "src.py": (
            "class MyClass:\n"
            "    def method_a(self): pass\n"
            "    def method_b(self): pass\n"
            "def top_level_func(): pass\n"
        )
    }
    _load_anchors_gate(run_info, sources)


def test_anchors_typo_raises() -> None:
    """② 单个 anchor 拼错时抛 ValueError，消息含 anchor 键名和符号名。"""
    run_info = {
        "estimand": {
            "implementation_anchors": {
                "anchor_good": "src.py, real_func",
                "anchor_bad": "src.py, GhostFunc",
            }
        }
    }
    sources = {"src.py": "def real_func(): pass\n"}
    with pytest.raises(ValueError) as exc:
        _load_anchors_gate(run_info, sources)
    msg = str(exc.value)
    assert "anchor_bad" in msg
    assert "GhostFunc" in msg
    # 正常的 anchor 不应出现在错误消息中
    assert "anchor_good" not in msg


def test_anchors_string_literal_still_raises() -> None:
    """③ 符号仅作为字符串字面量出现、无定义位置时仍抛错。"""
    run_info = {
        "estimand": {
            "implementation_anchors": {
                "anchor_x": "src.py, phantom_func",
            }
        }
    }
    # phantom_func 只在字符串和注释中出现，没有 def/class/赋值定义位置
    sources = {
        "src.py": (
            'name = "phantom_func"\n'
            'print("calling phantom_func")\n'
            '# phantom_func is not defined here\n'
        )
    }
    with pytest.raises(ValueError) as exc:
        _load_anchors_gate(run_info, sources)
    assert "phantom_func" in str(exc.value)


def test_anchors_parenthetical_note_not_matched() -> None:
    """anchor 值带括号注释时，括号内的局部变量名不参与定义位置匹配。"""
    run_info = {
        "estimand": {
            "implementation_anchors": {
                # (system_rho) 是 _factor_spanning 内的局部变量，
                # 不应被当作需要匹配的符号
                "anchor_a": "src.py, MyClass.real_method (system_rho)",
            }
        }
    }
    sources = {
        "src.py": (
            "class MyClass:\n"
            "    def real_method(self): pass\n"
        )
    }
    _load_anchors_gate(run_info, sources)


def test_anchors_empty_dict_does_not_raise() -> None:
    """没有 implementation_anchors 时不抛异常。"""
    _load_anchors_gate({"estimand": {}}, {"src.py": "x = 1\n"})
    _load_anchors_gate({}, {"src.py": "x = 1\n"})


# ---------------------------------------------------------------------------
# 真正 import build_prompt 模块：验证 sys.path 处理 + from shared.symbol_match import
# 保险：若 build_prompt.py 自己的 import 链坏掉，既有用例（预注入符号）仍会通过，
# 但这个用例会失败。
# ---------------------------------------------------------------------------

def test_build_prompt_imports_symbol_has_definition_from_shared() -> None:
    """真正 import build_prompt 模块（不注入任何符号），断言其 _symbol_has_definition
    与 shared.symbol_match.symbol_has_definition 是同一个对象（is 判定）。

    build_prompt.py 顶层会执行文件读取和闸门检查，可能因文件不存在而抛错。
    但 import 行（from shared.symbol_match import ...）在文件读取之前，
    所以即使后续顶层代码抛错，_symbol_has_definition 已绑定到模块命名空间。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_prompt", BUILD_PROMPT_PATH)
    module = importlib.util.module_from_spec(spec)
    # build_prompt.py 顶层成功执行时会写入 prompt 输出文件——测试后清理以防污染工作区
    _output_file = BUILD_PROMPT_PATH.parent / "prompt_research-review_round1.md"
    try:
        spec.loader.exec_module(module)
    except Exception:
        pass  # 顶层执行可能因文件不存在或闸门检查而失败，不影响 import 链验证
    finally:
        if _output_file.exists():
            _output_file.unlink()

    from shared.symbol_match import symbol_has_definition
    assert hasattr(module, "_symbol_has_definition"), \
        "build_prompt 模块未绑定 _symbol_has_definition——import 链可能已断"
    assert module._symbol_has_definition is symbol_has_definition, \
        "build_prompt._symbol_has_definition 与 shared.symbol_match.symbol_has_definition 不是同一对象"