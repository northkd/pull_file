# 中文 Nature 风格 LaTeX 稿

此工程为 Nature 风格的中文双栏排版稿，不是 Nature 官方模板。

## 编译

需要 XeLaTeX、Biber、TikZ、ctex/xeCJK，以及以下字体：

- Liberation Serif / Sans / Mono
- Noto Serif CJK SC
- Noto Sans CJK SC
- Noto Sans Mono CJK SC

执行：

```bash
latexmk -xelatex main.tex
```

## 主要文件

- `main.tex`：版式、摘要和文档入口
- `chapters/chapter1.tex`：主文、结果与讨论
- `chapters/chapter2.tex`：方法及声明
- `refs.bib`：参考文献
- `figures/*_tikz.tex`：可复现矢量图
