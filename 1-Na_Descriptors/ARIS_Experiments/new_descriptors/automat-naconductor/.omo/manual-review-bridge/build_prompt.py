"""构建 research-review prompt 的 Python 脚本。
读取 8 个指定文件，拼装成完整的 Claude 网页端 prompt。
"""
import pathlib
import re
import sys

import yaml

# 从 shared/symbol_match.py 导入符号定义位置匹配器（与 descriptors/registry.py 复用同一份实现）
# .omo/ 目录不在 Python 包路径中，需手动添加仓库根到 sys.path
_repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
from shared.symbol_match import symbol_has_definition as _symbol_has_definition  # noqa: E402

project_root = pathlib.Path(
    r"E:\work\worklist\1-Na离子导体\nasicon-causal-inference-main"
    r"\experiments\02_组合描述符搜索\automat-naconductor"
)
output_file = project_root / ".omo" / "manual-review-bridge" / "prompt_research-review_round1.md"

# 文件列表 (相对路径标签, 绝对路径)
# 历史文档（.aris/ 审计正文含旧代码全文）绝不能喂给闸门，否则被审计过的
# 已删符号会因在旧代码全文里出现而被误判为"仍然存在"。
LIVE_SOURCES = [
    ("run_info.yaml", project_root / "run_info.yaml"),
    ("program.md", project_root / "program.md"),
    ("descriptors/deconfound.py", project_root / "descriptors" / "deconfound.py"),
    ("descriptors/stability.py", project_root / "descriptors" / "stability.py"),
    ("descriptors/combination.py", project_root / "descriptors" / "combination.py"),
    ("run_pipeline.py", project_root / "run_pipeline.py"),
]

CONTEXT_DOCS = [
    (
        ".aris/traces/experiment-audit/2026-08-07_run01/001-experiment-audit.response.md (run01 EXPERIMENT_AUDIT)",
        project_root
        / ".aris"
        / "traces"
        / "experiment-audit"
        / "2026-08-07_run01"
        / "001-experiment-audit.response.md",
    ),
    (
        ".aris/EXPERIMENT_AUDIT.md (run02 EXPERIMENT_AUDIT)",
        project_root / ".aris" / "EXPERIMENT_AUDIT.md",
    ),
]

file_list = LIVE_SOURCES + CONTEXT_DOCS

# 读取所有文件
file_contents = {}
for label, path in file_list:
    content = path.read_text(encoding="utf-8")
    file_contents[label] = content
    print(f"读取: {label} ({len(content)} chars)")

# 闸门语料：只含当前活源码中的 .py 代码文件（descriptors/*.py 与 run_pipeline.py）。
# 不含 run_info.yaml / program.md（它们不定义代码符号，混入只会在子串/整词命中时
# 制造洗白）；更不含 .aris/ 历史文档（旧代码全文会让已删除的符号被误判为"仍然存在"）。
# 这里只影响闸门语料，file_embed 的嵌入内容由 file_list（LIVE_SOURCES + CONTEXT_DOCS）
# 合并生成，一字不改。
live_py_contents = {
    label: file_contents[label]
    for label, path in LIVE_SOURCES
    if path.suffix == ".py"
}

# 拼装文件嵌入段
file_embed = ""
for label, _ in file_list:
    file_embed += f"--- 文件开始: {label} ---\n"
    file_embed += file_contents[label]
    if not file_contents[label].endswith("\n"):
        file_embed += "\n"
    file_embed += f"--- 文件结束: {label} ---\n\n"


