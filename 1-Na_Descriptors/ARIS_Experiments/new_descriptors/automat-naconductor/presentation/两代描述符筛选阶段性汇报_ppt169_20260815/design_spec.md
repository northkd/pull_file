<!-- ppt-master-schema: design-spec/v1 -->
# 两代描述符筛选阶段性汇报 - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | 两代描述符筛选阶段性汇报（组会版） |
| Canvas Format | PPT 16:9, 1280 × 720 px |
| Page Count | 13 |
| Target Audience | 从事固态电解质设计、熟悉材料结构与离子输运问题，但不要求精通机器学习算法的课题组研究者。 |
| Communication Intent | 用材料筛选中的具体问题串起两代方法：第一轮做了什么、为什么还不能直接下结论、第二轮增加了哪些可理解的检查、目前能说到哪一步。 |
| Desired Audience Outcome | 听众能用材料研究语言复述两轮方法的差别，理解第二轮是在减少体系差异、重复信息和偶然高分，而不是单纯追求更复杂的算法。 |
| Core Message / Ask / Action | 第二轮的核心不是把模型做得更复杂，而是让每个候选结构量先经过“可比、可解释、可重复”的检查，再进入组合和材料机制讨论。 |
| Delivery Context | 课题组现场工作汇报：约20分钟正文，约5分钟问答附录；正文页面需要脱离讲稿也能看懂。 |
| Artifact Afterlife | 会后作为阶段性进展记录、算法核查依据和下一轮描述符验证工作的交接材料。 |
| Reading Mode | balanced |
| Content Strategy | 页面少术语、多解释句；精确代码口径放在问答附录，正文只保留听众需要理解的判断。 |
| Design Style | 冷白研究纸面、矿物青主轴、铜橙表示风险与未完成项；借鉴参考PPT的克制科研风格，不使用互联网产品化语言。 |
| Formula Policy | text-only |
| AI Image Acquisition Path | not applicable |
| Generation Mode | continuous |
| Spec Refinement | user-requested revision |
| Created Date | 2026-08-16 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | ppt169 |
| Dimensions | 1280 × 720 px |
| viewBox | `0 0 1280 720` |
| Margins | 左右48 px；顶部40 px；底部36 px |
| Content Area | x=48–1232；y=86–662；标题区与页脚区之外可用1184 × 576 px |

## III. Visual Theme

### Theme Style

- **Mode**: narrative
- **Visual style**: data-journalism
- **Theme**: 冷白研究纸面上的问题—检查—边界证据链。
- **Tone**: 审慎、材料问题优先、少用算法黑话；不把探索性结果包装成最终发现。

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #FFFFFF | 主纸面 |
| Secondary background | #EFF3F1 | 弱层级底色、解释区 |
| Primary | #113B4A | 标题、主轴、方法骨架 |
| Accent | #C75B39 | 风险、口径差异、未完成 |
| Secondary accent | #2E7D6E | 已建立的检查与可执行步骤 |
| Body text | #182229 | 正文与标签 |
| Rule / grid | #CFDAD7 | 分隔线与表格网格 |
| Muted text | #647176 | 边界、页脚与注释 |

## IV. Typography System

### Font Plan

| Role | Chinese | English | Fallback tail |
| --- | --- | --- | --- |
| Title | Songti SC | Georgia | serif |
| Body | PingFang SC | Arial | sans-serif |
| Data | PingFang SC | Georgia | serif |

- **Title stack**: Georgia, 'Songti SC', serif
- **Body stack**: Arial, 'PingFang SC', sans-serif
- **Data stack**: Georgia, 'PingFang SC', serif

### Font Size Hierarchy

| Purpose | Size (px) |
| --- | ---: |
| Body | 24 |
| Title | 42 |
| Subtitle | 32 |
| Lead | 30 |
| Annotation | 18 |
| Footnote | 16 |
| Page number | 14 |
| Data hero | 78 |

## V. Layout Principles

