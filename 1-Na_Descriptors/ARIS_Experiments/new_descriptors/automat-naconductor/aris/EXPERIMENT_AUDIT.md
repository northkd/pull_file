# Experiment Audit Report

**Date**: 2026-08-07
**Auditor**: Claude Web (manual bridge, read-only cross-model)
**Project**: automat-naconductor（Na 离子导体描述符搜索管线）
**Checklist**: stat-pipeline 专项（A-F 标准 + G-L 六项统计管线泄露/偏差专项）
**Round**: run02（run01 已于同日完成，本轮为 stat-pipeline 专项扩展）
**Compact Level**: 0（全文嵌入，16 个文件）

## Overall Verdict: FAIL

判定由 **H（FAIL）** 单独决定：四级全量目标依赖选择 → 无外层循环的 CV，且项目内唯一的乐观偏差承认（`selection_uncertainty_included: False`）在 `CombinationValidator.validate` 扁平化时被丢弃，不进入任何 CSV 或报告。叠加 H.6（噪声基线不对称）与 K.6（单列公式下 CV 退化为未去混杂的折内原始 Spearman）。

与 run01（A-H 审计，7 项 FAIL）相比：**G 项已从 FAIL 转为 PASS/WARN**——折内填充与标准化、子样本内独立预处理确实做对了，是实质进步。新增 I-L 四项暴露了更深的问题层。

## Integrity Status: fail

## Checks

### A. Ground Truth Provenance: PASS
- 目标 `log_sigma` 全程由 `data/naconductor_raw.csv` 读入，无模型输出反填。
- V2 残差目标已显式标注为 proxy（`fold_safe_oof_target_residual_prediction`）。
- 潜在隐患：`build_feature_matrix` 的 `metadata_cols` 保留了 `log_sigma`，当前白名单取列安全但未来有泄露风险。

### B. Score Normalization: WARN
- 无指标以模型自身输出统计量作分母（PASS）。
- `system_proxy_ratio` 两处硬饱和（`raw_rho_sq<1e-12`→0.0，符号翻转→1.0），1.0 语义二义。
- `signal_retention` 是"均值之比"非"比之均值"，跑在未筛全集上，**上一轮实际产出 102.5%——不可能值**。
- `delta_pct` 分母可能基于不同可用策略数，数学上无意义。

### C. Result File Existence: WARN
（results/ 按用户要求排除，仅评代码自洽性）
- "41 个描述符"在代码里实际是 38（`_INACTIVE_FOR_AUTOMATIC_SEARCH` 排除 3 个）。
- `analyze_all` docstring 写"80% 跳过"实际是 `n_valid < 5`，80% 阈值不存在。
- 报告混用 `filtered_deconfound_df` 与完整 `deconfound_df`，基线与 Stage 1 表格可能指向不同描述符。
- `evaluation.secondary` 声明的 `cv_rmse`/`stability_score` 不存在；`deconfound.method` 的 DML 未实现。
- `run_info.yaml` 多处参数不驱动代码（配置漂移）。

### D. Dead Code Detection: WARN
- **`_classify_descriptor` 接收 `deconf_p` 但完全不用**——"强物理信号"标签不含任何显著性要求（最有实质危害）。
- `noise_info_df` 算出后丢弃——噪声列与目标的实际相关不可见。
- `_base.py:CROSS_GROUP_RULES` 是第二套规则真值源，无人调用。
- `_one_hot_encode` 零调用；`_formula_dimensionally_valid` 的量纲推导对 multiply/ratio 无效。

### E. Scope Assessment: WARN
- 84 样本/3 体系/38 描述符，实际只有 6 个通过 Stage 1 预筛。
- `--seed` 不通到 CV（`StratifiedKFold(random_state=42)` 是字面量）。
- V1 置换仅 100 draws（p<0.01 不可表达）；V4 bootstrap 用 percentile 法（有偏）。
- "一致性优秀"可由单个数据点触发。
- 搜索空间高度不对称（F/G 族无跨族规则）且未披露。

### F. Evaluation Type: real_gt
- 主线全部对实测 `log_sigma`（real_gt）。
- V1=real_gt+体系内置换零分布（设计正确）；V2=real_gt折内残差化派生；V3/V4=real_gt原始 Spearman（未去混杂）。
- 无 human_eval、无 simulation_only。

