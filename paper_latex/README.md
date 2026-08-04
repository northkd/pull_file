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
现在的修改后的PDF和之前的PDF从根本上没有讲清楚这个工作是在干什么，pipeline中用到的各个模型在描述符筛选的流程中起到的实际作用是什么，一篇nature级别的文章这些工作原理和设计逻辑是要让外行人也能理解的，目前的内容显然没能做到。目前用到了多个算法，各个算法是用来解决什么问题的，这个算法之前是在哪个领域的起作用的，为什么现在应用到我工作中，选这个的优势，没选择别的原因，当前工作的目的是`寻找经过去混杂、稳定性校准和跨体系验证后仍然可解释的局域结构信号，而不是构建一个在训练集上性能最优但物理意义不透明的黑箱模型`那么这一目的会面临哪些问题，现在的pipeline是怎么解决的也要在文章中讲清楚
