# automat-reform - Work Plan

## TL;DR (For humans)

**目标**：将 AUTOMAT 从"化学组成→特征"管道改造为"CIF结构→物理描述符→因果推断"管道，用于 Na 离子导体（NASICON/硫化物/卤化物，~80-90样本）电导率描述符搜索，最终输出**有物理意义的描述符组合**及其完整证据链。

**你将得到什么**：
1. `automat-naconductor/` 目录：改造后的完整框架代码
2. 41 个描述符的计算脚本（8个已有 + 25个新增 + 8个已有中间量）
3. 4 阶段分析流水线：单描述符筛选 → 物理分组去冗余 → 物理约束组合搜索 → 组合验证
4. 最终产出：Top-5 物理约束组合，每个附带去混杂Spearman、噪声基线、体系分层、Factor Spanning完整证据

**为什么选这个方案**：
- 保留 AUTOMAT 的迭代范式（idea.md→idea.py→评估→keep/discard）+ 审计追踪
- 全面重写输入层/描述符层/CV层/评估层，适配你的小样本+体系混杂+因果推断需求
- 物理对象分组 + 双层组合约束（运算符+物理对象）防止产生无物理意义的组合
- 借鉴量化交易（Fama-MacBeth去混杂、HRP聚类思想、Factor Spanning Test、Sparse PO稀疏约束）和生物医学（Stability Selection、Knockoff Filter、SINDy稀疏识别）方法

**不做的事**：
- 不修改原始 `automat/` 目录
- 不使用 RF importance 作为特征筛选
- 不使用随机 k-fold 作为唯一 CV
- 不允许 log/√/幂次等无物理意义算子的组合
- 不允许跨物理对象族的无机制组合
- 不重算 SoftBV/Zeo++（复用已有数据）
- 不用 occupancy 推断空位

**工作量**：8 个实施任务 + 4 个最终验证任务，预计需要 2-3 天执行

**风险**：
- 新增描述符中 BVSE 能垒计算需要 SoftBV 工具（计算可行性待确认）
- 高风险族（电子结构代理 G、对称性破缺 H）可能全部被去混杂分析淘汰
- 80-90 样本做组合搜索统计功效有限，需依赖 bootstrap 置信区间

**关键决策（已确认）**：
- 复制 `automat/` 为 `automat-naconductor/`，在新目录改造
- CSV 用 `cif_path` 列直接指向 CIF 文件
- 仅 3 体系（NASICON/硫化物/卤化物）
- 物理约束组合搜索：仅允许 +（叠加）、×（协同）、同量纲比值，且仅允许同族或相邻族组合
- 噪声注入 + Stability Selection 替代简单 bootstrap ranking
- 必须回答"局域宽松因子的相关性有多少来自区分体系 vs 体系内物理"

## Scope

### IN（本计划覆盖的范围）
1. 复制 `automat/` 为 `automat-naconductor/`，在新目录完成全部改造
2. 数据层改造：新 CSV 格式（cif_path + 体系标签 + 阴离子标签 + logσ）
3. 描述符计算层：从 CIF 批量计算 41 个描述符（8个已有 + 25个新增 + 8个已有中间量）
4. 特征矩阵构建：描述符矩阵 + 噪声列 + 标准化
5. 交叉验证策略：阴离子分类 CV + LOSO + 体系内 CV
6. 体系去混杂分析：偏相关/残差分析，回答核心因果问题
7. Stability Selection + 噪声基线
8. 物理对象分组 + 去冗余选代表
9. 物理约束组合搜索：同族 + 相邻族协同，穷举 ~100 候选组合
10. 组合验证：噪声组合基线 + Factor Spanning + 体系分层 + bootstrap CI
11. AUTOMAT 迭代范式适配：idea.md 模板 + results.tsv 审计 + 综合指标 keep/discard

### OUT（本计划不覆盖的范围）
- 不修改原始 `automat/` 目录的任何文件
- 不重算 SoftBV/Zeo++（复用阶段3已有数据）
- 不做 DFT 计算
- 不做 Materials Project 数据库高通量筛选
- 不写论文正文（本计划产出的是分析结果，不是论文）
- 不解决空位族的 occupancy 推断问题（用 Voronoi/BVSE 替代方案绕过）
- 不训练深度学习模型（GNN/Transformer等）
- 不做 SISSO 全算子搜索（仅用物理约束子集）

## Verification strategy

- **测试策略**：tests-after（每个组件完成后写验证脚本）
- **每步验证**：输出格式正确性 + 数值范围合理性 + 与已知结果对比
- **最终验证波**：4 个验证任务，覆盖计划合规性、代码质量、数值正确性、范围忠实性
- **关键基准**：阶段3已知的局域宽松因子 Spearman=0.597、瓶颈加权宽松因子 Spearman=0.623 必须在改造后框架中复现

## Execution strategy

按 8 个实施任务顺序执行，每个任务产出可独立验证的文件或结果。任务间有依赖关系：C1→C2→C3→C4/C5/C6（并行）→C7→C8。

## Todos

- [ ] 1. 复制 AUTOMAT 并改造数据层和配置系统
- [ ] 2. 实现 41 个描述符的计算模块
- [ ] 3. 实现特征矩阵构建与噪声注入
- [ ] 4. 实现多策略交叉验证系统
- [ ] 5. 实现体系去混杂分析模块
- [ ] 6. 实现 Stability Selection 与物理分组去冗余
- [ ] 7. 实现物理约束组合搜索与评估
- [ ] 8. 实现组合验证与最终报告生成

## Final verification wave

- [ ] F1. 计划合规性审计：所有文件路径、函数签名、输出格式与计划一致
- [ ] F2. 数值基准复现：局域宽松因子 Spearman=0.597 在新框架中复现
- [ ] F3. 端到端流水线测试：从 CIF 输入到最终组合报告完整运行无错
- [ ] F4. 范围忠实性检查：未修改原始 automat/、未引入禁止算子、未做超出范围的事

## Commit strategy

每个任务完成后单独提交，提交信息格式：`feat(naconductor): 任务简述`

## Success criteria

1. `automat-naconductor/` 可从 CIF 批量计算 41 个描述符并输出标准化特征矩阵
2. 多策略 CV（阴离子分类 + LOSO + 体系内）均可运行并输出每折指标
3. 去混杂分析可回答"局域宽松因子的相关性多少来自体系混杂 vs 体系内物理"
4. Stability Selection 输出每个描述符的选择频率，噪声基线可计算
5. 物理约束组合搜索穷举 ~100 候选，按去混杂 Spearman 排序输出 Top-5
6. 组合验证报告包含：噪声基线对比、Factor Spanning 检验、体系分层评估、bootstrap CI
7. 原始 `automat/` 目录未做任何修改