def _assert_steps_match_sources(steps_text: str, embedded_sources: dict[str, str]) -> None:
    """Abort prompt construction if any symbol named in steps_text has no
    definition site in any embedded source body.

    语料必须只含当前活源码（.py 代码文件），混入历史文档（.aris/ 审计正文里的旧代码
    全文）会使检查失效——被审计过的已删符号会从旧代码全文里被误判为"仍然存在"。

    从 steps_text 中抽取所有反引号包裹的标识符（形如 `partial_spearman`、
    `CombinationValidator._noise_baseline`）。

    只认定义位置，不认文中出现：符号视为"存在"，当且仅当在任一语料正文里命中
    _symbol_has_definition 的任一模式。整词边界既避免 `not_partial_spearman` 洗白
    `partial_spearman`，也避免泛化末段（run / search / validate）在任意位置撞上。

    只要有一个符号在所有正文里都没有定义位置，抛 ValueError 并终止；异常消息列出
    全部缺失符号及其在 steps_text 中的行号。不降级为 warning，不 try/except 吞掉，
    不加 skip。
    """
    # 行号映射：先按行切分，每行对应其出现的（1-based）行号
    lines = steps_text.splitlines()

    # 收集每行的反引号标识符，记录符号名 -> 首次出现行号
    symbol_lines: dict[str, int] = {}
    for idx, line in enumerate(lines, start=1):
        for match in re.finditer(r"`([^`]+)`", line):
            raw = match.group(1)
            # 只关心形如 Python 标识符/成员引用 的 token，跳过含空格/标点的自然语言占位
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", raw):
                continue
            symbol_lines.setdefault(raw, idx)

    missing: list[tuple[str, int]] = []
    for symbol, line_no in symbol_lines.items():
        if not any(_symbol_has_definition(symbol, body) for body in embedded_sources.values()):
            missing.append((symbol, line_no))

    if missing:
        detail = "\n".join(
            f"  - {sym} (steps_text 第 {ln} 行)" for sym, ln in missing
        )
        raise ValueError(
            "algorithm_steps 中以下符号在所有嵌入源码正文中均不存在，"
            "清单已漂移，终止构建 prompt：\n" + detail
        )


def _assert_anchors_resolve(run_info_dict: dict, live_py_contents: dict[str, str]) -> None:
    """核验 run_info.yaml 中 estimand.implementation_anchors 的每个符号
    在活源码中有定义位置。

    复用 _symbol_has_definition 的匹配逻辑（同一套正则模式），不另写一套。

    anchor 值格式为 "文件路径, 符号路径 (可选注释)"，例如：
      "descriptors/deconfound.py, DeconfoundAnalyzer.build_rank_aware_controls"
      "descriptors/combination.py, CombinationValidator._factor_spanning (system_rho)"
    提取逗号后的符号路径，去掉括号注释，取末段做定义位置匹配。

    缺失则抛 ValueError，同时列出符号名与它所属的 anchor 键名。
    """
    estimand = run_info_dict.get("estimand", {})
    anchors = estimand.get("implementation_anchors", {})
    if not anchors:
        return

    missing: list[tuple[str, str]] = []  # (anchor_key, symbol)
    for anchor_key, anchor_value in anchors.items():
        # 取逗号后的部分（符号路径），去掉括号注释
        parts = str(anchor_value).split(",", 1)
        symbol_part = parts[1] if len(parts) >= 2 else parts[0]
        symbol_part = re.sub(r"\s*\(.*\)\s*$", "", symbol_part).strip()
        if not symbol_part:
            missing.append((anchor_key, "(空符号)"))
            continue
        if not any(
            _symbol_has_definition(symbol_part, body)
            for body in live_py_contents.values()
        ):
            missing.append((anchor_key, symbol_part))

    if missing:
        detail = "\n".join(
            f"  - anchor '{key}' -> 符号 '{sym}' 在所有活源码中无定义位置"
            for key, sym in missing
        )
        raise ValueError(
            "estimand.implementation_anchors 中以下符号在活源码中无定义位置，"
            "anchor 已漂移：\n" + detail
        )

