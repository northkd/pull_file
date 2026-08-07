# codex/naconductor-repair 中文单栏批注稿（模型逻辑重写版）

本手稿依据 `codex/naconductor-repair` 分支的实际代码逻辑重写。文章围绕结构描述符 `X`、材料体系/阴离子背景 `Z` 与离子电导率 `Y` 的关系，解释 Pipeline 中各模型分别排除哪一种假发现来源。

## 本版重点

- 不再按代码 Stage 简单罗列算法，而是按科学困难组织正文；
- 区分 Ridge 在去混杂和折外验证中的两种职责；
- 解释 Lasso 只用于稳定选择，Spearman 只用于单调方向；
- 结合 Na 配位、Na--Na 网络、空位、材料体系和 `log_sigma` 解释模型；
- 比较未采用 OLS、RF/XGBoost、GNN、单次 Lasso 和无界符号回归的原因；
- 说明 LOSO、阴离子分层和重复子采样分别回答不同问题；
- 明确 V1--V4、双轨隔离和后续 AIMD/实验验证的证据边界；
- 当前 CIF 不可用，因此所有散点图均为方法示意，不是材料学结果。

## 排版

- A4 单栏；
- 正文右侧保留约 58 mm 空白批注区；
- 每 5 行显示一次行号；
- 图件全部由 TikZ 源码生成。

## 编译

需要 XeLaTeX、Biber、TikZ、ctex/xeCJK，以及 Liberation 与 Noto CJK 字体。

```bash
latexmk -xelatex main.tex
```

GitHub Actions 输出：

```text
Na_conductor_repair_annotation_CN.pdf
```