- **Header area**: 左上先给出本页问题或阶段，再给主标题；标题下用细规则线。
- **Content area**: 每页只保留一个主关系；用说明句解释图形，不让听众依赖讲稿才能看懂。
- **Footer area**: 左侧显示“强相关描述符筛选｜阶段性汇报”或“Q&amp;A附录”，右侧显示“NN / 13”。
- **Spacing**: 页面左右安全边距48 px；主要内容块间距24 px；故事转折页使用40 px留白。
- **Icon usage**: none。页面只使用文字、线、矩形、箭头和概念性流程图，不画真实晶体结构。

## VI. Icon Usage Specification

- **Library**: none

## VII. Visualization Reference List

| Page | Template | Path | Native-ready | Usage |
| --- | --- | --- | --- | --- |
| P03 | process_flow | templates/charts/process_flow.svg | n/a | 第一轮各个方法模块分别承担什么作用 |
| P06 | process_flow | templates/charts/process_flow.svg | n/a | 第二轮如何换样本并按材料意义限制组合 |
| P09 | comparison_table | templates/charts/comparison_table.svg | yes | A2与NaNa两代公式、单位和聚合方式对照 |
| P11 | pipeline_with_stages | templates/charts/pipeline_with_stages.svg | n/a | 问答中精确说明主程序的实际执行范围 |
| P12 | pyramid_chart | templates/charts/pyramid_chart.svg | n/a | 统计证据从当前可做检查到未见体系外推的层级 |
| P13 | pyramid_chart | templates/charts/pyramid_chart.svg | n/a | 冗余和空位的分层验证路线 |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

- **Image Policy**: none。全篇不使用外部照片、AI插图或装饰性晶体渲染；所有视觉解释使用原生SVG。

## IX. Content Outline

### Part 1: 20分钟正文｜从第一轮结果走到第二轮检查

#### Slide 01 - 高分不难，难的是知道它为什么高

- **Audience move**: 从期待一个最高相关系数，转向先追问相关性是否可信。

- **Title**: 高分不难，难的是知道它为什么高
- **Core message**: 相关性高不等于结构规律；要先排除体系、测量口径和晶体文件表达造成的假象。
- **Content**: 三条材料问题汇入“高相关”：跨NASICON/硫化物/卤化物是否稳定、体系差异拿掉后是否仍同向、名字和公式是否真是同一个物理量。

#### Slide 02 - 第一轮数据集现在是什么情况？

- **Audience move**: 先把第一轮正式数据口径说清楚，再进入方法改动，不展开数据集搭建过程。

- **Title**: 第一轮数据集现在是什么情况？
- **Core message**: 第一轮筛选已经在一百零三条材料记录和一百零三个CIF上完整运行；本次汇报聚焦方法升级，第二轮尚无新数据上的最终候选。
- **Content**: 大数字103；说明第一轮数据覆盖多种固态电解质体系，能够支持探索但样本量和测量口径仍有限；不展开第二轮数据集搭建细节。

#### Slide 03 - 第一轮怎样把结构量变成候选？

- **Audience move**: 从“算法给出一个分数”转向理解多个环节各自承担什么材料问题。

- **Title**: 第一轮怎样把结构量变成候选？
- **Core message**: 第一轮不是一个单独算法，而是几个环节配合：构造结构量、做相关与简单预测、自动尝试组合、反复抽样看稳定、按材料类别做留出检查。
- **Content**: 用材料语言解释每个环节的作用：候选构造回答“看哪些结构量”；相关与简单预测回答“有没有同向关系”；组合搜索回答“两个结构因素一起看是否更有解释力”；重复抽样回答“是不是偶然”；留出检查回答“换一个材料类别还能不能成立”。

#### Slide 04 - 第二轮如何回应两个材料学问题？

- **Audience move**: 把冗余和空位从重复提问转成两条具体的证据检查路线。

- **Title**: 第二轮如何回应两个材料学问题？
- **Core message**: 描述符重复和空位识别都不能只看一个分数，第二轮把信息来源和证据强弱分开检查。
- **Content**: 左侧“重复信息”从精确别名、共同计算来源到新数据相关；右侧“空位”从CIF占位、几何空腔到能量和动态验证；明确哪些已经能做、哪些仍是下一步。

#### Slide 05 - 第二轮第一步：先把体系差异拿掉

- **Audience move**: 用“不同起跑线”的直观图理解为什么先比较体系内部。