# 已知弱点
known_weaknesses = r"""注：以下审计发现引用的部分符号名已改名或删除（对照见 RENAME_LOG.md），发现本身仍然有效。

以下为两轮 experiment-audit 的 Top Critical Findings 原文。

=== run01 审计（A-H 八项，7 项 FAIL）关键发现 ===

Overall Verdict: FAIL

A. Target Variable Provenance: FAIL
- 数据模式中不存在任何测量条件列。没有温度、没有测量方法（EIS/直流极化）、没有 total/bulk/grain-boundary 区分、没有样品制备、没有文献来源 ID。σ 是 Arrhenius 量，同一材料在 25°C 与 300 K 之外的报道值可差数量级；bulk 与 total 电导率对同一样品可差 2-3 个量级。
- 异质来源被合并且合并本身就是设计目的。NASICON / sulfide / halide 三体系汇入同一 log_sigma 向量，LOSO-CV 明确要求跨体系外推。

B. Metric Self-Reference: FAIL
- 复合标签可以奖励管线自身定义为失败的结果。_classify_descriptor 把 |deconf_rho| > 0.3 置于代理比判断之上，注释明写"无论代理比多高"。raw_rho=0.9, deconf_rho=0.31 时 system_proxy_ratio=0.881，即 88% 由体系混杂驱动的描述符被标为"强物理信号"。
- clip 销毁了方向信息。deconf_rho > raw_rho（抑制效应）会产生负比值，被 clip 成 0.0，即"最纯物理信号"。去混杂反而增强相关这一最该被警惕的情形，被编码为最高信誉等级。
- signal_retention 是"均值之比"非"比之均值"，可超过 100%。

D. Dead Path Detection: FAIL
- 注释声明"有效值不足 80% 则跳过"，代码执行 n_valid < 5。80% 这个数字在代码库中不存在。
- deconf_p 是死参数，"显著"一词建立在它之上，但 _classify_descriptor 从不使用它。
- partial_spearman 静默回退：z.shape[1] >= n_samples 时返回原始 Spearman 当作去混杂值，回退事件无任何记录。

E. Scope and Multiplicity: FAIL
- 零多重性控制。无 FDR、无 Bonferroni、无置换检验、无嵌套外层选择。
- "一致性优秀"的证据基数是 <=9 个非独立观测。

F. Threshold Provenance: FAIL
- 全部决定性阈值（0.2/0.3/0.3/0.7）零外部依据，标 "errata P3" 表明是看过输出后修订的。
- 参考类编码 + L2 惩罚 = 结果不随参考类别选择而不变。

G. Null Distribution and Selection Effects: FAIL
- 唯一的经验零分布是 Stage 2 注入噪声列。无置换检验、无 y 打乱、无跨种子重复。
- 零分布施加在错误阶段：真实描述符已过 Stage 1 预筛选，噪声列没有——两臂不可交换。

H. Randomness and Reproducibility: FAIL
- 配置文件与代码描述的是不同的过程。大量 YAML 键不被代码读取。改 YAML 不改行为。
- CLI seed 不传播到 CV 阶段。

=== run02 审计（A-L 十二项 stat-pipeline 专项）Top 3 Critical Findings 原文 ===

1. 混杂集可能是中介集——主指标系统性删除答案且不可逆。anion_type 经极化率→键软度→迁移势垒是结构→电导通路本身；system 是结构的下游标签。对中介条件化减掉待测效应，叠加 Stage1 永久剔除，管线可能在删除真实机制。

2. 四级全量目标依赖选择→无外层循环 CV，唯一承认在写盘前被丢掉。Stage1 预筛(38→6)→Stage2 稳定性选择→PhysicalGrouper 代表→Stage3 排序→Stage4 top-k CV，全在同一 84 行上。selection_uncertainty_included: False 在 validate() 扁平化时被丢弃。噪声基线不对称进一步放大偏差。

3. 单列公式下 CV 代数退化为未去混杂的折内原始 Spearman。Spearman(y_val, y_hat)=sign(a)*Spearman(y_val, x_val)，alpha/标准化无效。composite_score 度量原始关联却与 deconfounded_spearman 并列；LOSO 与 V3 非独立；anion_stratified 验证折混合阴离子类型在构造上被混杂。"跨 CV 策略一致性"无独立信息量。

=== 补充声明 ===
数据集仍在准备中，本次评审对象是算法设计本身，不涉及任何数值结果。"""

