<!-- ppt-master-schema: spec-lock/v1 -->
# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## communication
- audience: 从事固态电解质设计、熟悉材料结构与离子输运问题，但不要求精通机器学习算法的课题组研究者
- objective: 第一轮做了什么、跑完发现什么问题，每个问题后紧跟第二轮怎么解决，让听众看到完整逻辑链条
- core_message: 第二轮每一步都对应第一轮暴露的一个具体问题：全样本混比→扣体系差异；测量标准不统一→分表记录；候选评价同批→封版+限制组合；名实不符→身份证+等价写法探针；空位只靠CIF→分层验证
- consumption_mode: balanced

## mode
- mode: narrative

## visual_style
- visual_style: data-journalism

## colors
- background: #FFFFFF
- secondary_bg: #EFF3F1
- primary: #113B4A
- accent: #C75B39
- secondary_accent: #2E7D6E
- body_text: #182229
- rule_grid: #CFDAD7
- muted_text: #647176

## typography
- font_family: Arial, 'PingFang SC', sans-serif
- title_family: Georgia, 'Songti SC', serif
- body_family: Arial, 'PingFang SC', sans-serif
- data_family: Georgia, 'PingFang SC', serif
- body: 24
- title: 42
- subtitle: 32
- lead: 30
- annotation: 18
- footnote: 16
- page_number: 14
- data_hero: 78

## icons
- library: none
- inventory: none

## page_rhythm
- P01: anchor
- P02: dense
- P03: breathing
- P04: anchor
- P05: breathing
- P06: anchor
- P07: dense
- P08: dense
- P09: dense
- P10: anchor
- P11: dense
- P12: anchor

## pptx_structure
- mode: flat
- template_reuse_scope: style

## page_charts
- P02: process_flow
- P04: comparison_table
- P05: comparison_table
- P07: comparison_table
- P08: pipeline_with_stages
- P10: pyramid_chart
- P11: pyramid_chart

## forbidden
- Mixing icon libraries
- Using any icons; the confirmed icon library is none
- External photographs, AI-generated images, decorative crystal renders, or any structure sketch that could be mistaken for a real crystal structure
- Presenting first-generation historical scores as second-generation results or as a single A2×NaNa descriptor correlation
- Calling rank_corr_of_linear_residuals a standard partial Spearman
- Drawing unimplemented Zeo++, BVSE, correlation-cluster selection, or LOSO capability as completed
- Internet-company language such as “数据线、算法线、问题暴露、手写组合” in visible slide text
- Repeating equal-width card grids as the default page structure
- Decorative gradients, heavy shadows, glow effects, or rainbow chart palettes
- `mask`, `<style>`, `class`, external CSS, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<set>`, `<script>` / event attributes, `<iframe>`
- HTML named entities in text; write typography as raw Unicode and escape XML reserved characters
