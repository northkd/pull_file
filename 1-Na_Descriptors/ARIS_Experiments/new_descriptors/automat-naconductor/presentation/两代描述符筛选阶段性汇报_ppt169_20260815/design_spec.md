<!-- ppt-master-schema: design-spec/v1 -->
# 两代描述符筛选阶段性汇报 - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | 两代描述符筛选阶段性汇报（组会版） |
| Canvas Format | PPT 16:9, 1280 × 720 px |
| Page Count | 12 |
| Target Audience | 从事固态电解质设计、熟悉材料结构与离子输运问题，但不要求精通机器学习算法的课题组研究者。 |
| Communication Intent | 用材料筛选中的具体问题串起两代方法：第一轮做了什么、跑完发现什么问题，每个问题后紧跟第二轮怎么解决，让听众看到完整的逻辑链条而不是先抛问题再层层展开。 |
| Desired Audience Outcome | 听众能用材料研究语言复述每个问题对应的解法，理解第二轮的每一步都是针对第一轮的具体误判，而不是单纯追求更复杂的算法。 |
| Core Message / Ask / Action | 第二轮的每一步都对应第一轮暴露的一个具体问题：全样本混比→扣体系差异；测量标准不统一→分表记录；候选评价同批→封版+限制组合；名实不符→身份证+等价写法探针；空位只靠CIF→分层验证。 |
| Delivery Context | 课题组现场工作汇报：约20分钟正文，约5分钟问答附录；正文页面需要脱离讲稿也能看懂。 |
| Artifact Afterlife | 会后作为阶段性进展记录、算法核查依据和下一轮描述符验证工作的交接材料。 |
| Reading Mode | balanced |
| Content Strategy | 页面少术语、多解释句；精确代码细节放在问答附录，正文只保留听众需要理解的判断。 |
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
| Accent | #C75B39 | 风险、标准差异、未完成 |
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
- **Footer area**: 左侧显示“强相关描述符筛选｜阶段性汇报”或“Q&amp;A附录”，右侧显示“NN / 12”。
- **Spacing**: 页面左右安全边距48 px；主要内容块间距24 px；故事转折页使用40 px留白。
- **Icon usage**: none。页面只使用文字、线、矩形、箭头和概念性流程图，不画真实晶体结构。

## VI. Icon Usage Specification

- **Library**: none

## VII. Visualization Reference List

| Page | Template | Path | Native-ready | Usage |
| --- | --- | --- | --- | --- |
| P02 | process_flow | templates/charts/process_flow.svg | n/a | 第一轮流程简述（103 CIF → 提取结构量 → 35 候选 → 重复抽样 → 留出检查） |
| P04 | comparison_table | templates/charts/comparison_table.svg | yes | 第一轮五个问题与第二代解法、现状对照 |
| P05 | comparison_table | templates/charts/comparison_table.svg | yes | 第一轮 vs 第二代组合描述符方式对比 |
| P07 | comparison_table | templates/charts/comparison_table.svg | yes | A2 与 NaNa 两代公式、单位和聚合方式对照 |
| P08 | pipeline_with_stages | templates/charts/pipeline_with_stages.svg | n/a | 问答中精确说明主程序的实际执行范围 |
| P10 | pyramid_chart | templates/charts/pyramid_chart.svg | n/a | 冗余证据从精确别名到数据相关的强弱层级 |
| P11 | pyramid_chart | templates/charts/pyramid_chart.svg | n/a | 空位分层验证路线（几何→键价→DFT→AIMD） |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

- **Image Policy**: none。全篇不使用外部照片、AI插图或装饰性晶体渲染；所有视觉解释使用原生SVG。

## IX. Content Outline

### Part 1: 20分钟正文｜从第一轮结果走到第二轮检查

#### Slide 01 - 这次要解决的不是"谁的相关系数最高"

- **Audience move**: 从期待一个最高相关系数，转向先追问相关性是否可信。
- **Title**: 这次要解决的不是"谁的相关系数最高"
- **Core message**: 找到高分描述符不难，难的是确认它反映的是材料结构，而不是材料体系、数据记录方式或 CIF 写法。
- **Content**: 三个目标：找稳定相关的结构量；扣掉体系差异后是否还在；名字公式和实际算的数是否一致。

#### Slide 02 - 第一轮做了什么，跑完以后发现了什么问题

- **Audience move**: 先看第一轮流程，再直接看到跑完暴露的五个问题，把"全样本混在一起比"等弊端归到第一轮。
- **Title**: 第一轮做了什么，跑完以后发现了什么问题
- **Core message**: 第一轮跑通了完整流程，但跑完暴露五个问题：全样本混比、测量标准不统一、候选评价同批数据、名实不符、空位只靠 CIF。
- **Content**: 上半页简述第一轮流程（103 CIF → 提取结构量 → 35 候选 → 重复抽样 → 留出检查）；下半页五个问题表格，每条说清具体表现。第一轮的合理之处也点明。

#### Slide 03 - 两条线并行，规则先于数据定死

- **Audience move**: 理解为什么要重做算法，以及为什么规则要在数据到来前冻结；此页不展开第二代具体解法。
- **Title**: 两条线并行，规则先于数据定死
- **Core message**: 第一轮的问题不能靠加数据解决；数据线搭新数据集，算法线重建规则；规则在看到数据前定死，否则相关性虚高且无法补救。
- **Content**: 双线时间轴；强调"先封版再进数据"是设计不是延误。

#### Slide 04 - 第二代怎么解决这五个问题