# 算法步骤清单
algorithm_steps = """以下是从嵌入代码中识别的主要算法步骤，请逐条评估。

适用范围：本清单只覆盖统计管线层。描述符实现层（CIF → 特征值）不在此列，
由 descriptor-impl profile 单独评审。

**去混杂层（descriptors/deconfound.py）**
- 步骤 A1: `build_rank_aware_controls` — 构造 system 为主控制 + 秩感知增量 anion 对比项的设计矩阵（deconfound.py:68）
- 步骤 A2: `rank_corr_of_linear_residuals` — 对 x 与 y 分别做 Ridge 线性残差化，对残差求 Spearman；非文献意义的 partial Spearman（deconfound.py:132）
- 步骤 A3: `analyze_all` — 对每个描述符计算 raw_spearman 与 rank_corr_of_linear_residuals，按 |rho| 降序（deconfound.py:206）

**稳定性选择层（descriptors/stability.py）**
- 步骤 B1: `StabilitySelector.run` — 无放回子采样 + 子样本内独立预处理 + Lasso + 选中频率统计 + 噪声列 95 分位基线（stability.py:100）
- 步骤 B2: `PhysicalGrouper.group_and_select` — 按物理族分组，每组取 |rank_corr_of_linear_residuals| 最高的代表（stability.py:230）

**组合搜索与验证层（descriptors/combination.py）**
- 步骤 C1: `ConstrainedCombinationSearch.search` — 声明式算子注册表约束的二元/三元公式枚举 + 去混杂 Spearman 排序（combination.py:305）
- 步骤 C2: `CombinationValidator._noise_baseline`（V1）— 体系内分量置换零分布（combination.py:552）
- 步骤 C3: `CombinationValidator._factor_spanning`（V2）— 折内残差化 + OOF 公式预测 vs 残差目标。折由 StratifiedKFold 按 system 分层生成，每折均含全部体系；最小体系不足 2 时回退随机 KFold（combination.py:603，分折逻辑见 643–654）
- 步骤 C4: `CombinationValidator._per_system`（V3）— 逐体系原始 Spearman（combination.py:762）
- 步骤 C5: `CombinationValidator._bootstrap_ci`（V4）— 体系分层 bootstrap CI（percentile 法）（combination.py:784）
- 步骤 C6: `CombinationValidator.full_validation` — 组装 V1–V4 与 uncertainty 元数据（combination.py:842）
- 步骤 C7: `CombinationValidator.validate` — 扁平化 V1–V4 至 CSV 行（combination.py:885）

**管线级（run_pipeline.py）**
- 步骤 D1: `runStage0` — 读取原始 CSV 与 CIF，CIF 存在性与可解析性预检（run_pipeline.py:212）
- 步骤 D2: `runStage1` — 全描述符线性残差秩相关分析 + 预筛选（run_pipeline.py:269）
- 步骤 D3: `runStage2` — 稳定性选择 + 物理族代表选择（run_pipeline.py:311）
- 步骤 D4: `runStage3` — 约束组合搜索（run_pipeline.py:403）
- 步骤 D5: `runStage4` — V1–V4 探索性验证 + 单描述符基线（run_pipeline.py:461）
- 步骤 D6: `generateReport` — 汇总报告与 CSV 写出（run_pipeline.py:535）

**跨阶段结构**
- 步骤 E1: Stage 0 → 1 → 2 → 3 → 4 构成全量目标依赖的选择链，全部在同一批样本上完成，无外层循环 CV
"""