### G. Data Leakage in Preprocessing: WARN
| 检查项 | 判定 |
|---|---|
| 中位数填充 | PASS（折内） |
| StandardScaler | PASS（折内） |
| 噪声列注入 | PASS（固定种子全局一次，纯标准正态） |
| 稳定性选择子样本 | PASS（循环体内新建 Pipeline） |
| 去混杂残差化 | Stage1全量(允许)/Stage4 V2折内(PASS)/Stage3排序全量(问题在H) |

- **`build_feature_matrix` 明确不做全量填充——工程质量最高的一处。**
- 噪声基线是"零分布的一次抽样"非零分布，基线高低取决于种子运气且不可见。
- `_factor_spanning:encode_controls` 有静默错编码风险（测试折未见类别被当参考类）。

### H. Feature Selection Leakage: FAIL（CRITICAL）
1. **稳定性选择→CV：泄露。** Stage 1 用全量84行含目标统计量预筛（38→6，砍84%），之后同84行做CV。
2. **组合top-k→CV：泄露。** 按全量 `combined_deconf_spearman` 排序取top-10，在同样84行上跑CV，无外层循环。
3. **PhysicalGrouper代表→CV：泄露。** 按全量 `|deconf_rho|` 选代表，报告把同一统计量当评估证据印。
4. V2折内安全，但候选选择条件于全量统计量。
5. **项目部分承认（`selection_uncertainty_included: False`）但该标志在 `validate()` 扁平化时被丢弃，不进CSV不进报告——决定性FAIL理由。**
6. **噪声基线不对称：真实描述符已过Stage1目标筛，15个噪声列没有——假阳性对照系统性偏向真实描述符。**

### I. Deconfounding Methodology: WARN（清单）/ FAIL级修复项（审稿人）
1. 残差化范围：Stage1全量(允许)，V2主指标折内(PASS)，V2补充量全量但已标注。
2. `build_rank_aware_controls` 基本正确，但"冗余"归属由字母序决定（任意）。
3. `system_proxy_ratio` 不是有效分解量：Spearman²≠R²，符号翻转硬置1.0用噪声断言"完全混杂驱动"。
4. **Ridge alpha=1.0 引入系统性偏差**：分类混杂one-hot下OLS即饱和调整，alpha=1.0导致体系组~5%、稀有anion组~26%欠调整，残差保留混杂，`deconfounded_spearman`系统性偏向`raw_spearman`——偏差方向有利于结论。
5. 无双重控制（PASS）。
6. **`partial_spearman` 静默回退**：n<3或z列数≥n时返回原始Spearman无标记，Stage3可达（5个有效点的ratio可冒充`combined_deconf_spearman`排第一）。
7. 先残差化后取秩破坏Spearman单调不变性，与选用Spearman的理由矛盾。

### J. Multiple Testing: WARN（清单）/ FAIL级修复项（审稿人）
1. 无任何多重检验校正，`deconf_p`不扣除已估计混杂参数（反保守），且在标签判定中被完全忽略。
2. `composite_score`只用可用策略——透明度PASS，但`delta_pct`跨不同N相除WARN。
3. top-k乐观性未被承认（同H.5），"最强组合"定义不自洽（按deconf rho选，用composite打分）。
4. **Bootstrap CI算的是原始Spearman非去混杂Spearman，不覆盖选择不确定性，却被题为"体系分层Bootstrap 95% CI"与deconf rho并列——读者会误读。**
5. `consistency_desc`跨候选汇总（应逐候选），`"所有CV策略均无显著相关"`措辞错误。

### K. Target & Metric: WARN（清单）/ 领域级FAIL风险（审稿人）
1. `log_sigma`无校验（log10 vs ln），目标未标准化（PASS）。
2. **混杂集里没有温度/测量方法/体相-晶界——支配性混杂完全缺席。** 文献中这些因素以数量级计，远超结构描述符效应量。
3. Spearman只捕单调关系，而快离子导体经典构效关系非单调（volcano曲线）。
4. **`composite_score`取绝对值双层掩盖方向翻转**：层一策略内带符号平均（折间抵消趋0），层二策略间取绝对值。+0.5/-0.5与+0.5/+0.5不可区分。
5. 过校正风险不可逆：体系间机制被标"体系代理"→Stage1永久剔除→Stage2/3/4无法回收。0.3/0.3/0.7阈值无来源。
6. **单列公式下CV Spearman=sign(a)·Spearman(y_val,x_val)，alpha/标准化/正则化一概无效——三条CV不是"三种模型验证"而是三种划分的原始秩相关平均，且无一条去混杂。** LOSO≈V3（非独立），anion_stratified验证折混合阴离子类型（构造上被混杂）。

