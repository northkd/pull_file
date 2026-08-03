# codex/naconductor-repair 中文单栏批注稿

此工程依据 `codex/naconductor-repair` 分支的实际代码逻辑重写，采用接近 Nature Article 的中文稿件结构，但不是 Nature 官方模板。

## 排版特点

- A4 单栏；
- 正文右侧保留约 58 mm 空白批注区；
- 每 5 行显示一次行号，便于纸面定位；
- 图件全部由 TikZ 源码生成；
- 正文明确区分软件验证与真实材料学结果。

## 编译

需要 XeLaTeX、Biber、TikZ、ctex/xeCJK，以及：

- Liberation Serif / Sans / Mono
- Noto Serif CJK SC
- Noto Sans CJK SC
- Noto Sans Mono CJK SC

执行：

```bash
latexmk -xelatex main.tex
```

输出文件在 GitHub Actions 中重命名为：

```text
Na_conductor_repair_annotation_CN.pdf
```