# 输出格式
output_format = """请按以下结构输出，对每个算法步骤逐条给出四问的回答：

## Overall Assessment
[2-3 段总体评价：这套算法管线作为"结构描述符-电导率去混杂相关性搜索"工具，其设计层面的核心问题是什么？]

## Per-Step Algorithmic Assessment

对每个步骤（A1, A2, A3, A4, B1, B2, C1, C2, D1, D2, D3, D4, D5, D6, E1）逐条输出：

### 步骤 [编号]: [名称]
1. **Does it accomplish its design goal?** [回答]
2. **Degeneration conditions?** [回答]
3. **Minimal fix and cost?** [回答]
4. **Standard method this is an ad-hoc version of?** [回答]

## Cross-Cutting Issues
[跨步骤的系统性问题——如果某些问题不属于单个步骤但在多个步骤中反复出现，在此总结]

## Top 3 Actionable Recommendations
1. [recommendation 1]
2. [recommendation 2]
3. [recommendation 3]"""

# 会话指示
session_instructions = """【会话指示 - research-review】

1. 本模板支持多轮迭代对话。第 1 轮复制下方"prompt 正文"全部内容，粘贴到新的 Claude 对话。
2. 第 2-N 轮【在同一对话中继续】——不要开新对话。后续轮次可针对未解决的弱点追问。
3. 后续轮次的典型用法：
   - 追问特定算法步骤的细节
   - 请求某个"标准方法"的具体实现方案
   - 请求某个退化条件的构造性证明
   - 请求替代算法设计的草图
4. 何时停止：双方就每个步骤的四问回答达成一致、核心设计问题明确、修复方向确定。
5. 如需全新审稿人视角（防止长期对话的偏见累积），可开新对话重新粘贴完整 prompt。

注意：本次评审的特殊约束——
- 不评估可发表性，不提议新实验
- 只评判算法设计本身（不涉及数值结果，数据集仍在准备中）
- 对每个算法步骤回答四个固定问题"""

# 拼装完整 prompt
# 闸门：在把 algorithm_steps 写进 prompt 之前，确认其中点名的每个符号都在活源码
# （.py 代码文件）里有定义位置。任一个无定义位置即抛 ValueError，阻止生成含幽灵步骤的 prompt。
_assert_steps_match_sources(algorithm_steps, live_py_contents)

# 闸门：核验 run_info.yaml 中 estimand.implementation_anchors 的符号在活源码中有定义位置。
# 任一个无定义位置即抛 ValueError，阻止生成含漂移 anchor 的 prompt。
run_info_dict = yaml.safe_load(file_contents["run_info.yaml"])
_assert_anchors_resolve(run_info_dict, live_py_contents)

prompt = f"""{session_instructions}

---

I'm going to present a complete ML research project for your critical review.
Please act as a senior ML reviewer (NeurIPS/ICML level) with deep expertise in
causal inference, feature selection, and small-sample statistics.

This project is a **Na-ion conductor structural descriptor search pipeline**.
The goal: find CIF-structure-derived descriptors whose deconfounded Spearman
correlation with log10(conductivity) is maximized, using ~84 samples across
3 material systems (NASICON / sulfide / halide).

**Important scope constraint**: The dataset is still being prepared. You are
reviewing the **algorithm design itself**, not any numerical results. Do not
comment on specific numbers, scores, or outcomes—judge the algorithms as
algorithms.

## 你的任务

For each algorithmic step below, assess:
1. Does the procedure actually accomplish what it is designed to accomplish?
2. Under what conditions does it degenerate to something trivially different?
3. What is the minimal design change that would fix it, and what does that
   change cost?
4. Is there a standard method in the statistics/ML literature that this step
   is an ad-hoc version of? Name it.

Do not propose new experiments. Do not assess publishability. Judge the
algorithms as algorithms.

## 算法步骤清单

{algorithm_steps}

## 已知弱点（两轮 experiment-audit 的 Top Critical Findings 原文）

{known_weaknesses}

## 文件内容

{file_embed}
## 输出格式

{output_format}
"""

# 写入文件
output_file.parent.mkdir(parents=True, exist_ok=True)
output_file.write_text(prompt, encoding="utf-8")
print()
print(f"Prompt 文件已写入: {output_file}")
print(f"总字符数: {len(prompt)}")
print(f"总行数: {prompt.count(chr(10)) + 1}")