### L. Causal Claim Boundary: WARN（清单）/ 全项目最危险一处（审稿人）
- 纪律层面好：`causal_claim: False`一致设置，README/program.md有限制语。
- **但五条抵消：**
  1. **混杂集被断言非论证**：`run_info.yaml`写"不是因果通路"，`deconfound.py`写"同时影响X和Y"——均为未经检验的DAG断言。`anion_type`经极化率→键软度→迁移势垒→电导率，是结构→电导通路本身（中介非混杂）。对中介条件化会减掉待测效应。
  2. **手稿标题"因果去混杂搜索方法"与代码`causal_claim: False`直接冲突**——审稿人一眼可见，最容易导致拒稿。
  3. "deconfounded"在因果推断文献中意味着后门准则可识别，此处实际只是Ridge残差化。
  4. "强物理信号"标签由`|deconf_rho|>0.3`单条件触发（不看p/n/CV/多重性），把统计阈值翻译成物理断言。
  5. 报告免责声明是装饰性的：Stage4表末"探索性"是f-string硬编码不读`causal_claim`；结论段标题"物理发现"；"信号保留率102.5%"配因果味措辞。

## Action Items

### 阻断级（投稿前必须处理，6项）
1. 画DAG辩护`system`/`anion_type`是混杂非中介，或改口径（删断言、`deconfounded_spearman`更名`within_system_partial_spearman`、同时报告去混杂前后）
2. 手稿标题去掉"因果"，或补可识别性论证
3. 加外层嵌套验证（外层按system留出，内层完整重跑Stage1-4），或至少把`selection_uncertainty_included: False`加进产物+报告顶部加乐观偏差明文声明
4. 修正噪声基线对称性（噪声列走完全相同的Stage1预筛），否则删除`above_noise_baseline`
5. `deconf_p`接进`_classify_descriptor`+BH-FDR校正
6. `_evaluate_candidate`加`n_valid`下限(≥30或≥50%)+`partial_spearman`静默回退返回`deconfound_applied: False`标志

### 高优先级（6项）
7. DeconfoundAnalyzer Ridge改`alpha=0`(OLS)，拆分混杂alpha与预测alpha
8. `composite_score`加带符号版本+Fisher z平均
9. 重写`signal_retention`（逐描述符中位数+分位区间）或删除
10. 修`delta_pct`（仅同策略数可比时计算）+统一"最强组合"定义
11. `consistency_desc`改逐候选计算，`len(signs)<3`禁输出"优秀"
12. `_encode_controls`加显式断言（测试折未见类别记skipped）

### 中优先级（8项）
13-20. YAML真驱动代码、noise_info落盘、删死代码、统一41/38口径、增列n_valid、V1≥2000 draws、V4改BCa、披露搜索空间不对称、补温度/测量方法列

## Claim Impact
- Claim 1（关联性/预测稳健性，非因果）: **needs_qualifier**
- Claim 2（去混杂后信号保留）: **unsupported**
- Claim 3（跨CV策略一致性）: **unsupported**
- Claim 4（组合优于单描述符）: **unsupported**

## Top 3 Critical Findings（stat-pipeline 专项）

1. **混杂集可能是中介集——主指标系统性删除答案且不可逆。** `anion_type`经极化率→键软度→迁移势垒是结构→电导通路本身；`system`是结构的下游标签。对中介条件化减掉待测效应，叠加Stage1永久剔除，管线可能在删除真实机制。

2. **四级全量目标依赖选择→无外层循环CV，唯一承认在写盘前被丢掉。** Stage1预筛(38→6)→Stage2稳定性选择→PhysicalGrouper代表→Stage3排序→Stage4 top-k CV，全在同一84行上。`selection_uncertainty_included: False`在`validate()`扁平化时被丢弃。噪声基线不对称进一步放大偏差。

3. **单列公式下CV代数退化为未去混杂的折内原始Spearman。** `Spearman(y_val, ŷ)=sign(a)·Spearman(y_val, x_val)`，alpha/标准化无效。`composite_score`度量原始关联却与`deconfounded_spearman`并列；LOSO≈V3非独立；anion_stratified验证折混合阴离子类型在构造上被混杂。"跨CV策略一致性"无独立信息量。

---

**审计覆盖限制**：(a) 41个描述符实现文件未提供，物理正确性未审；(b) 无真实行号，传输损坏与真实bug不可区分；(c) results/已排除，数字级核对未做；(d) run_status.py/plot_run_results.py/test_descriptors.py未提供。