- **Title**: 第二轮第一步：先把体系差异拿掉
- **Core message**: 不把“材料属于哪一类”误认为“结构量本身有作用”。
- **Content**: 先在NASICON、硫化物、卤化物内部比较，再汇总不能由体系类别解释的剩余趋势；页面用完整句解释“为什么全样本混在一起会误判”；边界写明仍未控制致密度、烧结和测试方法。

#### Slide 06 - 第二轮怎样组合描述符？

- **Audience move**: 从“多试公式”转向理解“按材料意义挑类型、按量纲定组合”。

- **Title**: 第二轮怎样组合描述符？
- **Core message**: 第一轮是先列出大量公式再挑高分；第二轮先按材料意义选不同类型的结构量，再只组合有物理解释、单位也说得通的形式。
- **Content**: 用“换一半样本重新选—按局域配位/网络/骨架/组成分组—允许加乘除且检查量纲—复查靠前组合”的流程解释；正文不用bootstrap、top_k、LOSO和稀疏选择术语。

#### Slide 07 - 目前能说到哪一步？

- **Audience move**: 从期待第二轮已经产出最终候选，转向区分已经能做、正在补和还不能说的结论。

- **Title**: 目前能说到哪一步？
- **Core message**: 第二轮的筛选框架已经建立，但还没有新数据上的最终候选，也还不能宣称跨体系外推。
- **Content**: 三块文字：已经能做（体系内比较、换样本、受约束组合）；正在补（描述符定义核对、重复信息自动识别）；还不能说（新数据结论、完全未见体系预测）。

### Part 2: 5分钟问答附录｜精确口径

#### Slide 08 - Q1｜第一轮到底是103条，还是84条？

- **Audience move**: 区分正式主数据和目录中的历史缓存。

- **Title**: Q1｜第一轮到底是103条，还是84条？
- **Core message**: 第一轮正式口径是103条记录和103个CIF；84行是第二代目录中的历史输入/特征缓存，不能替代第一轮主数据。

#### Slide 09 - Q2｜A2和NaNa为什么不能跨代对应？

- **Audience move**: 从同名即同量转向核对公式、单位、聚合方式和数据依赖。

- **Title**: Q2｜A2和NaNa为什么不能跨代对应？
- **Core message**: 两代同名量在公式、单位、聚合方式和数据依赖上都发生了变化，必须重新实现和检验。

#### Slide 10 - Q3｜0.793和41→38分别代表什么？

- **Audience move**: 防止把历史模型性能或入口数量误读为第二轮发现。

- **Title**: Q3｜0.793和41→38分别代表什么？

- **Core message**: 0.793是第一代历史模型性能，41→38是代码入口状态，两者都不是第二轮新结果。

#### Slide 11 - Q4｜主程序实际执行到哪一步？

- **Audience move**: 区分一键主程序和需要单独运行的审计工具。

- **Title**: Q4｜主程序实际执行到哪一步？
- **Core message**: 一键主程序当前只有Stage 0–4；数据校验、室温选择、写法敏感性和数值指纹是独立工具。

#### Slide 12 - Q5｜为什么统计证据仍是探索性的？

- **Audience move**: 理解现有检查能减少误判，但还没有覆盖选择过程和未见体系外推。

- **Title**: Q5｜为什么统计证据仍是探索性的？
- **Core message**: 当前检查能减少误判，但选择不确定性和完全未见体系的验证仍未补齐。

#### Slide 13 - Q6｜下一步怎样验证才够？

- **Audience move**: 从寻找万能判据转向接受分层证据和三道正式运行门槛。

- **Title**: Q6｜下一步怎样验证才够？
- **Core message**: 冗余和空位都要从低成本线索逐层走向更强证据，同时补齐主检验、重复信息识别和跨体系验证三道门。

## X. Speaker Notes Requirements

- **Filename**: match each SVG filename under `notes/`
- **Content**: 每页写完整口语化讲法与自然过渡；正文少术语，附录给出精确代码/文件口径。拆分备注文件不使用Markdown标题行。
- **Total duration**: 约25分钟；P01–P07约20分钟，P08–P13为5分钟问答附录，可按追问选择性展示。
- **Notes style**: conversational，材料研究语言优先；每页按“问题—原因—本步解决—仍存边界”讲述。