- **Audience move**: 直接看每个问题对应的解法，不先抛问题再层层展开。
- **Title**: 第二代怎么解决这五个问题
- **Core message**: 对应第一轮五个问题逐条给解法，文字直说，每条标注现在能做到哪一步。
- **Content**: 五行表格（问题 → 解法 → 现状）：全样本混比→扣体系平均；测量标准→新数据表分记；候选评价同批→封版+限制组合；名实不符→身份证+等价写法探针；空位→四层分层方案。

#### Slide 05 - 第二代怎样组合描述符

- **Audience move**: 从"多试公式挑高分"转向"按材料意义限制再组合"，用直白例子说明。
- **Title**: 第二代怎样组合描述符
- **Core message**: 第一轮穷举 7000 公式挑高分；第二代先按材料意义分组挑代表，只允许有物理意义的加减乘除，检查量纲。
- **Content**: 第一轮 vs 第二代对比表；直白举例（局域配位配网络配骨架，长度加长度可以、长度加无量纲数不行）；诚实说明统计去重和嵌套外推还没做。

#### Slide 06 - 目前能说到哪一步

- **Audience move**: 区分已经能做、正在补、还不能说的结论。
- **Title**: 目前能说到哪一步
- **Core message**: 框架已建，零真实数据结果；不能说复现第一代的数，不能说预测未见体系。
- **Content**: 三块文字：已经能做（描述符计算、扣体系主排序、换样本、受约束组合、分体系检查）；正在补（205 身份字段、LOSO、p 值计算方式、相关簇去重）；还不能说（新数据结果、复现 0.597、跨体系外推）。

### Part 2: 5分钟问答附录｜精确细节

#### Slide 07 - 附录一｜数据量对不上，同名量也不能跨代比

- **Audience move**: 区分正式主数据和目录缓存；理解同名量跨代不对应。
- **Title**: 数据量对不上，同名量也不能跨代比
- **Core message**: 正式数据 103 条；84 是历史缓存。两代同名量（A2/NaNa）公式单位聚合都不同，历史相关系数不能跨代搬。
- **Content**: 103 vs 84 澄清；历史七类分布；第一代局域宽松因子（A2）是无量纲比值，第二代是最长键长均值（埃），不是同一个量；位点连通量（NaNa）第一代跨样本百分位秩，第二代单结构近似。

#### Slide 08 - 附录二｜0.793 是怎么回事，主程序到底跑到哪

- **Audience move**: 防止把历史模型性能误读为第二轮发现；区分一键主程序和独立审计工具。
- **Title**: 0.793 是怎么回事，主程序到底跑到哪
- **Core message**: 0.793 是第一代模型预测性能不是组合描述符相关；主程序只到第0-4步，数据校验/写法探针/指纹是独立工具。
- **Content**: 0.793 来自机器学习模型（ExtraTrees）交叉验证的秩相关系数，是模型性能不是组合描述符；主程序五步流程；独立工具列表。

#### Slide 09 - 附录三｜冗余能识别到什么程度，统计证据为什么还只能算探索性

- **Audience move**: 理解冗余从精确别名到数据相关的强弱顺序；理解统计证据为何仍是探索性。
- **Title**: 冗余能识别到什么程度，统计证据为什么还只能算探索性
- **Core message**: 冗余四档从强到弱，相关簇去重没实现；留一体系被删是关键缺口，结果标探索性。
- **Content**: 冗余四档（精确别名→共用底层→同数学形式→数据相关）；探索性原因（选择不确定性+外推未覆盖）。

#### Slide 10 - 附录四｜空位探针证明了什么，低成本方案缺在哪

- **Audience move**: 理解占位拆分检验证明的是写法敏感不是空位准确率；理解分层方案各层当前状态。
- **Title**: 空位探针证明了什么，低成本方案缺在哪
- **Core message**: 占位拆分检验证明描述符对结构文件写法敏感，不等于测了程序找钠空位准不准；几何方法没接后端、键价能垒缺可执行文件、高成本计算要算力。
- **Content**: 占位拆分检验操作与证明/未证明边界；低成本方案四层当前状态。

#### Slide 11 - 附录五｜"扣体系差异后的排序相关"到底是怎么算的

- **Audience move**: 理解主量的准确算法和它与标准偏秩相关的区别。
- **Title**: "扣体系差异后的排序相关"到底是怎么算的
- **Core message**: 程序里叫"线性残差的秩相关"，不是标准偏秩相关；不能自动控致密度。
- **Content**: 算法步骤（体系分组控制→扣线性可解释部分→剩余算秩相关）；与标准偏秩相关的区别；局限性。

#### Slide 12 - 附录六｜补齐哪些缺口，结果才能写进论文

- **Audience move**: 接受分层证据和三道正式运行门槛。
- **Title**: 补齐哪些缺口，结果才能写进论文
- **Core message**: 冗余空位分层走；补齐主检验统计显著性、相关簇去重、留一体系验证三道门，之前结果不进论文结论。
- **Content**: 两条分层路线；三道门；结论门槛。

## X. Speaker Notes Requirements

- **Filename**: match each SVG filename under `notes/`
- **Content**: 每页写完整口语化讲法与自然过渡；正文少术语，附录给出精确代码/文件细节。拆分备注文件不使用Markdown标题行。
- **Total duration**: 约25分钟；P01–P06约20分钟，P07–P12为5分钟问答附录，可按追问选择性展示。
- **Notes style**: conversational，材料研究语言优先；每页按“问题—原因—本步解决—仍存边界”讲述。
