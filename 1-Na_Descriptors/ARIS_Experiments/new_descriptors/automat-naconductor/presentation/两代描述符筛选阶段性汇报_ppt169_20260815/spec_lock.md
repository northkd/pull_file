<!-- ppt-master-schema: spec-lock/v1 -->
# Execution Lock

## canvas
- viewBox: 0 0 1280 720
- format: PPT 16:9

## communication
- audience: 从事固态电解质设计、熟悉材料结构与离子输运问题，但不要求精通机器学习算法的课题组研究者
- objective: 用材料问题解释两轮描述符筛选为何不同，使听众理解第二轮增加的检查及其边界
- core_message: 第二轮升级的核心是先确认结构量可比、可解释、可重复，再谈组合和高分
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
- P02: breathing
- P03: dense
- P04: anchor
- P05: breathing
- P06: dense
- P07: anchor
- P08: dense
- P09: dense
- P10: anchor
- P11: dense
- P12: dense
- P13: anchor

## pptx_structure
- mode: flat
- template_reuse_scope: style

## page_charts
- P03: process_flow
- P06: process_flow
- P09: comparison_table
- P11: pipeline_with_stages
- P12: pyramid_chart
- P13: pyramid_chart

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
