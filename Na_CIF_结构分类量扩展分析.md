# 晶态 Na 固态离子导体的 CIF 可复现结构分类量：扩展候选图谱与文献启发审计

> 版本：2026-08-17（公开文献检索截止 2026-08-17）  
> 研究用途：在不预设与室温离子电导率有关的前提下，冻结一批定义清楚、可由 CIF 批处理、可跨 NASICON／硫化物／卤化物等体系检验的结构分类假说。

## 摘要结论

这次扩展不再把问题限制为“再找几个已经在 Li 中成功的描述符”，而是把一个 CIF 拆成若干可复现的数学对象，再从每个对象系统地产生候选分类。核心对象包括：带晶格平移标签的周期 Na 图、Voronoi／BVSE 空隙网络、带局域环境颜色的 Na 图、去 Na 后的骨架与多面体图、无序轨道图、对称群关系、刚性单元约束图以及静态能量子水平集。

本文最终给出的不是一张“已知有利规则”表，而是一张**待审计候选宇宙**。候选是否与 `log10(sigma_RT)` 有关，留给 Na 数据决定；文献在这里主要用于三件事：证明计算对象有成熟定义、指出容易与已有量撞车的地方、为尚未做过电导率关联检验的组合分类提供物理启发。

必须先强调四点：

1. “本轮没有找到直接先例”不等于数学意义上的世界首创。本文用分级证据状态，不使用绝对的“从未有人做过”。
2. 静态、已占据的 Na–Na 邻接图只是 `static occupied-Na candidate graph`，不自动等于真实迁移图。最好同时构造占据位图、几何空隙图与 BVSE 图，检查结论是否跨表示成立。
3. 所有周期拓扑量都必须在**带整数晶格平移标签的商图**上定义；`3×3×3` 或 `5×5×5` 超胞只能用于一致性测试，不能取代定义。
4. 候选多的目的不是把所有变量一起塞进显著性检验。鉴于分体系后可用样本约 50–60 个，本文采用**严格 design-rule 单轨**：先在不看电导率的前提下做条件式可操作性、体系内类别普查、参数/构造一致性和数据可得性审计；候选池先保留 8–10 条作为损耗余量，最终主检验严格控制在 5–6 条。其余 mechanistic 候选全部进入探索层，用 FDR 控制，结论只表述为“值得后续检验”。

## 0. 本地对话上下文对本报告的约束

根据 `Claude.html` 中前一轮讨论，本项目不是从零开始的普通描述符搜索，而有几项很具体的约束：

`Claude_files/` 也已检查；其中主要是离线网页的 CSS/JavaScript、保存资源和隔离 frame，未发现独立 CIF、描述符表或另一份需要单独合并的研究结论，实质对话上下文仍以 `Claude.html` 为准。

- 研究目标是用 CIF 结构量解释/检验 Na 固态离子导体室温 `log10(sigma)`，并显式控制 NASICON、硫化物、卤化物等 `system`。
- 旧的 84-CIF 数据集已被判定不可继续作为正式验证集；当前顺序应是**先冻结定义和代码，再接触新的电导标签**。
- 现有代码中的 `network_dimension` 实际上更接近最大连通分量比例，并不是真正的周期平移秩。任何基于它继续派生的环、冗余、割点结论都必须暂停，直到 translation-labelled graph 修好。
- 前一轮已经覆盖渗流维度、多面体共角/共边/共面、可转动多阴离子、BVSE、几何瓶颈、阴离子堆积、对称性、部分占位和间隙/空位；本文尽量新增它们的组织关系，而不是简单换名字。
- R1/R2/R3 分别指对象非唯一、参数依赖和 CIF 来源完整性风险；它们不是“重要性等级”。优先级 A/B/C/X 另行给出。
- 静态结构分类是否有物理含义与算法是否稳定是两道不同的门。即使标签在所有 cutoff 下稳定，也可能只是错误的迁移图表示。

## 1. 本文的边界与术语

### 1.1 纳入范围

- 主要输入是公开或自有的晶态材料 CIF。
- 可以调用标准元素表、离子半径、键价参数、空间群程序、Voronoi/CAVD、BVSE 和刚性矩阵等确定性工具。
- 不要求 DFT、NEB、AIMD 或实验谱学才能得到主标签；这些可用于事后物理校准。
- 分类优先采用二元或少量离散取值；连续量只用于生成有先验意义的顺序、拓扑事件或参数稳定平台，不允许根据电导率挑阈值。
- 目标对象是 Na 固态离子导体，但不少定义也可迁移到 Li、K、Mg 等体系。

### 1.2 不纳入或仅作校准的对象

- 由 MD 轨迹得到的真实跳频、相关运动、Haven ratio、path entropy。
- 由声子或弹性张量得到的真实软模、剪切模量和介电响应。
- 由 NEB/DFT 得到的精确迁移势垒或缺陷形成能。
- 平均 CIF 无法恢复的短程有序、相邻占位相关、瞬态多面体重排。

### 1.3 输入等级

| 等级   | 含义                                                         |
| ------ | ------------------------------------------------------------ |
| **I0** | CIF 坐标、元素、晶格与空间群即可；不需要氧化态或外部模型。   |
| **I1** | I0 + 标准元素表、氧化态推断、离子/共价半径或键价参数。       |
| **I2** | I0/I1 + 确定性派生模型，如 CAVD、BVSE、刚性矩阵、原型/拓扑数据库。仍不需要 DFT/MD。 |
| **I3** | 依赖 CIF 中常被省略或质量不一的信息，如可靠部分占位、split sites、ADP、测量温度或已知母相。 |

### 1.4 可靠性风险

每项风险按 `R1/R2/R3` 记为低（L）、中（M）、高（H）：

- **R1：对象非唯一风险。** 例如“哪一个空隙才是化学真实间隙位”、环基选择、刚体单元划分没有唯一真值。
- **R2：参数依赖风险。** 对象定义清楚，但依赖 cutoff、`symprec`、探针半径、配位规则或能量容差。
- **R3：CIF 来源风险。** 平均占位、无序、遗漏 H、精修坐标/ADP 质量会决定结果，算法无法完全补救。

### 1.5 文献/先例状态

| 代码   | 含义                                                         |
| ------ | ------------------------------------------------------------ |
| **D**  | 已有固态离子导体工作直接使用同一或实质等价概念，并检验迁移/电导；不能作为“全新量”宣传。 |
| **N**  | 有很近的机制、单材料/单家族、Li-only、动态轨迹或不同实现先例；精确定义仍可作为 Na 跨体系假说。 |
| **M**  | 成熟方法来自晶体拓扑、孔材料、信息论或刚性理论，但本轮未找到它被系统用于 Na-SSE 电导分类。 |
| **U?** | 本轮有针对性的公开文献检索未找到直接或足够近的先例；只是可审计的检索结论，不是绝对新颖性保证。 |

复合写法表示两个层级，例如 `M/U?` 是“底层数学/晶体学方法成熟，但精确的 SSE 离散分类与电导检验未找到”，`N/U?` 是“有相邻机制或构件先例，但精确构造未找到”。

## 2. 统一的计算对象

### 2.1 带平移标签的周期图

把一个周期网络写成有限商图

\[
Q=(V,E,\gamma),\qquad \gamma(e)\in\mathbb Z^3,
\]

其中 `gamma(e)` 记录一条边跨越的晶格平移。对闭合游走 `C`，其净平移为

\[
\tau(C)=\sum_{e\in C}\gamma(e).
\]

若平移商图不连通，先写成 `Q=⊔_alpha Q_alpha`。每个连通分量各有同调到平移格的映射

\[
\tau_\alpha:H_1(Q_\alpha,\mathbb Z)\rightarrow T,
\qquad L_\alpha=\operatorname{im}\tau_\alpha,
\qquad D_\alpha=\operatorname{rank}_\mathbb Z L_\alpha.
\]

长程网络维度应报告组件谱 `{D_alpha}`；若必须压成一个数，只取 `D_max=max_alpha D_alpha`。禁止把互不连通分量的 `e_x/e_y/e_z` gains 合并成一个假的 3D 网络。

这里的 `Q` 默认是按**纯平移群 `T`** 取商：`V` 是一个平移原胞内的实际候选 sites，而不是直接把整个 Wyckoff orbit 压成一个节点。空间群随后用于把这些 sites/edges 分成对称轨道。若要直接以 Wyckoff orbit 作最小节点，则边标签必须升级为完整 symmetry-labelled quotient graph，不能只留 `Z^3` 平移向量。

定向反边满足 `gamma(e_bar)=-gamma(e)`。改变顶点代表元 `phi:V→Z^3` 时，

\[
\gamma^\phi(u\to v)=\gamma(u\to v)+\phi(u)-\phi(v),
\]

换晶格基 `B'=BU`、`U∈GL(3,Z)` 时 gains 只作相应坐标协变。最终标签必须对 switching、原点、原子排序和 `GL(3,Z)` 换基不变；平行边和 gain self-loops 不得在简图化时丢失。

该表示也是后文路径冗余、方向耦合、环同调、组件谱和轨道删除试验的共同底座。周期迁移图和商图的必要性已有成熟算法文献；例如 [Shen 等的周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) 与 [Gao 等的晶体网络维度/重数算法](https://www.nature.com/articles/s41524-020-00409-0)。

### 2.2 至少并行构造五张图

| 图          | 节点                                                    | 边                                                      | 它回答的问题                       |
| ----------- | ------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------- |
| `G_occ`     | 平移原胞内 CIF 报告的 Na sites（附占位与 Wyckoff 标签） | 冻结的 Na–Na/共享面/几何可达判据                        | 已占据 Na 子晶格怎样组织？         |
| `G_void(r)` | Voronoi/CAVD 空隙节点                                   | 对半径 `r` 探针可通过的喉道                             | 纯几何自由空间怎样随探针半径变化？ |
| `G_bvse(E)` | BVSE 极小点/网格盆地                                    | minimax critical barrier/bottleneck 值不高于 `E` 的连通 | 静态键价能量景观怎样随能阈值贯通？ |
| `G_host`    | 去 Na 后的原子、强键或刚性多面体                        | 冻结成键/共享规则                                       | 宿主骨架的拓扑和柔性约束怎样组织？ |
| `G_col`     | `G_occ` 或 `G_void` 的节点                              | 同上，但节点/边附 CN、Wyckoff、化学与能量标签           | 长程路径是否必须切换局域环境？     |

[CAVD](https://pmc.ncbi.nlm.nih.gov/articles/PMC7244509/) 已展示如何用 radical Voronoi 分解把空隙映射为带间隙、通道和瓶颈的网络；[Zeo++ 的周期 Voronoi 方法](https://doi.org/10.1016/j.micromeso.2011.08.020) 则说明同一类工具可以计算可达空隙和自由球尺度。它们证明对象可算，不证明下文每个离散分类都与 Na 电导有关。

## 3. 候选分类总表

以下每个候选都先给操作性定义和建议离散取值。`优先级 A` 表示最值得先进入冻结候选池；`B` 表示储备；`C` 表示高探索性或较易共线；`X` 表示更适合负对照/质量控制。

### 3.1 周期 Na 图：不再只问“几维”，而问各方向如何被组织

这一族建立在同一个 `G_occ` 或经独立物理校准的候选迁移图上。它们有意避开前一轮已经提出的普通路径冗余、二分图、degree regularity、single-orbit percolation 和原始 cycle rank。

凡涉及 filtration，先把原始距离、clearance 或能量阈值重参数化为“边只增加”的离散 inclusion step `s`；“首次/更早”均指该偏序中的最早 step，而不是直接比较可能方向相反的原始半径或能量数值。同一阈值的边必须整批加入。

凡下表使用 node/edge orbit 或“图自同构”时，默认群不是不受约束的完整抽象 `Aut(G_tilde)`，而是保持平移作用与全部冻结标签的 gain-compatible 群

\[
\operatorname{Aut}_T(\widetilde G,\ell)
=N_{\operatorname{Aut}(\widetilde G,\ell)}(T),
\]

等价地由满足 gain compatibility 的三元组 `(sigma,U,phi)` 表示。逐 lift component 分析时再取该 component 的 setwise stabilizer `H_alpha` 与 deck lattice `L_alpha`；所有 orbit 都在 `H_alpha` 下计算，不能让一个 edge orbit 横跨两个不同的 `Q_alpha`。若研究问题只允许真实晶体空间群，则预先把 `H_alpha` 换成其 crystallographic subgroup，并将两套答案分开报告。

| ID       | 分类量                                              | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | --------------------------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **PG01** | **最小满秩跳跃轨道基**                              | 在单个连通分量 `Q_alpha` 内，把 `H_alpha` 下等价边合为 hop orbit，求保持 `D_alpha` 所需的最少轨道数 `h_min`；分 `1 / 2 / 3 / ≥4`。删除一个 orbit 是相关删除其所有平移/对称副本，不是单缺陷。 | I0；L/M/L；U?      | A      |
| **PG02** | **跳跃轨道删除秩降谱**                              | 在每个 `Q_alpha` 内逐个删除 `H_alpha` 下的 hop orbit，记录 `Delta D_alpha=0/1/≥2` 多重集；分“无单轨道控制 / 单方向关键轨道 / 多方向共同关键轨道”。 | I0；L/M/L；N       | A      |
| **PG03** | **Z2 平移余同调最小支撑谱**                         | 对实际可达格 `L_alpha` 的每个非零 parity character `a`，求对应 `H^1(Q_alpha;F2)` 类在冻结 edge-orbit 支撑意义下的 cosystole `w(a)`；输出排序整数谱。它不是最短路径长度，也不直接等于普通 cut-width。 | I0；M/M/L；M/U?    | A      |
| **PG04** | **独立方向 edge-orbit-disjoint cycle packing**      | 在同一个 `Q_alpha` 内，求 gains 在 `L_alpha⊗Q` 中线性独立、且不共享 `H_alpha` quotient edge orbit 的简单 winding cycles 最大数；另报 vertex-orbit 版本。它表示不同方向是否共用 hop orbit，不等于 lift 中几何路径绝不相交。 | I0；M/M/L；M/U?    | A      |
| **PG05** | **elementary-cycle 可达格基指数**                   | 在 `D_alpha` 个独立简单 winding cycles 中最小化 `[L_alpha:<tau(C1),…,tau(CD)>]`；分 `1 / 2–4 / >4`。PG05 问简单环能否构成**实际可达格**的基，PG06 另问该可达格在 ambient translation lattice 中是否饱和。 | I0；M/M/L；M/U?    | A      |
| **PG06** | **平移子格 Smith 正规形**                           | 若 `rank(T)=d`、`SNF(L_alpha)` 的非零因子为 `d1|...|dr`，输出 `(r;d1,...,dr)` 与 saturation index `s=[sat_T L_alpha:L_alpha]=prod_i di`；再用两个正交轴标 `full/lower rank` 与 `saturated/unsaturated`。降秩和非饱和可同时发生，不能做互斥三分类；仅 `r=d` 时 `[T:L_alpha]=s` 为有限 component multiplicity。 | I0；L/M/L；M/N     | A      |
| **PG07** | **infinite-lift block-orbit 稳定子秩谱**            | 对每个 `D_alpha>0` 的连通无限 lift 取标准 maximal vertex-biconnected blocks（桥按 `K2` block 处理）；`L_alpha` 对 blocks 的作用给出 canonical block orbits。对代表 `B` 定义 `T_B={t∈L_alpha:tB=B}`、`d_[B]=rank(T_B)`，输出 `(block类型,d_[B])` 的轨道多重集，并标是否所有 block 都是 rank 0；若结构所有 `D_alpha=0`，结构级输出冻结为 `no-infinite-lift-component`，使 core 分析不因定义域为空而删样本。不得把单个 block、block orbit 与其平移饱和并集混成同一对象；普通 quotient Tarjan 也不能代用。 | I0；M/M/L；M/U?    | A      |
| **PG08** | **满秩 periodic k-core 持久度**                     | 按 edge germs 计 degree（self-loop 贡献 2），周期同步剥除 degree `<k` 节点；每轮逐分量求 rank，定义仍含 `D_alpha` 分量的最大 `k_D` 与秩衰减词。 | I0；L/M/L；M/U?    | A      |
| **PG09** | **gain-compatible Cartesian 素分解**                | 只对 locally-finite connected simple lift 取最细 Cartesian prime factorization；先检验 `L_alpha` 对素因子的作用。若逐因子保持，记录各素因子的投影平移秩（含 rank-0 因子）并输出 canonical prime-rank multiset；若置换同构因子，则只报 factor-orbit sizes 与 `factor-permuting`，不伪造逐因子秩；含未处理 loops/multiedges 或唯一性条件未验证则 `not-applicable`。不得任选 `2+1` 或 `1+1+1`；组合可分也不证明动力学独立。 | I0；M/M/L；M/U?    | A      |
| **PG10** | **局域环—长程环首生次序**                           | 对每个最终 lift-component `alpha`，在每个过滤阈值枚举所有最终并入 `alpha` 的当前组件；`t0` 是任一当前组件首次含 reduced/simple zero-gain balanced circuit 的阈值，`tw` 是任一当前组件首次含 nonzero-gain simple winding circuit 的阈值。比较 `t0<tw / = / > / 缺失`；禁止平凡 `e·e_bar`，也不沿任意 elder branch 继承事件。 | I0；L/M/L；N/U?    | A      |
| **PG11** | **同调 successive-minima 型**                       | 对每个最终分量 `alpha` 定义 `t_k=min{t: 某个在阈值t的当前组件最终并入alpha且 rank L(C)≥k}`，记录 `k=1…D_alpha`。`D_alpha=0` 为 `not-applicable`，`D_alpha=1` 为 `single-direction`，`D_alpha≥2` 再分所有 `t_k` 相同的 `simultaneous` 与其余 `staged`。因为目标秩就是最终分量自身的 `D_alpha`，不得保留数学上不可发生的“永不满秩”。这是 canonical component poset 上的最早事件，不使用任意 elder/tie lineage，也不把同阈值未连通组件的 gains 聚合。 | I0；L/M/L；N       | A      |
| **PG12** | **winding backbone 覆盖型**                         | 只把属于某个 edge-simple nonzero-gain circuit/minimal unbalanced circuit 的节点/边计入 backbone；输出 `全覆盖 / 部分覆盖` 并报告精确比例，避免“出去又返回再绕远环”把 dangling edge 错算进去。 | I0；L/M/L；N/U?    | B      |
| **PG13** | **组件轨道 rank–SNF 谱**                            | 对每个有限 quotient-component/T-component-orbit 输出 `(D_alpha,SNF(L_alpha),s_alpha)` 多重集；full-rank 时另报有限 coset multiplicity，lower-rank 时明确是无限 component family，不能笼统称有限等价 cosets。 | I0；L/M/L；M/N     | A      |
| **PG14** | **特征覆盖 SPQR 形态**                              | 明确只在 `Q2,Q3` 有限特征覆盖的二连通块上做 SPQR，输出两尺度 `S/P/R` signature。它是有限尺度路由形态，不能直接声称 infinite lift 无割点或真实备用路径。 | I0；M/M/L；M/U?    | C      |
| **PG15** | **gain-biased-graph frame-matroid 连通级**          | zero-gain simple cycles 只定义 balanced-cycle class；frame-matroid circuits 还须按标准定义包含 unbalanced theta 与 tight/loose handcuffs。输出 matroid 的 1-sum/2-sum/更高连通分解，解释为“matroid 可分/不可分”，不直接称动力学耦合。 | I0；M/M/L；M/U?    | C      |
| **PG16** | **介观位点分离半径**                                | 在无限 lift 上 BFS distinct vertices；对局部标签相同的 sites，记录 coordination sequence 首次不同 shell `r_sep`，或“截至 `Lmax` 未分离”。除非有符号证明，不能写 `∞`。 | I0；L/M/L；M/U?    | A      |
| **PG17** | **coordination-sequence 递推候选型**                | 只有由 generating function/automaton 证明时才报精确最小递推阶/最终 quasi-period；有限 shell 拟合只能报“截至 `Lmax` 的候选阶 / unresolved”。 | I0；M/M/L；M       | B      |
| **PG18** | **zero-gain walk-regularity 破缺深度**              | 以 Laurent/Floquet adjacency 的常数项 `w_v(l)=[z^0](A(z)^l)_vv` 数返回同一 lift vertex 的闭游走，从 `l=1` 起比较；输出首次破缺或“截至 `Lmax` 未破缺”。 | I0；L/M/L；M/U?    | B      |
| **PG19** | **平移方向表示分解**                                | 对 lift-component stabilizer `H_alpha`，以共轭作用 `rho:H_alpha→GL(L_alpha)` 定义有限点作用像 `P_alpha=im(rho)≅H_alpha/ker(rho)`，再分解其在 `L_alpha⊗Q` 上的有理表示并输出实际 `D_alpha` 的 rank partition。`H_alpha/L_alpha` 只能另称 motif quotient，因 `ker(rho)` 可严格大于 `L_alpha`，不能默认它就是忠实点群像。 | I0/I2；L/M/L；M    | B      |
| **PG20** | **局部 stabilizer 作用型**                          | 用同一 `H_alpha`，按每个节点轨道取 site stabilizer 对 incident edge germs 集 `Omega` 的作用，按优先级分成互斥类：`|Omega|<2 / 2-transitive / primitive-not-2T / transitive-imprimitive / intransitive`。不再把蕴含关系 `2-transitive⇒primitive` 当成两个并列类别。 | I2；M/M/L；M       | B      |
| **PG21** | **距离各向同性半径**                                | 用同一 `H_alpha`，对每个 vertex orbit 分别求 site stabilizer 在 `1…r` lift 球壳上传递的最大 `r`；输出多重集或最小值，而非默认 vertex-transitive。 | I2；L/M/L；M/U?    | C      |
| **PG22** | **带 rank/SNF 注记的轨道 merge tree**               | 距离滤过中记录组件合并树，每个节点附 `(D,SNF)`；或在 `Q2,Q3` 输出 tree pair。`balanced/comb/multifurcating` 必须用冻结的树形判据，不能目测。 | I0；M/M/L；M/U?    | B      |
| **PG23** | **TRIM 零特征值重数谱**                             | 逐 component 先作 spanning-tree switching 令 tree gains 为零，此时 chord gains 落在 `L_alpha`；再固定无权 adjacency，对全部 `2^D_alpha` 个 `chi∈Hom(L_alpha,{±1})` 构造 `A_alpha(chi)` 并输出排序 nullity。不能把定义在 `L_alpha` 的 character 直接作用于任意 `T`-valued raw edge gain。 | I0；M/M/L；M/U?    | C      |
| **PG24** | **无权 adjacency Floquet flat-band 类别**           | 使用与 PG23 相同的 switched component 和 deck group `L_alpha`，固定 Laurent adjacency `A_alpha(z)`，以 `det(A_alpha(z)-lambda I) identically 0` 定义 flat band；分 `无 / 单 / 多`。邻接、组合 Laplacian 与归一化 Laplacian不可混用；只作组合图模态代理。 | I0；M/M/L；M/U?    | B      |
| **PG25** | **gain-compatible 图轨道—晶体学轨道关系**           | 先验证 crystallographic component stabilizer 是 `H_alpha` 的子群，再在同一节点/边集比较 orbit partitions；子群成立时晶体学轨道分区只能等于或严格细化图自同构轨道分区，故分 `equal / strict crystallographic refinement / subgroup-or-invariance failure`，不把数学上不可能的 `crossing` 当正常材料类别。只比较轨道数不够，也不能写因果“拓扑决定”。 | I2；M/M/M；M/U?    | B      |
| **PG26** | **组合定向反演/拓扑 handedness**                    | 检查 `H_alpha` 在 `L_alpha` 上的线性像是否含 `det=-1`；分 `有 orientation-reversing / 仅 orientation-preserving`。这不等于每个方向 `t→−t`，也不等于晶体手性。 | I2；M/M/L；M       | C      |
| **PG27** | **有限特征 torus-cover treewidth**                  | 在基不变的 `Q2,Q3` 上输出精确 `(tw2,tw3)`；它是两个有限尺度签名，随 cover 尺寸增长，不分没有结构学依据的“低/中/高”。 | I0；L/M/L；M/U?    | C      |
| **PG28** | **有限 cover critical-group 多重集**                | 对 `Q2,Q3` 的每个有限连通分量分别由 reduced Laplacian SNF 得 Jacobian invariant factors；只有连通有限图才有 `|Jac|=spanning-tree count`。 | I0；L/M/L；M/U?    | C      |
| **PG29** | **infinite-lift full-rank biconnectivity 出生滞后** | `tB` 定义为首次存在连通、周期、rank-`D_alpha` 且 infinite-lift vertex-connectivity≥2 的子图；与 `tD` 比较为 `同步/滞后/永不`。有限 torus 环会把一维 double ray 误判为二连通，不能代用。 | I0；M/M/L；N/U?    | B      |
| **PG30** | **环境颜色分区—图轨道分区关系**                     | 对被检验颜色层 `c∈{CN,geometry,Wyckoff}`，先显式从标签中拿掉 `c`，计算 `H^(-c)=Aut_T(G,labels_without_c)`；再在同一节点集比较 `c` 的颜色分区与 `H^(-c)` 轨道分区，分 `equal / strict-color-refinement / strict-color-coarsening / crossing`，其中 refinement/coarsening 均明确为 proper。若仍用含 `c` 的完整标签自同构群，轨道必细化颜色而使本量退化，故只作 QC。措辞不作“拓扑决定环境”的因果解释。 | I0/I2；M/M/M；N/U? | A      |

其中三个较陌生量可写成：

\[
a\in\operatorname{Hom}(L_\alpha,\mathbb F_2)\setminus\{0\},
\qquad \xi_a=a\circ\tau_\alpha\in H^1(Q_\alpha;\mathbb F_2),
\]

\[
w(a)=\min_{z\in\xi_a}
\sum_{O\in E/H_\alpha}
\mathbf 1\!\left[\exists e\in O:z(e)\ne0\right].
\]

即 PG03 在同一 component stabilizer `H_alpha` 下最小化**edge-orbit 支撑**，而不是边数或路径长度。字符定义在实际可达格 `L_alpha` 上；例如 gain `2e1` 的一维链在 `L_alpha=2Z e1` 上仍有非平凡 parity character，不能直接把 ambient gain 模 2 后误判为零。排序后的 `w(a)` 对换原胞代表元不变。PG05 为

\[
u_{\rm elem}=\min_{C_1,\ldots,C_{D_\alpha}}
\left[L_\alpha:\langle\tau(C_1),\ldots,\tau(C_{D_\alpha})\rangle\right],
\]

而 PG08 为

\[
k_{D_\alpha}=\max\{k:\operatorname{core}_k(\widetilde G_\alpha)
\text{ 含 winding rank }D_\alpha\text{ 的分量}\}.
\]

这些式子定义的是同一冻结图上的不变量；它们不会修复错误的 Na–Na 建图规则。

#### 不建议继续扩张的图论量

- 无限共紧 `Z^D` 图的 ends 数基本由维度决定，几乎不会提供新信息。
- 普通 primitive quotient 的 planarity、treewidth 和 centrality 会被 gain self-loop 严重误导；若要用，只能在特征 torus cover 或无限周期定义上使用。
- 固定大小超胞的 spanning-tree count、环数、平均路径长会随复制规模机械增长；不能直接跨材料比较。
- 单列普通 matching/cycle cover、边轨道删除脆弱性、canonical net key，通常会与已有候选或化学体系高度重叠，宜作为内部诊断而非主假说。

本族的数学灵感主要来自 [gain/biased graph](https://doi.org/10.1016/0095-8956(89)90063-4)、[晶体 net 自同构](https://doi.org/10.1107/S0108767303012017)、[周期图 connectivity](https://doi.org/10.1107/S2053273316003867)、[coordination sequence 的 quasi-polynomial 结构](https://doi.org/10.1107/S2053273320016769)、[Cartesian graph factorization](https://doi.org/10.1016/j.disc.2005.09.038) 和 [周期图 flat bands](https://doi.org/10.1063/5.0156336)。这些工作提供可计算定义，但本轮没有找到 PG03–PG10、PG16、PG18、PG22–PG24 被作为 Na-SSE 跨材料电导分类量的直接检验。

### 3.2 几何空隙与通道网络：把一个 probe radius 变成完整过滤过程

单个瓶颈半径或最大自由球只能描述一个临界数值；下面的候选保留“空隙组件怎样合并、何时产生不同长程方向、关键窗口是单点控制还是成组出现”。所有 `VN` 项都应以去 Na 后的 radical Voronoi/CAVD 网络为默认对象，并同时报告至少一组离子半径扰动。

| ID       | 分类量                                           | 操作定义与建议离散值                                         | 输入；风险；状态    | 优先级 |
| -------- | ------------------------------------------------ | ------------------------------------------------------------ | ------------------- | ------ |
| **VN01** | **空隙网络节点/喉道转移数**                      | 对可达 void graph 数空间群下 node/edge orbits `(pv,qv)`；分 `1,1 / 单节点多喉道 / 多节点单喉道 / 多—多`。问几何通道是否由一种空腔和一种窗口重复组成。 | I2；M/H/M；N        | A      |
| **VN02** | **首次贯通临界窗口轨道简并**                     | 按 throat clearance 批量加入并列边；首次出现非零 winding 时，分 `单一临界 edge orbit / ≥2 个非等价 orbit 同阈值 / 容差内近并列未决 / 不贯通`。后续顺序由 VN06 记录，避免类别重叠。 | I2；M/H/M；N/U?     | A      |
| **VN03** | **临界 elementary channel-family 数**            | 在首次/满秩临界阈值的有限 labelled quotient 中枚举全部 bottleneck-optimal、edge-simple、nonzero-gain cycles；在 `H_alpha`、cycle rotation/reversal 与 switching 下 canonicalize，输出所有并列最优 cycle-orbits 的多重集及 `1 / 2 / ≥3` 类数。不得按 vertex ID/输入顺序任选一个；不枚举 `Z^D` 中无限多个任意 primitive vectors。 | I2；M/H/M；N/U?     | A      |
| **VN04** | **通道家族交汇 incidence signature**             | 从 VN03 在有限 labelled quotient 中枚举的全部并列 optimal concrete cycles 出发，对无序的 distinct cycle pairs `(C1,C2)` 取 `H_alpha` 的**对角作用**（并同时模去 pair swap）之 joint orbits；逐 joint orbit 记录 `shared-edge / shared-junction-only / disjoint` 以及两条有理 gain lines 为 `equal / distinct`。输出 joint-orbit signature 多重集，单 cycle-orbit 但有多个对称副本时仍可产生内部 pair orbit；不从两个各自的 family orbit 任取代表比较方向或位置。 | I2；M/H/M；N        | B      |
| **VN05** | **pocket 共存型**                                | winding backbone 唯一定义为 PG12 的 nonzero-gain simple-circuit edge support `E_bb`，不与 2-core 混用。残余图固定为 `R=(V,E\E_bb)`：删除 backbone edges 但保留 attachment vertices；对 `R` 中接触 backbone 的有限 edge-components，以 cycle rank=0/＞0 区分 `(A0)` acyclic branches 与 `(A1)` zero-gain cyclic pockets，另以 `(I)` 标记与任何 winding component 断开的 zero-winding cavities。输出 `(I,A0,A1)∈{0,1}^3`、各类 orbit 数和 attachment-vertex 数。 | I2；M/H/M；N/U?     | B      |
| **VN06** | **空隙秩激活词**                                 | 随 clearance 阈值降低记录平移秩事件，如 `0→3`、`0→1→3`、`0→2→3`、`0→1→2→3`；另报 plateau 数。 | I2；M/H/M；N        | A      |
| **VN07** | **方向激活简并型（VN06 派生）**                  | 从 VN06 的 rank-jump word 确定：`D=0 不贯通`、`D=1 单次`、`D=2 同时(0→2)/顺序(0→1→2)`、`D=3 同时(0→3)/1后2(0→1→3)/2后1(0→2→3)/全顺序`。用平移子空间而非 a/b/c；它只是 VN06 的预定义粗化，不另作主检验。 | I2；L/H/M；N/U?     | X      |
| **VN08** | **cage–window incidence regularity**             | 建 cage↔window 二部图并分 `regular / biregular / irregular`。无边界 natural tiling 中一个 window 通常邻接两 cages；dead end 应在 void skeleton 节点/边上另判，不能用“degree-1 window”混写。 | I2；H/H/M；M/U?     | B      |
| **VN09** | **window/constriction 拓扑字母表**               | 优先按 Delaunay constriction simplex/face graph、几何形状与对称轨道编码；只有找到冻结规则下的 canonical bonded rim cycle 才使用环长。分 `单一 / 二元 / ≥3 种 / ambiguous`。 | I2；H/H/M；M        | B      |
| **VN10** | **临界 constriction 化学语法**                   | 对首次贯通 constriction 的定义原子按“元素×局域环境”编码；有 canonical rim 时取模旋转/反射循环词，否则用带 face-graph 的无序多重集；分 `homogeneous / alternating / block / mixed / no-rim`。JACS 2025 已直接验证瓶颈局部化学组成与跳跃势垒/宏观电导的关系，因此物理原语不是全新；本轮未找到循环次序这一精确分类。确定性标签只适用于完全有序、rim 长度至少 4 且至少含两种标签的结构，其余输出 `not-applicable/ambiguous`。 | I2；H/H/H；N/U?     | B      |
| **VN11** | **cage-wall 化学 patchiness**                    | 将 cage 边界原子按化学标签着色，计算同色连通 patch；分 `同质 / Janus-like / 多 patch`。它把平均阴离子组成变成空间分布类型。 | I2；H/H/H；M/U?     | B      |
| **VN12** | **void k-core 层级型**                           | 对周期可达 lift 同步做 k-core，令 `C2,C3` 为 2/3-core；按优先级给互斥穷尽类：`C2 empty / C3 nonempty / C3 empty且C2为G的真子图 / C2=G且C3 empty`，并标每个 core 的 winding rank及 lift 是否无环。double ray 虽无图论 cycle 却是 pure 2-core，因此 `acyclic` 必须另轴报告。 | I2；M/H/M；N        | C      |
| **VN13** | **void component-orbit 维度谱**                  | 对有限 quotient components/T-component-orbits 记录 `(D_i,SNF_i)` 多重集；例如 quotient 谱 `{3,0,0}` 表示每平移商域一个 3D 主网轨道与两个孤立空腔轨道。full-rank 时可报有限 coset multiplicity；lower-rank 层/链须标为无限 component family，不能声称枚举了“全部组件”。 | I2；L/H/M；M/U?     | A      |
| **VN14** | **笼—窗口净空/收窄剖面**                         | 联合 largest included sphere `Di`、largest free sphere `Df` 和沿自由路径最大 included sphere `Dif`，或沿预注册 canonical winding path 的 clearance `c(s)`；按冻结阈值分 `低调制近均匀 / 单主瓶颈大笼窄窗 / 多个非等价显著瓶颈 / ambiguous`。单个 CIF 只定义 clearance/constriction profile，不应称相对参考态的 contraction。周期重复的同一窗口不算多级；并列近等价路径异类时输出 `ambiguous`。通道均匀性与瓶颈机制已有直接/近先例，精确互斥剖面分类本轮未见直接检验。 | I2；M/H/M；D/N/M/U? | B      |
| **VN15** | **空隙 merge-tree 形态**                         | 对 clearance 过滤的连通组件合并树做 canonicalization；分 `balanced / comb-like / multifurcating`。它描述空腔逐层接通的层级。 | I2；M/H/M；M/U?     | B      |
| **VN16** | **critical-throat orbit cut 数**                 | 只允许按对称喉道轨道删除，求使可达网络 winding rank 下降的最少轨道数；分 `1 / 2 / ≥3`。这是空隙网版本，不与占据 Na 图的 S1 混写。 | I2；M/H/M；N/U?     | A      |
| **VN17** | **两端口 characteristic-cover 路由签名**         | 对 VN03 每个 canonical family，在固定 characteristic covers `m=2,3` 中作 two-terminal reduction。按优先级给互斥类：`unique-path(series-only)`；否则若抑制度2点后为单层 parallel bundle，记 `parallel-alternatives`；否则若为 two-terminal series-parallel，记 `mixed-series-parallel`；其余 `non-series-parallel`。输出所有 `(family,m)` 类的多重集，并另标 `uniform/heterogeneous`；terminal 未被唯一识别或两尺度冲突时为 `not-resolved/cover-dependent`。它是有限-cover 签名，不是无限 lift 绝对不变量。 | I2；M/H/M；N/U?     | A      |
| **VN18** | **空隙网二分/奇局域环**                          | 在无限 lift 上判是否有 odd zero-gain closed walk；分 `bipartite / non-bipartite`。它与在占据 Na 图上做 S2 是两个不同实验。 | I2；L/H/M；U?       | B      |
| **VN19** | **空隙局域几何字母表**                           | 对 void nodes 的 Delaunay 邻域用 ChemEnv/连续对称度标为 Tet/Oct/Prism/其他；分 `单型 / 二型 / 多型`，再报这些类型在 winding backbone 上是否混合。 | I2；M/H/H；N        | B      |
| **VN20** | **临界通道中心线嵌入型**                         | 只对 VN03 families 的冻结 CAVD/Voronoi 中心线代表，用共线性、共面性、离散曲率和扭率分 `直 / planar zig-zag / helical / 3D curved / mixed`。存在 screw operation 不能单独证明 helix，因为轴上直通道也可被 screw 保持；并列 critical path orbit 全部分类后若不一致则为 `mixed`。已有螺旋/弯曲路径的单材料机制案例，但未见统一五分类的跨 SSE 电导检验；形态本身没有已知单调有利方向，故保留在探索/储备层。 | I2；H/H/M；N/M/U?   | C      |
| **VN21** | **host-natural-tiling 与 void-net 对偶关系**     | 构造宿主 natural tiling 的对偶图并与 void graph 作带平移标签同构；分 `周期同构 / 仅壳层序列相同 / 非对偶 / not-applicable或ambiguous`。 | I2；H/H/M；M/U?     | C      |
| **VN22** | **几何—BVSE winding-lattice 关系**               | 在共同 ambient translation lattice 中分别保留 void 与 BVSE 的 component-orbit lattice spectra `{L_void,i}`、`{L_bvse,j}`，并输出所有 `(i,j)` 的 `(rank Li,rank Lj,rank intersection)` 与两侧 SNF/双指数关系矩阵，绝不先聚合断开组件。仅当两侧各恰有一个 positive-rank component orbit，或另有合法等变组件对应时，才逐对应导出 `equal / one-side-proper-subgroup / incomparable-positive-intersection / incomparable-zero-intersection`；其余结构级状态为 `multi-component-unpaired`，全无 winding 则单列。关键 orbit 比较还须另有合法节点/边映射。 | I2；M/H/M；N/U?     | A      |
| **VN23** | **占据 Na 位—扩展 interstitial-node 对应关系型** | 在冻结距离/环境规则下，建立 Na sites 与 CAVD 式扩展节点集（Voronoi vertices + 必要 face centres + bottleneck/intersection candidates）之间的空间群等变二部候选关系并保留节点类型；输出各关系组件的 `(n_Na,n_void;两侧degree多重集)`。结构级粗类按优先级为 `perfect 1:1 / partial 1:1 / many-to-one only / one-to-many only / many-to-many-or-mixed / no relation`。若下游必须 matching，只报告最大 matching 是否唯一/对称简并，不按原子 ID 任取；VN24 仅接受关系本身为可靠 perfect 1:1。只匹配 void maxima 会漏掉位于 Voronoi face/bottleneck 的已知离子位点。 | I2/I3；M/H/H；N     | A      |
| **VN24** | **占据位—空隙位稳定子关系**                      | 只在 VN23 可靠一一匹配且匹配规则给出共同局域 frame/等变映射 `g:x→y` 的子集，将 `g G_Na g^-1` 与 `G_void` 置于同一群后取交 `H`，报告双指数并分 `conjugate-equal / one-side nested / incomparable`。若 `g` 不规范或有多个非等价选择，报 `conjugacy-only/ambiguous`；一对多、多对一、未匹配为 `split/unavailable`。 | I2/I3；M/H/H；U?    | A      |

这里很多算法在孔材料中已经成熟，尤其是 [Zeo++](https://doi.org/10.1016/j.micromeso.2011.08.020)、[CAVD](https://doi.org/10.1038/s41597-020-0491-x) 以及 periodic net/tiling 方法。因此 VN01、VN08、VN09、VN14、VN19 不能声称“新方法”。更稳妥的论文表述是：**把成熟的空隙几何对象转化为预注册的 Na-SSE 离散分类，并首次审计其跨体系电导关联**。VN02、VN03、VN06、VN10、VN16、VN17、VN22、VN24 在本轮检索中未找到精确定义相同的 Na 跨材料检验。

### 3.3 宿主骨架、多面体与刚性：不只看共角/共边，还看骨架怎样分层组织

`G_host` 的最大难点是成键并非 CIF 原生字段。所有结果都必须至少跨两种合理成键方案或 solid-angle 阈值报告稳定平台。非唯一性主要来自 host 成键、去构筑以及 ring/cage 选择；对适用的 3-periodic net，冻结 [natural-tiling 算法](https://doi.org/10.1107/S0108767307038287) 后其目标正是给出唯一自然铺砌，但仍须允许 `not-applicable/failure`。因此不同项目的 R1 来源要分开写，不能笼统称 natural tiling 本身无唯一规则。

| ID       | 分类量                                        | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | --------------------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **HF01** | **宿主 net 顶点/边转移数**                    | 去 Na 后的周期键图分别在 crystallographic component stabilizer 与 gain-compatible `Aut_T` component stabilizer 下数 vertex/edge orbits `(p,q)`；两套结果分开报告。不能使用不正规化 CIF 平移作用的任意 abstract automorphism。 | I0/I2；M/H/M；M    | B      |
| **HF02** | **natural-tiling 转移数**                     | 对固定 host net 的自然铺砌数 vertex/edge/face/tile orbits `(p,q,r,s)`；粗分 `1111 / 低转移 / 高转移`。 | I2；H/H/M；M       | C      |
| **HF03** | **宿主 coordination-sequence 生长类**         | 对骨架节点轨道计算 shell growth；分 `轨道同质/异质` 与低/中/高拓扑密度（箱界由全数据 X 分布预注册，不看 y）。 | I0；M/H/M；M       | B      |
| **HF04** | **vertex-ring signature 字母表**              | 固定 ring convention 后，对每个骨架节点记录穿过它的环长**多重集**（含重数），再在 site stabilizer 下 canonicalize；分 `1 / 2 / ≥3` 种局域环环境。除非额外给出可验证的局部 frame，不使用依赖 incident-edge 编号的“有序环长串”。 | I2；H/H/M；M       | C      |
| **HF05** | **笼/NBU 字母表**                             | natural tiles 或 natural building units 按 face symbols 编码；分 `单笼 / 双笼 / 多笼`，另报是否有开放通道单元。 | I2；H/H/M；M       | B      |
| **HF06** | **宿主 labelled quotient multigraph 型**      | 记录 host quotient 是否含不同 gain 的 parallel edges/self-loops；分 `simple / loop / parallel / both`，并报重数谱。 | I0；M/H/M；M/U?    | B      |
| **HF07** | **接触层级拓扑持久词**                        | 按 Voronoi solid angle 或成键置信度逐级加入/删除弱 host edges，记录 net 类型和维度的稳定 plateau；分 `单平台 / 一次跃迁 / 多级跃迁`。 | I0/I2；M/H/M；M/U? | A      |
| **HF08** | **骨架 component-orbit 维度谱**               | 对去 Na 后有限 quotient components/T-component-orbits 记录 `(D_i,SNF_i)` 多重集，如 `{3}`、`{2,0}`、`{1,1}`；full-rank 时可给有限 multiplicity，lower-rank 链/层明确是无限 component family。 | I0；M/H/M；M/N     | A      |
| **HF09** | **host-net component-orbit 重数与空间互穿**   | 先报告有限的 quotient/T-component-orbit 数 `1 / 2 / ≥3`、各 orbit 的 stabilizer rank/SNF 和 homo-/hetero-topology；full-rank 才另报有限 coset multiplicity，lower-rank 标为无限平行 family。再用独立空间缠结判据标 `interpenetrated / parallel-disjoint / ambiguous`；多组件轨道本身不等于互穿。 | I2；H/H/H；M       | B      |
| **HF10** | **缠结关系向量**                              | 基于固定强环/自然环和 linking number，分别判三个位：`I=不同无限 net 空间互穿`、`P=不同组件的环发生 polycatenation`、`S=同一组件内 self-catenation`；输出 multi-hot `(I,P,S)∈{0,1}^3`，仅 `(0,0,0)` 称 `none`。这样互穿组件中又含 self-catenation 的结构不会被强塞进单一类别。 | I2；H/H/H；M       | C      |
| **HF11** | **层堆垛词**                                  | 对 2D host components，将相邻层平移在 layer group 下约化；分 `AA / AB / ABC / 更长周期 / mixed`。 | I2/I3；H/H/H；M    | B      |
| **HF12** | **骨架手性层级**                              | 分开判断 `abstract-net chirality / embedded-net chirality / 多副本 handedness`，末者再分 homochiral/racemic；不以其中一层替代另一层。 | I2；H/M/H；M       | C      |
| **HF13** | **临界通道的多面体连接词**                    | 对 VN03 的全部并列 optimal cycle-orbits，把每个 throat 归属到其相邻/控制骨架多面体，再记录这些多面体之间的 corner/edge/face 循环词；在 `H_alpha`、rotation/reversal 与 switching 下输出 word-orbit 多重集，只有多重集为单类时才给 `纯型 / 周期交替 / block / mixed` 单标签。不能按输入顺序择一路，也不能把 void path 直说成穿过实体多面体。 | I2；H/H/H；N/U?    | A      |
| **HF14** | **异种多面体混合型**                          | 节点按“中心元素×配位几何”着色，比较相邻 mixing matrix 与度保持 null；分 `homophilic / heterophilic / mixed`。 | I2；M/H/H；M/U?    | A      |
| **HF15** | **畸变状态空间排序**                          | 将多面体按连续对称度稳定平台分 regular/mild/severe，再用预注册的邻接标签自相关/度保持 null 分 `uniform / assortative-clustered / disassortative-alternating / neutral-mixed`。不使用没有操作定义的 “frustrated”，也不以平均畸变代替空间排列。 | I2；M/H/H；M/U?    | B      |
| **HF16** | **共角铰链网络维度**                          | 先冻结 rigid-unit 字母表与共享判据；仅当两个刚体恰共享一个桥联原子、未共享边/面，且局部线性约束 Jacobian 保留非零相对转动自由度时连 hinge edge，再逐分量求平移秩 `0–3`。判据失败/几何退化为 `ambiguous`；这只是静态柔性代理。 | I2；M/H/M；N       | A      |
| **HF17** | **Maxwell index 类别**                        | 冻结哪些单元视为刚体、共享角/边/面贡献多少独立约束，报告 Maxwell index 的 `欠计数 / 等计数 / 过计数` 与 states-of-self-stress 计数。它只是约束计数，不据此断言真实框架柔性或刚性。 | I2；H/H/M；M/N     | B      |
| **HF18** | **Gamma 点 infinitesimal-flex 支撑类**        | 构固定晶格周期刚性矩阵，除去平移零模后先报 flex-space dimension；再在 symmetry motif-orbits 上求能支撑非零 flex 的最小 orbit 子集，分 `无非平凡 flex / proper-subset motif-sparse / all-orbit-required`。Gamma flex 全部是周期模，不能称空间“局域/延展”；固定周期边界也不自动扣整体转动，允许晶格应变须另立 affine-flex 版本。 | I2；M/H/M；M/U?    | B      |
| **HF19** | **RUM rank-drop locus 谱**                    | 对 phase-periodic rigidity matrix 用 maximal minors/Fitting ideal 定义 torus 上 rank-drop locus；报告 `trivial-only?`、不可约/连通成分维数多重集与最大维数。孤立点、曲线、曲面可同时存在，不能强迫成互斥单标签；它也不是真实声子谱。 | I2；M/H/M；M/U?    | C      |
| **HF20** | **Γ 柔性空间的 collective-opening 可行性**    | 对每个关键喉道 clearance `c_j` 取一侧/广义方向导数，在单位 Γ-flex 空间上算 `max_u min_j D c_j(u)`；分 `>eps collective-opening / <-eps 必有 trade-off / |.|≤eps marginal / 无 flex`。因 `u↔−u`，不能定义“只有闭口模”；对称并列瓶颈的不可微性须用各喉道导数或 Clarke 型规则处理。 | I2；H/H/M；U?      | B      |
| **HF21** | **bond-hierarchy deconstruction depth**       | 依据预先冻结的 complete→skeletal 弱键层级逐级简化，记录直到拓扑标签稳定所需层数；分 `单层 / 两层 / ≥3 层 / 无稳定平台`。这是受 skeletal-net hierarchy 启发的自定义派生量，不冒充该文献的标准量。 | I2；H/H/M；M/U?    | B      |
| **HF22** | **多阴离子缩合的完整组件谱**                  | 不只给 isolated/dimer/chain/layer/3D，而记录不同缩合组件共同出现的字母表，如 `{0D,1D}`、`{1D,2D}`；桥联定义冻结。 | I0/I2；M/H/M；N    | B      |
| **HF23** | **稀有骨架 motif 的 route-support necessity** | 保持原始几何不变，只删除由某低频 motif orbit 归属/控制的 Na/void throat 或 hop-edge orbits，再检验 winding rank 是否下降；分 `无稀有关键支持 / 单一关键 / 多个关键 / 归属不唯一`。不能通过删除 host 原子并重算空隙来制造反事实“大洞”。 | I2；H/H/H；U?      | A      |
| **HF24** | **阴离子 weighted-Delaunay simplex grammar**  | 只取阴离子点集作 regular/radical Delaunay；3D simplex 固有 4 个顶点，故按四顶点化学、形状/体积和退化类型着色，而不按“simplex CN”分类；再将共享面序列分 `homotypic / alternating / mixed`。共球/近共球导致 triangulation 非唯一时，保留 regular-cell degeneracy 或只接受所有合法细分一致的标签。 | I1/I2；M/H/M；N/U? | B      |

HF01–HF12 的方法学在晶体 net、zeolite 和 MOF 中并不新：[ToposPro](https://doi.org/10.1021/cg500498k) 使用 coordination sequences、point/vertex symbols 和 tiling signatures，[周期 net taxonomy](https://doi.org/10.1039/B615006C) 使用 transitivity，[natural tilings](https://doi.org/10.1107/S0108767307038287) 与 [skeletal-net hierarchy](https://doi.org/10.1107/S2053273323008975) 也已有严格定义。可探索的新问题是这些分类是否在 Na-SSE 的体系内部仍有变异并与电导相关。HF16–HF20 的灵感来自 [周期框架的 RUM/rigidity polynomial](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/) 和 [zeolite flexibility window](https://pmc.ncbi.nlm.nih.gov/articles/PMC4669995/)；它们只能称作理想化静态柔性代理。

### 3.4 带颜色的 Na 位点环境与跨子晶格关系

这一族把“有几种 Na 环境”升级为“不同环境在长程路径上承担什么角色”。局域环境识别可采用 [ChemEnv 的连续配位环境方法](https://doi.org/10.1107/S2052520620007994)、Voronoi 拓扑或固定 CN 规则；三种方法不一致时应输出 `ambiguous`，而不是强迫标签。

| ID       | 分类量                                            | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | ------------------------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **CE01** | **Na CN 状态数**                                  | 对 Na 轨道按统一配位规则取 CN，分 `1 / 2 / ≥3` 种；同时报告在冻结参数域与测度下的标签稳定质量。 | I0；L/H/M；N       | B      |
| **CE02** | **Na 多面体字母表**                               | 以连续对称度分 Tet/Oct/Prism/其他/ambiguous；分 `单型 / 二型 / 多型 / 主要 ambiguous`。 | I2；M/H/M；N       | B      |
| **CE03** | **环境邻接混合型**                                | 在同一周期 Na 图上分别用 `CN`、`coordination geometry`、`Wyckoff orbit` 三张颜色层计算同色/异色边 mixing，分 `homophilic / heterophilic / mixed`；联合乘积颜色只作敏感性分析，避免把纯环境异质性退化成同/异轨道边。 | I0/I2；M/H/M；N/U? | A      |
| **CE04** | **CN 改变是否为长程必需（CE06 派生）**            | 从 CE06 的 CN-layer successive-minima 向量映射：`D_alpha=0→not-applicable`；`全零→intra-CN sufficient`；`零/正混合→仅部分方向 required`；`全正→CN-change required`。可用删异 CN 边重算 rank 作回归验证；它是三类粗化摘要，不另作主检验。 | I0；L/H/M；N/U?    | X      |
| **CE05** | **几何环境改变是否为长程必需**                    | 完全镜像 CE04，但颜色用完整配位几何：`D_alpha=0→not-applicable / 全零→同型足够 / 零正混合→仅部分方向必须换型 / 全正→所有长程基方向均需换型`；只有配位标签或最优环在冻结规则下不稳定才记 `ambiguous`。比原 S9 更具体，也不等同于 Wyckoff orbit。 | I2；M/H/M；N/U?    | A      |
| **CE06** | **环境切换 successive-minima 向量**               | 对每个 `D_alpha>0` 的 `Q_alpha`，在 CN、几何、Wyckoff 三张颜色层分别计算：从有限 edge-simple winding cycles 中选 gains 构成 `L_alpha⊗Q` 基的 `D_alpha` 个环，按字典序最小化其排序后颜色变化次数向量；每层按优先级粗分 `全0 / 零正混合 / 全正且max=2（此时全为最小的2次切换） / 全正且max≥3`，`D_alpha=0` 为 `not-applicable`，多组件结构输出 component multiset。闭合循环词只要非恒定就至少切换两次，因此不设置不可能的“1次切换”类。变化“次数”与切换类型数另报；CE04 是 CN 层的三类映射。若最终进入主检验，只允许预注册的 `v_CN` 粗类占一个假说名额；另外两层及联合三元组为 exploratory follow-up，避免把一个 ID 暗中当成三个主假说。 | I0/I2；M/H/M；U?   | A      |
| **CE07** | **稀有环境必要性**                                | 对出现频率最低的环境 orbit 逐类删除，检查 winding rank；分 `非必要 / 单方向必要 / 多方向必要`。频率只按轨道/多重性定义，不看 y。 | I0/I2；M/H/M；U?   | A      |
| **CE08** | **环境循环语法**                                  | 对有限 translation quotient 中全部并列最优 edge-simple elementary winding cycle-orbits，分别记录 CN、几何、Wyckoff 循环词；在 `H_alpha`、rotation/reversal 与 switching 下输出 word-orbit 多重集，只有单类时才给 `constant / AB alternating / block / ≥3-color mixed` 标签。不按原子 ID 破 tie，也不枚举无限多个任意平移向量。 | I0/I2；M/H/M；M/U? | B      |
| **CE09** | **Na Voronoi-cell 拓扑多样性**                    | 以 Voronoi index/简化面图而非距离阈值描述局域邻域；分 `1 / 2 / ≥3` 个拓扑型，并与 ChemEnv 是否一致交叉分类。 | I0/I2；M/M/M；M    | B      |
| **CE10** | **配位标签歧义型**                                | 比较至少两种配位算法；分 `完全一致 / 只在 CN 一致 / 几何冲突 / CN 也冲突`。这既是候选，也是重要质量标签。 | I2；L/M/M；M/U?    | A      |
| **CE11** | **site symmetry—配位形状兼容性**                  | 冻结邻居—理想顶点对应与多面体实际取向，把 `G_site`、`G_poly` 嵌入同一正交群并只取实际交 `H=G_site∩G_poly`；报告双指数，分 `equal / one-side nested / non-nested / ambiguous`。不再同时做“最大共轭交”；若想允许旋转优化，必须另立量并报告非唯一 maximizer。 | I2；M/H/M；M/U?    | A      |
| **CE12** | **局域配位手性**                                  | 判断 Na 配位壳层是否为手性，以及两个手性是否在晶胞中成对；分 `achiral / homochiral / racemic-local`。 | I2；H/H/M；M/U?    | C      |
| **CE13** | **畸变符号模式**                                  | 相对最佳理想多面体主轴，分 `近规则 / 轴向拉长 / 轴向压缩 / 多轴混合`；再看轨道间是否同号或交替。 | I2；M/H/M；M/U?    | B      |
| **CE14** | **Na 多面体体积排序**                             | 对不同 Na 环境只保留偏序：`占位高者体积大 / 小 / 无一致序 / 单一环境`；需先控制 CN。 | I0；M/H/H；N/U?    | C      |
| **CE15** | **阴离子角色字母表**                              | 对每个阴离子赋予可并存的 multi-hot 角色集：terminal、Na–Na bridge、framework–framework bridge、Na–framework bridge；结构分 `全部单角色 / 含双角色 / 含≥3角色 / 规则不确定`，不强迫互斥标签。 | I0；M/H/M；N/U?    | A      |
| **CE16** | **mobile/void × host incidence 拓扑（纯平移商）** | 严格按 2.1：二部节点是在一个**纯平移原胞**内的实际 Na/void sites 与实际宿主多面体/阴离子单元，不先压成空间群 orbit；每个几何 incidence edge 保留整数平移 gain，平行且 gain 不同的 edges 不合并。输出两轴联合签名：结构级先报 `no-incidence / one non-isolated lift-component orbit / ≥2 non-isolated component orbits` 并单列 isolates；再对每个非孤立 lift-component 报 `acyclic-chain / acyclic-branched / cyclic-or-parallel` 的 component-orbit 多重集。这样不在已连通组件内部再使用“disconnected”。随后才用空间群数 node/edge/component orbits；另报 degree spectrum、multigraph cycle rank，整数 incidence-count matrix 的 rank 固定在 `Q` 上（`F2` 仅敏感性）。若改用空间群压缩，必须升级成完整 symmetry-labelled groupoid。 | I2；M/H/H；N/U?    | A      |
| **CE17** | **瓶颈所有权**                                    | 每个 critical throat 由几个 host atom/polyhedron orbits 共同定义；分 `单一轨道控制 / 两轨道协同 / 分布式`。 | I2；M/H/H；N/U?    | A      |
| **CE18** | **Na/host 平移格 commensurability**               | 在共同有理坐标系中分别求 full、Na、阴离子、不可动阳离子子结构的最大平移格；去除子晶格后所得格通常是 `Lambda_full` 的超格，可能含相对 full basis 的分数平移。对任意两格取 `Lambda0=LambdaA∩LambdaB`，报告双指数与 SNF，分 `equal / one-side superlattice / non-nested / ambiguous`。 | I0/I3；L/M/H；U?   | A      |
| **CE19** | **Na 排布导致的超结构指数**                       | 当已验证 `Lambda_full subset Lambda_host` 时，定义 `[Lambda_host:Lambda_full]=V_full/V_host`，分 `1 / 2 / 3–4 / >4`；若不嵌套则 `not-applicable`。这是 CE18 的简化解释量，不能用反向体积比。 | I0/I3；L/M/H；N/U? | A      |
| **CE20** | **通道—层方向关系**                               | 若 host 有 2D 组件，比较 void/Na winding 子空间与层面；分 `in-plane / cross-plane / oblique/mixed`。 | I2；M/H/M；N       | B      |
| **CE21** | **mobile—framework 维度有序对**                   | 逐连通分量保留 mobile 与 host 的维度谱；主标签明确取 `(D_mobile^max,D_host^max)`，另分 `mobile>host / equal / mobile<host`，并同时输出完整 component spectra，绝不把断开组件的 gains 聚合。精确关系型分类本轮未找到直接 Na 跨体系先例，但构件均有前例。 | I0/I2；M/H/M；N/U? | A      |
| **CE22** | **Na 图—void 图 chain-map 同调型**                | 先用 VN23 的可靠 perfect-1:1 节点关系；再把每条 `G_occ` edge 以冻结、对称等变且 gain-compatible 的规则映射为连接对应 void nodes 的 `G_void` path，并验证反向/边界相容，形成合法 chain map。对诱导的整数 `H1` 映射直接报告 `rank ker(f_*)` 与 `coker(f_*)` 的 SNF（含自由秩），再导出互斥类：`isomorphism / injective-finite-index-proper / injective-rank-deficient / noninjective / 无合法映射`。最近点投影本身不够。 | I2；H/H/H；U?      | A      |
| **CE23** | **骨架铰链—瓶颈重合型**                           | critical throat 邻近的 host joints 是否属于 HF16/HF18 的柔性核心；分 `全部重合 / 部分 / 无 / 无柔性核心`。 | I2；H/H/M；U?      | A      |
| **CE24** | **Na 与骨架复杂度关系**                           | 在各自子晶格内以 `p_i=m_i/sum_j m_j` 归一化后，分别计算 Na-orbit 环境与 host-orbit 环境信息量，分 `Na更简单 / 相近 / Na更复杂`；这是关系型而非被原子数支配的总复杂度。 | I0/I3；M/M/H；M/U? | B      |

CE04–CE08、CE16–CE18、CE22–CE23 是尤其值得新数据检验的组合量。前人已经证明局域配位、面共享高配位 Na sites 和不同晶体学 Na 位点都可能参与迁移，但“环境颜色在整个周期路径上的必要性、循环语法和跨子晶格 incidence”仍是更细的命题。[Na 高配位面共享设计原则](https://www.nature.com/articles/s41467-023-43436-3) 是重要近邻先例，不能被遗漏。

### 3.5 无序、部分占位与缺陷容纳：只能从 CIF 声称“报告的平均结构”

2025 年的 CIF 高通量无序分类已经严格定义了 ordered (O)、substitutional (S)、positional (P)、vacancy (V) 以及 SV、SP、VP、SVP 轨道，并显示约一半 ICSD 条目含某种报告无序。因此 DO01–DO03 本身不是新分类方法；本文新增空间主要在“无序轨道在周期通道和跨子晶格耦合中的位置”。一手来源见 [Classification and statistical analysis of structural disorder](https://journals.iucr.org/j/issues/2025/03/00/jur5002/)。

| ID       | 分类量                             | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | ---------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **DO01** | **报告无序类型集**                 | 依上述 O/S/P/V/SV/SP/VP/SVP 规则对轨道分类；结构分 `ordered / substitutional-only / vacancy-only / positional-only / mixed`。 | I3；M/M/H；M       | X      |
| **DO02** | **无序所在子晶格**                 | 分 `Na-only / framework-cation-only / anion-only / multi-sublattice / none`。 | I3；L/M/H；N       | B      |
| **DO03** | **Na 占位轨道型**                  | 分 `全部满占位 / 单一部分占位轨道 / 多个部分占位轨道 / Na与其他元素混占`。 | I3；L/M/H；N       | B      |
| **DO04** | **报告晶胞计量 commensurability**  | 在明确 conventional/primitive cell convention 后，联合检查各 species 的 `multiplicity×occupancy`、报告组分和 split-site capacity/conflict 约束；分 `报告胞内整数相容 / 有限分母提示需超胞 / 不一致或未决`。整数计数只说明计量相容，不证明存在物理有序构型。 | I3；M/M/H；U?      | A      |
| **DO05** | **跨子晶格无序耦合图**             | 无序轨道作节点，共享配位阴离子/多面体则连边；分 `相互隔离 / Na-host 二部耦合 / 多子晶格连通`。 | I3；M/H/H；U?      | A      |
| **DO06** | **无序轨道环境一致性**             | 部分占位/混占轨道的 CN/几何标签是 `单一 / 多种 / 主要 ambiguous`。 | I2/I3；M/H/H；U?   | B      |
| **DO07** | **无序—winding backbone 位置关系** | 令 `U_B` 为投影到 winding backbone 轨道集 `B` 的无序轨道，`C⊆B` 为临界轨道；按固定决策树分 `off-backbone (U_B=empty) / all-backbone-orbits (U_B=B) / critical-only proper subset / noncritical-only proper subset / mixed proper subset`，并报告 `|U_B|/|B|` 与 `|U_B∩C|/|C|`。这样“覆盖广”与“落在关键点”不会重叠。 | I2/I3；M/H/H；N/U? | A      |
| **DO08** | **无序—临界瓶颈共定位**            | 首次贯通窗口 rim 或邻近多面体是否含无序轨道；分 `none / subset / all critical throats`。 | I2/I3；M/H/H；N/U? | A      |
| **DO09** | **报告 vacancy-orbit 网络维度**    | 仅将 Na 部分占位轨道的“未占据份额”视为平均 vacancy capacity，并在同一候选位点图上求 `0–3D`；必须叫 `reported vacancy-capacity graph`，不能叫真实空位轨迹。 | I3；H/H/H；N/U?    | B      |
| **DO10** | **positional split-site 网络维度** | 对互斥过近的 split positions 建图并保留平移标签；分 `局域簇 / 1D / 2D / 3D`。只适用于明确精修 split sites 的实验 CIF。 | I3；M/H/H；M/U?    | B      |
| **DO11** | **占位冲突图拓扑**                 | 过短、不能同时占据的 sites 作 conflict-graph 边；分 `独立 pairs / 有重叠 maximal cliques / finite connected clusters / periodic conflict network`。冲突不具传递性，connected component 只能叫 cluster，不能自动当成“至多占一个”的 group；严格互斥单元用 maximal cliques/hyperedges。 | I3；M/H/H；M/U?    | A      |
| **DO12** | **异标签接触网络是否贯通**         | 在平均 CIF 的占位/元素标记图中，只取连接不同标签的 contact edges 并求 winding rank；分 `0D / 1D / 2D / 3D`。它是 heterolabel contact network，不是已观测的无序畴边界，也不给实际短程有序。 | I3；H/H/H；U?      | B      |
| **DO13** | **无序轨道局域化/分散型**          | 在 host/Na orbit incidence 图上，以同一无序类型形成的组件分 `single cluster / multiple clusters / distributed backbone`。 | I3；M/H/H；U?      | B      |
| **DO14** | **占位标签导致的拓扑对称破缺指数** | 在同一 gain-compatible `Aut_T` 中比较不看占位标签与保留 full/partial 标签的 component stabilizers；只有真实子群包含成立时报告指数 `1 / 2 / >2`，否则报 `non-nested/ambiguous`。 | I2/I3；M/H/H；M/U? | C      |
| **DO15** | **占位—局域键价一致性**            | 最高占位 Na 轨道是否也是 `|BVS−1|` 最小者；分 `一致 / 并列 / 混合 / 反向`。 | I1/I3；L/H/H；N/U? | A      |
| **DO16** | **占位—BVSE 极小点一致性**         | 高占位轨道是否对应更低 BVSE minima；分 `单调一致 / 简并 / 无序 / 反向 / 无匹配`。 | I2/I3；M/H/H；N/U? | A      |
| **DO17** | **有界电中性占位调整自由度**       | 以 signed `Delta occupancy` 为变量，加入每个 site 的非负/容量/multiplicity bounds、conflict constraints、组分与形式电荷守恒，排除零解和整体倍乘；分 `无非零可行调整 / Na-only / 需 framework coupling / 多独立自由度`。它仍只是约束可行性，不是缺陷形成能。 | I1/I3；M/H/H；U?   | A      |
| **DO18** | **ADP 各向异性—通道方向关系**      | 仅对有可靠 anisotropic displacement parameters 的同温实验 CIF，比较 Na 主 ADP 轴与 winding direction；分 `aligned / transverse / mixed / unavailable`。ADP 同时含热运动与静态无序，不能单独解释成迁移方向证据。 | I3；M/M/H；N       | B      |
| **DO19** | **split-site 位移—通道关系**       | 对 positionally disordered combined site，比较 split vector 与候选 hop/void edge；分 `along-edge / toward-window / transverse / mixed`。 | I3；M/H/H；N/U?    | A      |
| **DO20** | **无序消除后的对称恢复型**         | 将混占视为统一平均 species、部分占位标签去除后重新求对称；分 `不变 / 恢复更高点群 / 恢复更小原胞 / 两者兼有`。 | I3；M/H/H；N/U?    | B      |
| **DO21** | **母相轨道分裂与无序关系**         | 有可靠母相/原型时，分 `无分裂 / 2-way / ≥3-way`，并标分裂主要落在 Na、host 或 anion。 | I2/I3；H/H/H；M/N  | C      |

对 DO 家族应设硬性数据门：生成结构、占位被规范化为 1 的数据库结构、未给精修温度或不含 split/ADP 信息的 CIF，不能与高质量实验 CIF 混作同一观测。DO09–DO12 尤其不能解释为实际 vacancy correlation；平均 CIF 不包含相邻晶胞中谁与谁同时占据。

### 3.6 对称性与信息复杂度：从“空间群号”扩展到谁打破了谁的对称

晶体结构信息量已有成熟公式，并已有可直接读取 CIF 的 [crystIT](https://journals.iucr.org/j/issues/2021/01/00/oc5005/index.html)。因此总 bits/atom 本身不是新量；值得探索的是 Na、host、占位和候选迁移骨架之间的**复杂度分解与关系型分类**。

| ID       | 分类量                            | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | --------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **SI01** | **晶体学 orbit 信息量等级**       | 按 Wyckoff multiplicities 计算 `I_G`/bits per atom；分箱只能由 X 的预注册分位数或文献固定界限产生。 | I0/I3；L/M/H；M    | X      |
| **SI02** | **Na 与 host orbit 熵关系**       | 在各自子晶格内以 `p_i=m_i/sum_j m_j` 归一化，分别计算 Na 与 host 的 orbit-multiplicity entropy；分 `Na<host / 相近 / Na>host`。 | I0/I3；L/M/H；M/U? | A      |
| **SI03** | **环境分区—Wyckoff 分区关系**     | 在 symmetry-equivariant 邻居规则下分别比较 Wyckoff、CN、几何分区：分 `equal / environment coarsens（合并多个轨道） / CN→geometry 的进一步合并 / apparent split或crossing（算法、cutoff、占位/无序QC失败）`。精确有序 CIF 中，同一 Wyckoff orbit 不应被对称完备环境规则正常“分裂”。 | I2/I3；M/H/H；M/U? | A      |
| **SI04** | **复杂度层级词**                  | 对 chemical、coordinational、combinatorial、crystallographic complexity 的偏序编码；如 `chemical<coordination<crystal` 或出现倒置。 | I2/I3；M/H/H；M    | B      |
| **SI05** | **winding backbone 条件信息关系** | 在同一表示内比较 `H(orbit|backbone)`、`H(orbit|off-backbone)`，并以各自节点/轨道质量归一化；分 `backbone更简单 / 相近 / 更复杂 / 支持不足`。同时报告 backbone 占比，避免子集大小伪造“更简单”。 | I2；M/H/M；U?      | A      |
| **SI06** | **对称压缩比**                    | 在 symmetry-expanded primitive cell 的同一节点/边集合上，比较 sites/edge germs 数与空间群或图自同构 orbit 数；分别对 Na、host、void 输出精确比值，主分析用它们的有序关系。 | I0/I2；L/M/M；M/U? | B      |
| **SI07** | **空间群容差平台型**              | 在预冻结 `symprec` 网格上求空间群；分 `稳定 / 单调恢复高对称 / 非单调不稳定`。这是质量与近似对称候选。 | I0；L/H/M；M/U?    | A      |
| **SI08** | **子晶格对称破缺来源**            | 把完整结构、去 Na 骨架、Na 子晶格嵌入同一晶格与原点，分别得 `G_full,G_host,G_Na`；先要求 `G_full=G_host∩G_Na` 且 `G_full` 为后二者子群，再按严格包含决策树分：三者全等=`neither`；`G_host>G_full=G_Na`=`Na-ordering-limited`；`G_Na>G_full=G_host`=`framework-limited`；后二者均严格大于且交为 `G_full`=`complementary-both`；等式/包含失败=`construction-or-tolerance failure`。`G_host` 与 `G_Na` 不嵌套本身可属于 `complementary-both`，不再另设重叠类别。 | I0/I3；M/H/H；N/U? | A      |
| **SI09** | **反演破缺来源**                  | 以不重叠决策树比较完整结构与去 Na 骨架：`完整结构仍中心对称 / host中心但加入Na后非中心（Na-induced） / host已非中心且完整结构仍非中心 / 对称判定不一致`。极性另由 SI13 处理。 | I0/I3；M/H/H；N/U? | A      |
| **SI10** | **传输方向表示分解型**            | 对实际 `D_alpha` 维 winding translation space 的有理表示作不可约秩分拆；输出 `1`、`2`、`1+1`、`3`、`2+1`、`1+1+1` 等，而非预设三根轴。它描述方向子空间怎样被对称操作耦合。 | I0/I2；L/M/M；M/U? | A      |
| **SI11** | **Na site-symmetry 字母表**       | Na 位点分 `全部 general / 全部 special且同型 / 多种 special / general+special`。 | I0/I3；L/M/H；N    | B      |
| **SI12** | **局域—site-group 对称兼容性**    | 在 symmetry-equivariant 邻居规则下，局域环境群应包含 site group；分 `equal / accidental higher local symmetry / incompatibility（算法、cutoff或symprec失败） / ambiguous`。不把“局域更低”当作精确 CIF 的正常物理类别。 | I2；M/H/M；M/U?    | B      |
| **SI13** | **允许极化子空间—通道子空间关系** | 由完整点群求允许极化向量子空间 `P`（点群 `1` 可为3D、`m` 可为2D，并非总有唯一 polar axis），与 winding 子空间 `W` 比较；分 `nonpolar / P包含于W / P与W正交 / partial-oblique`，使用实际晶格度量。 | I0/I2；M/M/M；N/U? | B      |
| **SI14** | **组合—嵌入—晶体学手性关系**      | 分开交叉 PG26 的组合定向反演、HF12 的 embedded-net chirality 与完整 exact space group 是否属于 65 个 Sohncke types；分 `均非手性 / 仅组合 / 仅嵌入或晶体学 / 一致 / 容差不稳`。Sohncke type 对正确确定的完整结构可判 crystallographic structural chirality，但不能与仅 22 个 chiral/enantiomorphic space-group types 或抽象图手性混称。 | I2；H/M/M；M/U?    | C      |
| **SI15** | **母相 Wyckoff 分裂级别**         | 有冻结原型时，母相轨道在观测结构中分成 `1 / 2 / ≥3` 个；分别对 Na 和 host 输出。 | I2/I3；H/H/H；M/N  | C      |

### 3.7 BVS、点电荷与 BVSE：从单一势垒数值扩展到能量景观拓扑

键价模型和 valence maps 用于定位可迁移离子/通道已有长期历史，见 [Bond Valence Model 综述](https://pubs.acs.org/doi/10.1021/cr900053k)、[energy-scaled bond-valence landscape](https://doi.org/10.1039/B901753D) 与 [BVPA/BVSE pathway analysis](https://doi.org/10.1021/acs.chemmater.0c03893)。因此“算一个 BVSE barrier”已经是直接先例。下面更探索性的方向是：只保留 minima、critical bottlenecks、子水平集连通和轨道关系，不声称它们等于真实自由能面。除非连续插值后另行验证 `grad E=0` 且 Hessian 恰有一个负特征值，本文不把网格 minimax bottleneck 称为 Morse 意义的一阶鞍点。

| ID       | 分类量                            | 操作定义与建议离散值                                         | 输入；风险；状态   | 优先级 |
| -------- | --------------------------------- | ------------------------------------------------------------ | ------------------ | ------ |
| **EL01** | **Na BVS 失配符号模式**           | 对 Na 轨道按 `BVS−1` 分欠键/匹配/过键；结构分 `全欠 / 全匹配 / 全过 / 正负混合`。 | I1；L/H/M；N       | B      |
| **EL02** | **键价应力所在子晶格**            | 比较 Na、host cations、anions 的中位绝对 BVS mismatch；分 `Na主导 / host主导 / anion主导 / 并列`。 | I1；M/H/M；N/U?    | A      |
| **EL03** | **Na 点电荷位点能级数**           | 仅对统一形式电荷和 Ewald/边界 convention 下的 point-charge/Madelung site-energy proxy，以冻结误差容差聚类；分 `单一 / 二级 / ≥3级 / 不稳定`。`|BVS−1|` 级数由 EL01 另报，不能称能量。 | I1/I2；M/H/M；N    | B      |
| **EL04** | **CN 排序—静电能排序一致性**      | 比较 Na orbit 的 CN 和点电荷/Madelung site energy 偏序；分 `高CN更低能 / 低CN更低能 / 无单调 / 单一轨道`。 | I1/I2；M/H/M；N/U? | B      |
| **EL05** | **报告 Na 位—BVSE minima 匹配**   | 分 `全部一一对应 / 部分对应 / 无对应 / 存在额外未占据 minima`。 | I2/I3；M/H/H；N    | B      |
| **EL06** | **低能间隙储库轨道数**            | 未匹配且在预注册相对能窗内的 BVSE minima 为 `0 / 1 / ≥2` 个对称轨道；称候选储库，不称真实空位。 | I2；M/H/M；N/U?    | A      |
| **EL07** | **BVSE 秩激活词**                 | 随能阈升高记录 `0→1→2→3` 等 winding-rank 序列和缺失阶段；是 VN06 的能量版本。 | I2；L/H/M；N       | A      |
| **EL08** | **局域环—长程环能量首生次序**     | 在同一 BVSE 子水平 filtration 中，比较首个 reduced/simple zero-gain cycle 与首个 nonzero-gain winding cycle 的阈值；分 `local-first / simultaneous / winding-first / 均未生`。不把 H0 的 basin merge 与 H1 的 cycle birth 当成同一事件。 | I2；M/H/M；N/U?    | A      |
| **EL09** | **BVSE minima merge-tree 类型**   | 只对 H0 子水平集组件合并树 canonicalize；分 `balanced / comb-like / multifurcating`，另标哪个叶类对应已占据 Na。merge tree 不编码 zero-gain loops 或 winding；若需环信息应另用 EL08/extended persistence。 | I2；M/H/M；M/U?    | B      |
| **EL10** | **critical-barrier orbit 字母表** | 将连接 minima 的 minimax bottleneck/grid critical points 按空间群、邻接环境和 barrier level 分轨道；分 `1 / 2 / ≥3` 类。只有通过连续梯度/Hessian 门后才另标 `first-order saddle`。 | I2；M/H/M；N/U?    | B      |
| **EL11** | **首次贯通 barrier-orbit 简并**   | 在冻结能量容差内，产生首个 nonzero winding 的 critical barriers 分 `单一 orbit / ≥2 非等价 orbits 精确并列 / 近并列未决 / 不贯通`；方向阈值分裂由 EL14 记录。 | I2；M/H/M；N/U?    | A      |
| **EL12** | **能量瓶颈集中/分布型**           | 达到 full rank 的路径是否由 `单一 barrier orbit / 每方向一个 / 多 orbit 分布式` 控制。 | I2；M/H/M；N/U?    | A      |
| **EL13** | **低能 backbone 覆盖型**          | 在 full-rank 临界能附近，参与 winding cycles 的 minima 占 `全部 / 多数 / 少数`；比例箱界需预注册，主标签可先用“全部/非全部”。 | I2；L/H/M；N/U?    | B      |
| **EL14** | **方向阈值分裂谱**                | 令 `E_k` 为 winding rank 首次达到 `k` 的最小能阈；对 `D_alpha≥2` 输出归一化相邻间隔 `Delta_k=(E_{k+1}-E_k)/(E_D-E_1+epsilon)` 的排序谱，并按冻结容差分 `simultaneous / one-dominant-gap / multi-stage / unstable`；`D≤1` 为 `not-applicable`。它增加阈值间隔信息，不再复制 EL07 的 rank-jump word。 | I2；M/H/M；N/U?    | B      |
| **EL15** | **barrier-orbit cut number**      | 按 critical-barrier edge orbit 删除边，求使临界能网络 rank 降低的最少 orbit 数；分 `1 / 2 / ≥3`。 | I2；M/H/M；N/U?    | A      |
| **EL16** | **minima/barrier graph 转移数**   | 对低能 minima/critical-barrier graph 数 node/edge orbits；分 `1,1 / 1,q / p,q`，并与 `G_occ`/`G_void` 转移数比较。 | I2；M/H/M；M/N     | B      |
| **EL17** | **几何—能量关键窗一致性**         | critical geometric throats 与 critical BVSE bottleneck/barrier orbits 的映射分 `一一 / 多对一 / 一对多 / 不一致`。 | I2；M/H/M；N/U?    | A      |
| **EL18** | **三种静态位点代理排序一致性**    | 仅在 occupied Na↔void node↔BVSE minimum 的共同可靠匹配 orbit set 上，以“值越低越有利”统一方向，比较 `A=|BVS−1|`、`B=point-charge site energy`、`C=BVSE minimum value`。冻结各代理的 tie tolerance；若所有 orbit 对的三值符号（含 tie）相同，两个代理的 weak order 才算完全相同。分 `A=B=C / exactly one identical pair (AB/AC/BC) / no identical pair / <2 matched orbits`，另报三组 Kendall tau-b 以保留部分一致性。BVS mismatch 不是能量，故只称代理排序。 | I1/I2；M/H/M；U?   | A      |
| **EL19** | **混合价/氧化还原储库代理**       | 同一 host 元素的 BVS 是否落在 `单价态邻域 / 两个相邻价态 / 多价态 / 无法判定`。不等于真实电子局域化。 | I1/I3；H/H/H；N/U? | C      |

EL07–EL18 与单一 `bvse_barrier_estimate` 的区别在于保留了**景观的拓扑事件和轨道组织**。最需要警惕的是把 bond-valence energy 当成真实动力学：它适合作为统一的低成本排序/拓扑代理，但不能替代 NEB、AIMD 或实验激活能。

## 4. 对用户给出的 S1–S12 的重新审计

下表专门修正“U0/未验证”的表述。结论针对精确定义而不是标题名称；检索截至 2026-08-17，`未找到` 仍不等于绝对不存在。

| 原候选                                      | 审计结论                                                     | 原因与建议                                                   |
| ------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **S1 periodic path redundancy**             | **近先例，不能强称 U0**                                      | 动态 [path entropy](https://www.nature.com/articles/s41467-026-71316-z) 已把路径多样性与 Li 迁移联系起来；[周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) 也已有成熟表示。精确静态 Na periodic connectivity 本轮未见跨体系检验，但必须区分：ordinary quotient connectivity≠lift connectivity；删 quotient edge 是删整个 translation orbit；超胞 min-cut 随截面尺寸增长；方向冗余需固定 `(v,0)` 到 `(v,t)` 或使用 cohomology cut class。更好的定义是 PG01–PG07/VN16。 |
| **S2 Na graph bipartite**                   | **本轮未找到直接 SSE 电导分类先例，保留在机制探索层**        | 必须判无限 lift：只有 odd-length、zero-net-gain closed walk 才破坏二分性。普通 quotient 的 gain self-loop 或奇数 torus cover会制造假象。三种表示不能混成一个标签；本报告以 `G_occ` 为主表示，`G_void/G_bvse` 只作表示一致性 follow-up。 |
| **S3 single-Wyckoff-orbit percolation**     | **强近先例，不是精确定义的直接先例**                         | [bcc 阴离子骨架的 Li 设计规则](https://www.nature.com/articles/nmat4369) 讨论相邻四面体间隙构成的理想化低能贯通环境，fcc/hcp 路径可能必经不同配位环境；[Na 高配位位点设计](https://www.nature.com/articles/s41467-023-43436-3) 也讨论有利位点的直接连接。但这些都没有按 single Wyckoff orbit 作逐轨道诱导子图检验。可保留，主张应是精确实现与跨体系审计，而非核心概念首创。 |
| **S4 Na graph regularity**                  | **本轮未见精确直接检验，但信息量有限**                       | 规则度是成熟图量；可能主要反映 orbit 数和体系。PG08、PG16、PG18、PG20 比单纯 `degree 全相等` 更有区分力。 |
| **S5 unbranched/branched**                  | **建议删除主候选**                                           | 对单个连通、局部有限且共紧周期的 infinite-lift component，若最大 degree≤2，该分量只能是有限 cycle 或 double ray，稳定子平移秩至多为 1。因此在一个真实 D≥2 分量中必有分支；但多个互不连接的一维链族可沿不同方向存在，不能先错误聚合 gains 再套此结论。 |
| **S6 framework dimension**                  | **有强方法学/近先例，不宜强称 U0**                           | 去移动离子后的 host graph、Li-free topology 和晶体 net 维度已有大量方法；[JACS 2025](https://doi.org/10.1021/jacs.5c04828) 同时分析 Li-only/Li-free 点集。精确的 Na 跨体系 `D_host×sigma` 仍值得做，但主张应是新应用/系统审计。 |
| **S7 mobile–framework dimension mismatch**  | **精确关系型分类本轮未见直接跨 Na-SSE 检验，保留**           | 构件本身均有先例，但 `(D_Na,D_host)` 或 `D_Na−D_host` 的跨体系审计仍相对干净。建议保留完整有序对 CE21，而不只留差值，以避免 `(3,2)` 与 `(1,0)` 被合并。 |
| **S8 Na environment multiplicity**          | **近先例很多，不能强称 U0**                                  | Na 局域环境数、CN、晶体学不等价位点和多面体类型已有筛选/个案研究。[Sc-NZSP 的 NMR+电导实验](https://www.nature.com/articles/s41598-018-30478-7) 在单材料中明确涉及 3 个不等价、部分占位 Na sites，是 S8/S9 的实验近先例。更有新意的是 CE03–CE08 的环境邻接、切换必要性和循环语法。 |
| **S9 inter-environment/orbit hop required** | **强近先例；精确删边必要性检验仍可保留**                     | 有利环境直接连接 vs 必经不利中间环境是 bcc/fcc/hcp、Na 高配位连接和 [Sc-NZSP 局域快交换触发长程传输](https://www.nature.com/articles/s41598-018-30478-7) 的机制邻居，但所检索文献没有统一执行“删除异环境边后逐分量重算 winding rank”的跨材料检验。应细化成 CN/geometry/Wyckoff 三张独立颜色层。 |
| **S10 framework polyhedron composition**    | **强近先例 N，不是精确量的直接先例 D**                       | [Li corner-sharing oxide framework 工作](https://www.nature.com/articles/s41563-022-01222-4) 已跨 8572 个 Li 氧化物按非 Li 阳离子多面体连接分类并验证候选；但它检验的是 Li-only corner-sharing connectivity，不是精确的 tetra/octa/prism single/mixed composition。后者仍可检验，但容易与化学体系共线；HF13–HF15 的序列与空间混合更有信息。 |
| **S11 polyanion condensation topology**     | **Li 家族内近先例，不宜强称 U0**                             | [Li ultraphosphate 工作](https://doi.org/10.1021/jacs.1c07874) 已明确使用 terminal/internal/branching tetrahedra、chain/ring/layer 与缩合结构并测量电导；它不是 Na 跨家族统一分类。可作为标准化复现量，但创新点宜放在 HF22 的混合组件谱或其与 Na/void network 的关系。 |
| **S12 cycle rank / Betti-1**                | **方法近邻必须披露；精确 periodic gain-graph 量仍属近而非直接** | [JACS 2025 multiscale topological learning](https://doi.org/10.1021/jacs.5c04828) 已直接使用 Li-only/Li-free persistent `beta1`/cycle density，但并非 translation-labelled periodic migration-graph cyclomatic rank。普通超胞 `E−V+C` 随复制膨胀；逐分量应定义 `beta1,alpha=|E_alpha|−|V_alpha|+1`、`D_alpha=rank im(tau_alpha)`、`beta_zero-gain,alpha=rank ker(tau_alpha)=beta1,alpha−D_alpha`。最后一项是 zero-net-gain homology rank，不等于某个唯一几何 simple-ring 数，也不能跨断开分量相消。 |

由此，前一轮最干净的精确命题仍是：S2 的**无限 lift 二分性**、S7 的**移动—骨架维度关系**，以及扩展后的方向/轨道组织量；最不应继续作为“新量”主打的是 S3、S9、S10 与未拆分的 S12。

## 5. 157 个扩展候选条目怎样变成可执行计划

本表共列出 157 个扩展候选条目（PG 30、VN 24、HF 24、CE 24、DO 21、SI 15、EL 19），并不建议一次全部进入统计模型。这里的“条目”不等于 157 个彼此独立或都具有文献新颖性的假说：一部分是成熟方法的 Na 应用，一部分是关系型组合，一部分是同一对象的表示/敏感性变体。它们应被视为七个**假说家族**，先做与电导率无关的结构审计。

### 5.1 第一阶段：先实现共享 helper，而不是逐个写 157 个脚本

| 实现模块                       | 核心对象/直接产物                                            | 典型交叉依赖                                                 |
| ------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **P1. `PeriodicGainGraph`**    | PG01–PG30 的统一 gain-graph/Aut_T 底座；S1/S2/S4/S7/S12 的严格版本 | PG23/27/28 调 P2；PG30 调 P4/P8；void/BVSE 版本由 P3/P9 提供 |
| **P2. `CharacteristicCovers`** | PG23、PG27、PG28 与图算法回归测试                            | 依赖 P1 的规范 gain graph                                    |
| **P3. `VoidFiltration`**       | VN01–VN18、VN20 的空隙/喉道对象                              | VN19 还需 P4；VN21 需 P5；VN22 需 P9；VN23–24 需 P4/P8       |
| **P4. `EnvironmentColoring`**  | CN、ChemEnv、Voronoi topology 与标签歧义；CE01–CE15          | CE16–17 需 P3/P5；CE20–21 需 P1/P5；CE24 需 P8；HF13–15 需 P5 |
| **P5. `HostNet`**              | HF01–HF15、HF21–HF24 的宿主键图/tiling 对象                  | CE20–21 需 P1/P4；CE22 还需 P1/P3；CE23 需 P3/P6；CE18–19 由 P8 |
| **P6. `RigidityProxy`**        | HF16–HF20                                                    | CE23 还需 P3/P5                                              |
| **P7. `DisorderOrbit`**        | DO01–DO14、DO17–DO21                                         | DO15 需 P10；DO16 需 P9；SI08/CE18–19 需 P8                  |
| **P8. `SymmetryRelation`**     | 子晶格空间群、稳定子、交集/指数、容差平台；SI01–SI15         | VN24、CE11/18/19 还需各自几何/子晶格对象                     |
| **P9. `EnergyFiltration`**     | BVSE minima、critical-barrier graph、子水平 filtration；EL05–EL17 | VN22 需 P3；DO16 需 P7；EL18 需 P3/P8/P10                    |
| **P10. `StaticSiteProxy`**     | BVS mismatch 与 point-charge/Madelung proxy；EL01–EL04、EL19 | DO15 需 P7；EL18 还需 P3/P8/P9                               |

### 5.2 机制探索层的首批计算优先级：17 个 core + 7 个 gated

以下 24 项是从 157 项中压缩出的**机制探索计算优先级**，不再整体作为 confirmatory design-rule 主检验清单。与 5.6 的 8 条损耗池重合者以 5.6 为准：四关全过后才可能升级为主检验；其余维持探索身份。这里的 “core” 不是说所有量共享同一个样本分母，而是说：只要其基础表示（occupied/void/BVSE/host）可构造，就不再要求某个额外匹配事件成功。每个表示家族仍应冻结自己的可用总体。

**Core-exploratory（17 项）**

1. PG03 `Z2` 平移余同调最小支撑谱
2. PG05 elementary-cycle 可达格基指数
3. PG07 infinite-lift block-orbit 稳定子秩谱
4. PG08 满秩 periodic k-core 持久度
5. PG09 gain-compatible Cartesian 素分解
6. PG16 介观位点分离半径
7. VN02 首次贯通临界窗口轨道简并
8. VN06 空隙秩激活词
9. VN17 两端口 characteristic-cover 路由签名（`not-resolved/cover-dependent` 作为预注册输出保留，不因失败删样本）
10. HF07 接触层级拓扑持久词
11. HF16 共角铰链网络维度
12. CE06-CN 环境切换 successive-minima 向量（几何层、Wyckoff 层和联合三元组为 follow-up；CE04 仅作 CN 层三类映射摘要）
13. CE18 Na/host 平移格 commensurability
14. EL07 BVSE 秩激活词
15. EL15 barrier-orbit cut number
16. S2 `G_occ` 无限 lift 二分性（`G_void/G_bvse` 只作表示一致性 follow-up）
17. CE21 mobile—framework 维度有序对

**Gated-exploratory（7 项）**

1. VN24 占据位—空隙位稳定子关系：仅 VN23 关系本身为可靠 perfect-1:1 的子集
2. HF13 临界通道的多面体连接词：仅 VN03 family 与 host-bond 平台均稳定者
3. CE16 mobile/void × host incidence 拓扑（纯平移商）：仅 incidence 归属稳定者
4. CE22 Na 图—void 图 chain-map 同调型：仅存在合法 gain-compatible chain map 者
5. DO07 无序—winding backbone 位置关系：仅 I3 高质量实验精修子集
6. SI08 子晶格对称破缺来源：仅共同晶格/原点下三套群均稳定者
7. EL18 三种静态位点代理排序一致性：仅三方 orbit 匹配可靠者

这 24 项覆盖七个结构家族。每个 gated 项必须预注册自己的 eligibility set、成功率、缺失机制和多重性 family；不得把“匹配失败”当作普通结构类别，也不得与 core 项共用一个看似统一的样本分母。它们可以批量计算并在探索层以 FDR 控制，但不能因数学定义精细就自动升级为设计规则。

### 5.3 基础估计量—表示—粗化的依赖关系

157 个条目里存在有意保留的“同一数学骨架、不同结构表示”以及逻辑粗化。它们适合做跨表示复现，不应被当成互相独立的 157 次发现机会：

| 基础对象                     | 表示版本/粗化                                                | 统计处理                                                     |
| ---------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| winding-rank activation word | PG11（occupied/general graph）、VN06（void）、EL07（BVSE）；VN07 是 VN06 的方向简并粗化；EL14 已另定义为阈值间隔谱 | 先作一个跨表示 omnibus，再看一致性；不得把三个同向显著当作三次独立证据 |
| component dimension spectrum | PG13、VN13、HF08                                             | 作为 occupied/void/host 三视图；主张必须写明是哪一表示       |
| component merge hierarchy    | PG22、VN15、EL09                                             | PG/VN/EL 的 filtration 不同；EL09 只含 H0，不与环出生混称    |
| orbit deletion/cut           | PG02、VN16、EL15                                             | 共用 deletion-orbit 逻辑，但边对象分别是 hop/throat/critical barrier |
| 环境切换必要性               | CE06 为完整向量；CE04 映射为 `全零/零正混合/全正` 三类       | CE04 只作派生摘要；若进入主检验，两者合计只占一个假说名额    |
| 子晶格 commensurability      | CE18 为完整群/SNF 关系；CE19 为体积指数粗化                  | 优先 CE18；CE19 只用于解释与回归测试                         |
| 几何—能量/占据跨表示关系     | VN22、EL17 是比较量；CE22 是要求合法 chain map 的强版本      | 先冻结共同匹配集；映射失败单独报告，不做有利类别             |

### 5.4 第二阶段储备池

首批若在某家族内完全没有体系内变异，再从同一族替换；若有变异但主量不相关，可用预注册的相邻候选定位“哪个结构层级失效”。建议顺序：

- 周期图储备：PG04、PG10、PG13、PG18、PG22、PG24。
- 空隙储备：VN03、VN05、VN10、VN13、VN16、VN22。
- 骨架储备：HF08、HF14、HF18、HF20、HF23、HF24。
- 环境储备：CE03、CE07、CE11、CE17、CE23。
- 无序储备：DO04、DO05、DO08、DO11、DO17、DO19。
- 对称/信息储备：SI02、SI03、SI05、SI07、SI10。
- 能量储备：EL02、EL06、EL08、EL11、EL17（EL18 已进入 gated-exploratory）。

### 5.5 仅作负对照或方法附录

- 单一空间群号、总 atoms/cell、单纯 Wyckoff 数、普通 degree regularity。
- 原始 Voronoi 节点数和把每个空腔叫“真实间隙位”的标签。
- 普通超胞环数、超胞 centrality、固定超胞 articulation count。
- 强制 bcc/fcc/hcp 阴离子分类而不给 template ambiguity。
- 只在一个默认 cutoff 下得到、没有参数平台的任何 R2 分类。
- 对没有可靠 occupancy/split-site/ADP 的 CIF 计算 DO/ADP 机制量。

### 5.6 严格 design-rule 单轨：8 条候选作为损耗余量

这里必须把**逐结构分类变量**与**方法学基础设施**分开。translation-labelled 晶胞压缩连接图、参数扫描规则、看电导率之前的前置筛除条件、周期算法回归测试和多重校正方案只是基础设施，不是候选分类量。

现有 5 条逐结构候选为：

| 候选                          | 对应条目     | 当前状态                                       |
| ----------------------------- | ------------ | ---------------------------------------------- |
| 通道方向贯通顺序              | VN06/VN07    | Gate 1 与 Gate 4 仅作粗估通过；Gate 2/3 待实测 |
| 长程路径是否必须改变配位环境  | CE04/CE06-CN | Gate 1 与 Gate 4 仅作粗估通过；Gate 2/3 待实测 |
| 关键通道的多面体连接方式      | HF13         | Gate 1 与 Gate 4 仅作粗估通过；Gate 2/3 待实测 |
| 关键瓶颈是唯一还是并列        | VN02         | Gate 1 与 Gate 4 仅作粗估通过；Gate 2/3 待实测 |
| Na 通道维度与宿主骨架维度关系 | CE21         | Gate 1 与 Gate 4 仅作粗估通过；Gate 2/3 待实测 |

在公开文献专项审计后，补充池暂时只加入 3 条，把总池扩为 8 条；中心线形态保留为探索储备而不占严格 design-rule 名额：

| 补充候选                      | 对应条目                    | 文献状态                                                     | 单轨位置                                                     |
| ----------------------------- | --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **周期路径对称族冗余/脆弱性** | PG02/PG04/VN16 的预注册粗化 | 广义路径多样性已有直接动力学证据，周期图与连通度构件成熟；整条 edge/vertex orbit 删除后重算 winding rank 的精确组合未见直接电导检验（`D/N/M/U?`） | `selection-ready` 暂留；必须冻结主图表示、作用群和结构级粗化 |
| **笼—窗口净空/收窄剖面**      | VN14                        | “均匀路径”、大瓶颈和笼间连通机制已有直接/近先例；`低调制/单主瓶颈/多非等价瓶颈` 的精确互斥分类未见直接检验（`D/N/M/U?`） | `selection-ready` 暂留；创新点只能是剖面分类，不能声称“大瓶颈”本身新颖 |
| **关键窗口 rim 化学语法**     | VN10                        | 局部瓶颈组成影响跳跃势垒与宏观电导已有强近先例；循环 run/顺序语法未见直接检验（`N/M/U?`） | 条件式暂留；只在完全有序、rim≥4 且有至少两种标签的 eligible subset 上计算 |
| 临界通道中心线形态            | VN20                        | 有直、弯曲、螺旋路径的单材料案例和成熟提取方法，但未见统一离散分类；也没有可预设的单调有利方向（`N/M/U?`） | 不进严格 8 条，留 mechanistic/exploratory 储备               |

“暂留”不等于已经进入主检验。预计 Gate 2 与 Gate 3 会淘汰约 30%–40%；最终 confirmatory 主检验只保留四关全过且类别支持充分的 5–6 条，绝不因为某一条文献新颖而突破样本量上限。

## 6. 参数平台与预注册规则

### 6.1 每个 R2 项至少输出三样东西

先为每个算法家族冻结参数域 `Theta` 和测度 `mu`（例如长度 cutoff 用线性还是对数均匀必须事先写明），再用固定 quadrature/grid 近似；不同建图算法的参数不能混成一个“稳定率”。不要只输出默认点标签，至少输出：

1. **模态类别**：占参数测度最大的类别 `argmax_c mu{theta:f(theta)=c}`。
2. **稳定质量**：该模态所占 `mu` 质量，而不是任意网格上的简单点数比例。
3. **平台宽度/最坏情形**：一维参数报最大稳定区间宽度；多参数报连通稳定域或“全域一致/有反例”。

可冻结例如：稳定质量 `≥0.8` 才进入主分析，`0.5–0.8` 进入敏感性分析，`<0.5` 标为 `unstable/undefined`。0.8/0.5、参数域、测度和 quadrature 都必须在看电导率前冻结；否则加密某一段网格就能任意改变简单“网格点占比”。

### 6.2 建议共同扫描的参数

- `symprec`：至少三个数量级附近的合理值，并记录单调恢复与非单调跳变。
- Na/host 邻接：至少两种物理规则；例如半径和、Voronoi solid angle、共享阴离子/多面体路线。
- void probe radius：围绕 Na 有效半径和文献合理范围做固定网格。
- ChemEnv/CSM：报告最佳标签和次佳标签差；差太小即 `ambiguous`。
- BVSE：参数表版本、氧化态解、网格分辨率和相对能阈统一。
- 环/笼：ring convention、natural tiling 是否存在、失败原因都写入输出。

### 6.3 周期算法的必做回归测试

- 一个节点 + primitive gain `e1` self-loop：lift 是 1D double ray；gain `2e1` 另检验两个 cosets 与 SNF/index。
- 三个互不连接分量分别只绕 `ex/ey/ez`：全局 gain span 看似 3，但正确 `D_max=1`。
- 三边 quotient triangle 总 gain `e1`：无限 lift 可二分；另造 odd zero-gain 版本应非二分。奇数 torus cover 可非二分，不能据此替代 lift 判定。
- full-rank index-2 例，如 gains `2ex,ey,ez`，检查 component multiplicity 与 SNF。
- 随机顶点代表元 switching、`U∈GL(3,Z)` 换基、原点平移、原子排序、primitive/supercell 表示；周期不变量保持，raw gain coordinates 只要求协变。
- self-loop、parallel edges、digons 在建图/序列化中均不得丢失。
- 算法构造的 `Q_m` 必须与直接生成的**同一个 m** torus/supercell 有限图同构；不要求 `m=2,3,5` 的 treewidth、critical group 或 spanning-tree count 彼此相等，它们本来会随尺度增长。
- rank、infinite-lift bipartiteness、component rank–SNF 谱等真正周期不变量应对 primitive/supercell 表示保持；有限 cover signature 只检查预期增长律或收敛性质。
- 删除单一物理边、translation edge orbit、space-group edge orbit 必须是三个不同测试和名称。
- filtration 中同一阈值/tie tolerance 的边必须批量加入，验证事件次序对并列处理稳定。

## 7. 不看电导率时的四道主检验过滤器

四关全过才允许进入严格 design-rule 主检验；任何一关不过都降到探索层。执行顺序固定为 Gate 1 → Gate 2 → Gate 3 → Gate 4，避免先为昂贵算法写代码，再发现分类量根本不可使用。

### Gate 1：条件式化学可操作性

先要求写出：

> 如果后续发现类别 A 比类别 B 的电导更高，为了把材料推向 A，应当采取什么可合成执行的动作？

动作只能是换元素/阴离子、换骨架原型、掺杂/缺陷调控或烧结/热处理控制等真实化学操作。再按是否必须先计算该量区分：

- **intervention-ready（I）**：不先计算该量，也能说出怎样通过化学动作推动该结构量改变；可作为严格意义的设计规则候选。
- **selection-ready（S）**：必须先计算标签，才能从候选结构中挑选目标类别；允许进入主检验，但论文必须明确称为结构筛选工具，不能冒充可直接反推合成路线的设计规则。
- **descriptive-only（D）**：即使知道有利类别，也写不出可执行动作；只留 mechanistic/exploratory。

有物理解释不自动等于 I/S；数学精细、但无法连接到元素替换、原型选择、掺杂或工艺控制的图不变量，在这一关就应退出主轨。

### Gate 2：解盲前的体系内类别普查

这一步在 CIF 接入之后、电导率接入之前执行，绝不读取 `sigma`：

- 分别列出 NASICON、硫化物、卤化物等每个 `system` 内的类别频数和缺失率。
- 至少两个主要体系内部必须存在实际类别差异；若分类量几乎等同于“是不是 NASICON/硫化物/卤化物”，它只能描述体系，不能支持控制体系后的设计规则。
- 冻结稀有类合并、`other`、`not-applicable` 和 `ambiguous` 规则；不得在看到电导率后合并类别。
- 同时计算 Cramér's V、mutual information、adjusted Rand index 与条件熵等 X–X 关系。完全等价的候选优先保留定义更稳健、化学动作更清楚、计算更便宜者。

### Gate 3：参数平台与合理构造一致性

- 对 cutoff、`symprec`、探针/离子半径、配位判据和突出度阈值，在预注册参数域及测度下扫描，报告模态类别、稳定质量和最大连续平台。
- 稳定质量 `>80%` 才可继续主检验；`50%–80%` 只作敏感性/探索；`<50%` 标为不稳定。
- 对没有唯一算法对象的量，不再一律排除；必须实际实现并比较至少两种合理构造，报告逐结构一致率、类别混淆矩阵和按体系一致率。未经构造一致率实测者不得进入主检验。
- 两种合理构造不同且没有可辩护的唯一决策时，必须把 `ambiguous` 作为预注册输出；不能静默选择更符合预期的一种。
- 换原胞、整数晶格基、原点、原子顺序、primitive/supercell 表示和对称标准化后，真正的周期不变量必须保持不变或按定义协变。

网络表示 `G_occ/G_void/G_bvse` 的比较属于这一关，但三者不必被强迫成同一标签；应报告 `全一致/两者一致/全不一致/无法比较`。只在 `G_occ` 成立的结果只能称占据子晶格分类，不能自动解释成真实迁移网络。

### Gate 4：实际数据可计算性

- 在目标 CIF 集上达到预注册成功率，并报告失败是否集中在某体系或低质量结构。
- 只依赖坐标、元素和晶格的 I0/I1 量最安全；需要可靠占位、split sites、ADP、精修温度或短程有序的 I3 量只能在独立高质量子集分析。
- `missing/not-applicable/ambiguous` 必须区分；不得把算法失败补成一个普通结构类别。
- 本关按将要进入统计模型的实际 eligibility set 评估。若合格样本在分体系后不足以支持类别比较，即使定义正确也降到探索层。

现有 5 条只通过了 Gate 1 与 Gate 4 的粗估，Gate 2/3 尚未实测。补充候选也只是进入 8 条损耗池，不代表已经过关。

## 8. 与离子电导率关联时的统计设计

### 8.1 数据单位和标签统一

1. 一个观测单位应是“确定组成 + 相/结构 + 测量条件 + 文献来源”，不是简单的一条 CIF。
2. 区分 bulk、grain-boundary、total conductivity；主分析只混用预先指定的一类。
3. 室温实测与 Arrhenius 外推应分层；外推必须保留温区和激活能来源。
4. 同一材料多篇文献不能当独立结构样本。可采用预注册的优先级、随机效应或测量误差模型。
5. 多晶相、含杂相、玻璃陶瓷、复合电解质与单相晶态材料分开。

### 8.2 主分析不应是 157 次未经校正的 p 值

推荐层级：

```text
8–10 条 design-rule 损耗池
       ↓  四道过滤器（全程不看电导率）
最终冻结 5–6 条 confirmatory 主检验
       ↓
FWER 校正 + 体系内效应 + 全局控制体系模型

其余 PG/VN/HF/CE/DO/SI/EL mechanistic 候选
       ↓
按七个结构家族进入 exploratory 分析
       ↓
FDR 控制；结论只写“值得后续检验”
```

主模型可写为：

\[
y_i=\alpha_{\mathrm{system}[i]}+\beta x_i+\mathbf c_i^T\boldsymbol\eta
+u_{\mathrm{material}[i]}+v_{\mathrm{source}[i]}+\epsilon_i,
\]

其中 `y=log10(sigma_RT)`，`alpha_system` 控制 NASICON/硫化物/卤化物等体系，`c` 只放预注册的测量/数据质量协变量，`u_material` 与 `v_source` 分开处理同一材料重复和同一文献/实验室聚类（按数据结构决定嵌套或交叉）。分类量应以 planned contrasts 或有序趋势编码，而不是为每个稀有类别任意设 dummy 后挑最好结果。

这个固定 `system` 效应模型用于全局/体系内关联估计，不可原样用于一个从未见过的 held-out system，因为该系统的固定截距没有训练估计。外推检验应另用预注册的层级随机截距模型，或只在 held-out system 内评价排序/中心化效应方向；二者都要与关联模型的目标区分。

### 8.3 三类问题必须分别回答

- **全局关联：** 控制 system 后，全数据是否仍有关联？
- **体系内关联：** 每个主要体系内部方向是否一致？至少给效应量和置信区间，不只给 pooled p 值。
- **外推能力：** leave-one-system-out 时，用层级模型的预测分布，或在 held-out system 内中心化后检验排序/效应方向，规则能否保持？不得为未见 system 临时拟合一个固定截距后再称外推。

若 pooled 显著但每个体系内都不变，结论应是“体系标签的结构代理”；若体系内方向相反，不能给统一设计规则。

### 8.4 多重性和探索性结果

- 最终 5–6 个 confirmatory 候选分别在自己的预注册 eligibility set 与交换性方案下产生一个有效边际 p 值，再用全局 Holm（或事先冻结权重的 weighted-Holm）控制 FWER。不能因为样本分母不同就省略跨候选校正。
- 所有未进入最终 5–6 条的 mechanistic 候选，无论此前在 5.2 被称为 core 还是 gated，全部属于 exploratory；按 PG/VN/HF/CE/DO/SI/EL 七个家族或全局控制 FDR，结论措辞限于“值得后续检验”，不得称确认性设计规则。
- 所有置换/重采样须保持 `system`、material 和 source 的交换性，例如分层 residual permutation、wild/cluster bootstrap 或预注册的受限置换，不能裸置换 `y`。
- 任何根据 y 选择阈值、图 cutoff、类别合并、最佳网络表示的过程都必须嵌套在置换/交叉验证中；更好的做法是完全禁止。
- 报告 effect size、bootstrap CI、类别支持数、冻结测度下的稳定质量和缺失率；“不显著”也应保留，避免形成新的文献选择偏差。

### 8.5 建议的负对照

- 随机置换 Na/host 环境颜色但保持图和颜色频数，测试“空间排列”是否真比“种类数”多信息。
- 保持 degree/gain 分布的图随机化，测试环/分块量是否只是在读取 degree。
- 保持 system 和样本数的分层 y 置换，检查体系混杂。
- 用组成/空间群/原胞大小等简单基线，要求新结构量展示增量信息而非只重复数据库容易量。
- 对 `G_occ` 与 `G_void/G_bvse` 标签随机错配，估计跨表示一致性偶然水平。

## 9. 文献启发地图：哪些是已有事实，哪些是本文提出的检验问题

以下专项核查只以正式发表的一手论文和期刊官方页面作为证据。`D/N/M/U?` 针对**精确定义**判级：底层物理机制已有发表证据，不等于本文重新组合的 CIF 离散分类已被直接验证。

| 文献方向                                                     | 已经建立的事实/方法                                          | 本文由此提出、但仍待 Na 数据检验的问题                       |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| [Li bcc 阴离子骨架设计](https://www.nature.com/articles/nmat4369) | 理想 bcc 阴离子骨架中的相邻四面体间隙可形成有利贯通；fcc/hcp 可能要求跨不同配位环境。这是理想化拓扑/近等能环境结论，不等同于完整晶体中的单一 Wyckoff orbit。 | 同/异类环境切换的**最小次数、方向差异、循环语法**是否提供额外信息（CE04–CE08）？ |
| [Na 高配位面共享设计原则](https://www.nature.com/articles/s41467-023-43436-3) | Na 偏好高配位、面共享连接；使用 percolation radius 和局域 CN 筛选并实验验证氯化物。 | 关键窗口是否简并、串联/并联？有利位点是否属于同一 winding block？（PG07、VN02、VN17） |
| [Sc-NZSP 局域 Na 快交换](https://www.nature.com/articles/s41598-018-30478-7) | 单材料 NMR+电导研究区分 3 个晶体学不等价、部分占位 Na sites，并把 transition-site 局域快跳与长程传输联系起来。 | “多环境存在”升级成“某类环境切换对各 winding direction 是否必要”的跨材料删边检验（S8/S9、CE04–CE08）是否仍有信息？ |
| [Li corner-sharing framework](https://www.nature.com/articles/s41563-022-01222-4) | Li 氧化物中 corner-sharing host framework 与快速迁移有关，并经筛选/实验验证。 | 多面体连接的**顺序、异种 mixing、稀有 motif 必要性**是否比全局“含不含共边/共面”更有信息（HF13–HF15、HF23）？ |
| [Li ultraphosphate](https://doi.org/10.1021/jacs.1c07874)    | 已按 terminal/internal/branching PO4、链、层和环描述缩合拓扑，并对 Li3P5O14 测量电导。 | 同一标准化缩合组件谱在 Na 跨家族中是否仍有体系内变异，以及它与 Na/void winding 的关系是否有信息（HF22、CE16）？ |
| [Na 12,670 结构无监督筛选](https://www.nature.com/articles/s41524-024-01392-6) | 使用多种原子/简化表示和结构属性筛选；事后分析支持 ion channels、通道尺寸及较弱 Na–邻近原子作用的重要性，但没有主张一个单一普适描述符，且实验电导记录仅 34 条。 | 哪些离散拓扑量在 system 内仍有变异？无标签结构筛选与小样本 sigma 审计应怎样分开？ |
| [CAVD](https://pmc.ncbi.nlm.nih.gov/articles/PMC7244509/) 与 [Zeo++](https://doi.org/10.1016/j.micromeso.2011.08.020) | 可从静态结构算法化构造 periodic void/interstitial network、通道和几何瓶颈；结果仍依赖原子/离子半径、探针或可达阈值及结构质量。 | 不只取一个半径，而取完整**秩激活词、critical-window orbit、merge tree 和 pocket 共存型**是否更有用（VN02–VN17）？ |
| [通道 homogeneity](https://doi.org/10.1002/aenm.202101437)、[Li-argyrodite 笼间连通](https://doi.org/10.1021/acs.chemmater.3c01525) 与 [Na 大瓶颈原则](https://doi.org/10.1038/s41467-023-43436-3) | 均匀 transport gap、笼内/跨笼几何以及 Na percolation radius 已被用于筛选或与迁移/电导联系；因此“均匀通道”和“大瓶颈”都不是本文首创。 | 沿 canonical winding path 的净空剖面能否稳定分成 `低调制/单主瓶颈笼—窗/多非等价瓶颈`，且在控制体系后仍有信息（VN14）？精确三分类本轮未见直接先例。 |
| [弯曲 Li 路径个案](https://doi.org/10.1021/acs.chemmater.5b04608) 与 [helical pseudo-2D 路径个案](https://doi.org/10.1021/acs.inorgchem.3c01028) | 已有单材料把弯曲或螺旋路径与扩散/电导放在同一研究中；CAVD/Zeo++ 可提供中心线提取构件。但个案也表明直/弯本身没有跨体系单调的有利方向。 | `直/平面曲折/螺旋/3D弯曲/mixed` 的统一 CIF 分类是否有机制信息（VN20）？本轮未见跨 SSE 直接检验，故只放探索层。 |
| [Li2+xS1−xNx 瓶颈化学](https://doi.org/10.1021/jacs.5c02784) 与 [Li3OCl1−xBrx 局部通道化学](https://doi.org/10.1021/acs.chemmater.5b00988) | `SS/NS/NN`、`SSS/NSS/NNS/NNN` 等局部瓶颈组成及 Cl-rich/Br-rich 路径环境已与局部跳跃势垒、渗流和宏观电导联系；“瓶颈化学重要”已有强证据。 | 把 critical rim 的循环词模去旋转/反向后，按 run 结构分 `single/alternating/block/mixed` 是否增加信息（VN10）？精确循环次序检验未见先例，且平均无序 CIF 通常不能确定该标签。 |
| [周期迁移图](https://www.nature.com/articles/s41524-023-01051-2) | 带平移的迁移图能识别宏观 winding paths，并可加能垒权重。     | 在无需 DFT 权重时，gain graph 的 cut、格基、block、core、Cartesian factorization 能否作为静态组织量（PG03–PG09）？ |
| [JACS 2025 persistent topology](https://doi.org/10.1021/jacs.5c04828) | Li-only/Li-free simplicial complexes、cycle density 和 connectivity distance 已用于 Li conductor discovery。 | 哪些**非 Betti 数**的周期不变量，或 local-cycle/winding-cycle 分拆，能避免复制已有 cycle density（PG05、PG10）？ |
| [2026 path entropy](https://www.nature.com/articles/s41467-026-71316-z)、[周期迁移图](https://doi.org/10.1038/s41524-023-01051-2) 与 [周期 vertex-connectivity](https://doi.org/10.1107/S2053273316003867) | 动态 pathway multiplicity 已与 Li 迁移相关；带整数胞移的周期图和周期连通度构件也已成熟。 | 在冻结的 translation-labelled graph 和作用群上，删除整条 edge/vertex orbit 后重算 winding-rank 损失、最小保秩 orbit cut 或 orbit-disjoint 方向 packing，能否成为静态路径冗余先验（PG02/PG04/VN16）？精确组合本轮未见直接电导检验，且只能称“对称族脆弱性”，不能冒充单缺陷耐受。 |
| [晶体 net topology / ToposPro](https://doi.org/10.1021/cg500498k) | coordination sequence、point/vertex symbol、natural tiling、transitivity 是成熟晶体分类工具。 | 这些量或其关系型组合是否在 Na-SSE 中具有体系内变化和关联（PG16–PG22、HF01–HF08）？ |
| [CIF 无序分类](https://journals.iucr.org/j/issues/2025/03/00/jur5002/) | 可从平均 CIF 把轨道分类为 O/S/P/V 及混合类型，并计算无序熵。 | 无序是否位于 winding backbone、critical throat 或跨子晶格 incidence 核心（DO05–DO12），而不只是“无序多少”？ |
| [晶体结构信息量 crystIT](https://journals.iucr.org/j/issues/2021/01/00/oc5005/index.html) | 结构复杂度和含部分占位的 configurational entropy 可从 CIF 批处理。 | Na/host/backbone 的复杂度**关系**是否比总 bits/atom 更有信息（SI02–SI05）？ |
| [周期 rigid-unit-mode 理论](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/) | 可由理想周期刚性框架定义 phase-periodic flex 和 RUM spectrum。 | Γ 点理想化 flex 是否一阶打开关键窗口、柔性核心是否位于瓶颈附近（HF18–HF20、CE23）？只作静态代理，不把倒空间波矢直接解释成实空间传输方向，也不冒充真实声子。 |
| [Bond Valence Model](https://pubs.acs.org/doi/10.1021/cr900053k)、[energy-scaled BV landscape](https://doi.org/10.1039/B901753D) 与 [BVPA](https://doi.org/10.1021/acs.chemmater.0c03893) | BVS mismatch 本身不是严格能量；经过能量标度/短程与静电项构造的 BVSE/BVPA 已可定位候选位点、通道并给静态势垒代理。 | 子水平集的秩激活、critical-barrier orbit 简并、几何—能量排序冲突是否比单一 barrier 更有信息（EL07–EL18）？ |

## 10. 推荐的论文主张边界

可以安全地写：

> We pre-registered a small confirmatory set of chemically actionable or selection-ready, CIF-reproducible structural classifications, while retaining the broader mechanistic universe as FDR-controlled exploratory analyses. For selected exact constructions, no direct Li/Na cross-material conductivity test was found in the searched literature as of 17 August 2026.

不应写：

> These descriptors have never been studied, or the static Na graph is the true migration network.

若某个候选最终显著，下一步仍需做：

1. 跨 `G_occ/G_void/G_bvse` 表示复现；
2. 体系内和 leave-one-system-out 复现；
3. 参数平台复现；
4. 用少量代表材料的 BVSE/NEB/AIMD 或实验扩散路径校准物理解释；
5. 独立数据集确认，而不是在同一数据集继续调定义。

## 11. 最终建议

统计执行采用严格 design-rule 单轨：8 条候选只是 Gate 2/3 前的损耗池，最终主检验上限为 5–6 条。没有通过条件式化学可操作性、体系内类别普查、参数/双构造一致性或实际数据可计算性的候选，一律降入 FDR 探索层；这不是对候选科学质量的否定，而是样本量约束下对确认性功效和论文主张边界的保护。

值得扩大的范围远不止 S1–S12。最有潜力的增量不在继续收集“一个全局平均几何量”，而在三类关系：

1. **方向怎样耦合：** 独立方向是否共享同一 block、同一 critical orbit、同一 k-core，还是可 Cartesian 分解。
2. **环境怎样被迫切换：** 长程路径是否必须改变 CN/配位几何/化学颜色，稀有环境是否是必经角色。
3. **不同结构表示是否一致：** 报告占据位、几何空隙、BVSE 能量、宿主柔性和无序轨道是否指向同一条拓扑故事。

这三条比“某个描述符在 Li 中成名后移植到 Na”更适合产生新知识。即使最后大部分候选与电导无关，预注册的阴性结果也会回答一个重要问题：静态 CIF 的哪些结构层级根本没有跨体系预测力，哪些只在特定化学体系内有效。

---

## 参考文献与方法入口（精选）

1. Wang et al., *Nature Materials* (2015), [Design principles for solid-state lithium superionic conductors](https://www.nature.com/articles/nmat4369).
2. Zhang et al., *Nature Communications* (2023), [Design principles for sodium superionic conductors](https://www.nature.com/articles/s41467-023-43436-3).
3. Jun et al., *Nature Materials* (2022), [Lithium superionic conductors with corner-sharing frameworks](https://www.nature.com/articles/s41563-022-01222-4).
4. Shen et al., *npj Computational Materials* (2023), [Topological graph-based analysis of solid-state ion migration](https://www.nature.com/articles/s41524-023-01051-2).
5. Chen et al., *JACS* (2025), [Superionic Ionic Conductor Discovery via Multiscale Topological Learning](https://doi.org/10.1021/jacs.5c04828).
6. Guan et al., *Nature Communications* (2026), [Path entropy-driven design of solid-state electrolytes](https://www.nature.com/articles/s41467-026-71316-z).
7. He et al., *Scientific Data* (2020), [CAVD, towards better characterization of void space for ionic transport analysis](https://www.nature.com/articles/s41597-020-0491-x).
8. Willems et al., *Microporous and Mesoporous Materials* (2012), [Algorithms and tools for high-throughput geometry-based analysis of crystalline porous materials](https://doi.org/10.1016/j.micromeso.2011.08.020).
9. Gao et al., *npj Computational Materials* (2020), [Determining dimensionalities and multiplicities of crystal nets](https://www.nature.com/articles/s41524-020-00409-0).
10. Blatov et al., *Crystal Growth & Design* (2014), [Applied Topological Analysis of Crystal Structures with ToposPro](https://doi.org/10.1021/cg500498k).
11. Delgado-Friedrichs, O'Keeffe & Yaghi, *PCCP* (2007), [Taxonomy of periodic nets and the design of materials](https://doi.org/10.1039/B615006C).
12. Delgado-Friedrichs & O'Keeffe, *Acta Crystallographica A* (2003), [Identification of and symmetry computation for crystal nets](https://doi.org/10.1107/S0108767303012017).
13. Kaußler & Kieslich, *Journal of Applied Crystallography* (2021), [crystIT: complexity and configurational entropy of crystal structures via information theory](https://doi.org/10.1107/S1600576720016386).
14. Antypov et al., *Journal of Applied Crystallography* (2025), [Classification and statistical analysis of structural disorder](https://doi.org/10.1107/S1600576725003000).
15. Zimmermann & Jain, *RSC Advances* (2020), [Local structure order parameters and site fingerprints for quantification of coordination environment and crystal structure similarity](https://pubs.rsc.org/en/content/articlehtml/2020/ra/c9ra07755c).
16. Waroquiers et al., *Acta Crystallographica B* (2020), [ChemEnv: a fast and robust coordination environment identification tool](https://doi.org/10.1107/S2052520620007994).
17. Power, *Philosophical Transactions A* (2014), [Polynomials for crystal frameworks and the rigid unit mode spectrum](https://pmc.ncbi.nlm.nih.gov/articles/PMC3871295/).
18. Fletcher et al., *Acta Crystallographica B* (2015), [Intrinsic flexibility of porous materials; theory, modelling and the flexibility window of the EMT zeolite framework](https://doi.org/10.1107/S2052520615018739).
19. Brown, *Chemical Reviews* (2009), [Recent Developments in the Methods and Applications of the Bond Valence Model](https://doi.org/10.1021/cr900053k).
20. Eon, *Acta Crystallographica A* (2016), [Vertex-connectivity in periodic graphs and underlying nets of crystal structures](https://doi.org/10.1107/S2053273316003867).
21. Park et al., *npj Computational Materials* (2024), [Computational screening of sodium solid electrolytes through unsupervised learning](https://doi.org/10.1038/s41524-024-01392-6).
22. Blatov et al., *Acta Crystallographica A* (2007), [Three-periodic nets and tilings: Natural tilings for nets](https://doi.org/10.1107/S0108767307038287).
23. Blatova & Blatov, *Acta Crystallographica A* (2024), [Hierarchical topological analysis of crystal structures: the skeletal net concept](https://doi.org/10.1107/S2053273323008975).
24. Han et al., *JACS* (2021), [Extended Condensed Ultraphosphate Frameworks with Monovalent Ions Combine Lithium Mobility with High Computed Electrochemical Stability](https://doi.org/10.1021/jacs.1c07874).
25. Adams & Rao, *PCCP* (2009), [Transport pathways for mobile ions in disordered solids from the analysis of energy-scaled bond-valence mismatch landscapes](https://doi.org/10.1039/B901753D).
26. Wong et al., *Chemistry of Materials* (2021), [Bond Valence Pathway Analyzer—An Automatic Rapid Screening Tool for Fast Ion Conductors within softBV](https://doi.org/10.1021/acs.chemmater.0c03893).
27. Nespolo, *Journal of Applied Crystallography* (2023), [Molecular versus structural chirality](https://doi.org/10.1107/S1600576722011220).
28. Lunghammer et al., *Scientific Reports* (2018), [Fast Na ion transport triggered by rapid ion exchange on local length scales](https://doi.org/10.1038/s41598-018-30478-7).
29. Xiao et al., *Advanced Energy Materials* (2021), [transport-path homogeneity screening](https://doi.org/10.1002/aenm.202101437).
30. Gautam et al., *Chemistry of Materials* (2023), [cage size, inter-cage distance and Li-argyrodite transport](https://doi.org/10.1021/acs.chemmater.3c01525).
31. Baktash et al., *npj Computational Materials* (2020), [disorder-enabled inter-cage transport in Li argyrodites](https://doi.org/10.1038/s41524-020-00432-1).
32. Gomez et al., *Journal of Chemical Physics* (2021), [periodic long-range proton migration pathways](https://doi.org/10.1063/5.0039103).
33. Plass et al., *Inorganic Chemistry* (2023), [helical pseudo-2D Li pathways in Li-disordered bismuth thiophosphate](https://doi.org/10.1021/acs.inorgchem.3c01028).
34. Wohlmuth et al., *Chemistry of Materials* (2016), [curved Li migration pathways in gamma-LiAlO2](https://doi.org/10.1021/acs.chemmater.5b04608).
35. Zeng et al., *Journal of the American Chemical Society* (2025), [Disorder-Mediated Ionic Conductivity in Irreducible Solid Electrolytes](https://doi.org/10.1021/jacs.5c02784).
36. Deng et al., *Chemistry of Materials* (2015), [local halide channel chemistry in Li3OCl1−xBrx](https://doi.org/10.1021/acs.chemmater.5b00988).
参考了。更准确地说：这些候选是从已发表的一手论文中抽取物理机制和计算构件，再将其重组为尚待你验证的 CIF 离散分类量；不能表述成“文献已经证明这些新分类与 Na 电导率相关”。

截至 2026-08-17 的专项核查结果如下，未依赖预印本：

| 新候选 | 已发表文献基础 | 精确分类是否已有直接验证 |
|---|---|---|
| 周期路径冗余 | 动态“路径多样性/路径熵”已与 Li 电导联系；带跨胞平移标签的周期迁移图也已成熟 | **未找到**删除整条边/位点对称轨道后，以 winding-rank 损失或最小 orbit cut 分类并检验电导的工作 |
| 笼—窗口净空剖面 | Na 的贯通半径、大瓶颈、高配位面共享通道已有直接验证；路径均匀性也已有 Li 筛选先例 | **精确三分类未找到**；但“均匀通道”和“大瓶颈有利”不能声称新 |
| 通道中心线形态 | 螺旋、弯曲、直线/曲折路径都有单材料机制案例；Voronoi/CAVD 提取方法成熟 | **未找到**统一的 `直线/平面曲折/螺旋/三维弯曲` 跨材料电导检验；这是四项中依据最弱的 |
| 关键窗口 rim 化学 | 局部瓶颈的 S/N、Cl/Br 化学组成影响跳跃势垒和宏观电导已有直接证据 | **未找到**把 rim 循环顺序分类为 `单一/交替/分块/混合` 并系统检验电导的工作 |

关键文献包括：

- [Guan et al., Path entropy-driven design of solid-state electrolytes, Nature Communications, 2026](https://doi.org/10.1038/s41467-026-71316-z)：动力学路径多样性与 Li 输运。
- [Shen et al., Topological graph-based analysis of solid-state ion migration, npj Computational Materials, 2023](https://doi.org/10.1038/s41524-023-01051-2)：带胞移标签的周期迁移图。
- [Wang et al., Design principles for sodium superionic conductors, Nature Communications, 2023](https://doi.org/10.1038/s41467-023-43436-3)：Na 大瓶颈、面共享高配位通道及实验验证。
- [Xiao et al., Advanced Energy Materials, 2021](https://doi.org/10.1002/aenm.202101437)：Li 迁移通道的 homogeneity 概念及 AIMD 筛选。
- [Zeng et al., Disorder-Mediated Ionic Conductivity in Irreducible Solid Electrolytes, JACS, 2025](https://doi.org/10.1021/jacs.5c02784)：直接区分 SSS/NSS/NNS/NNN 等瓶颈化学环境，并联系局部跳跃势垒和宏观电导。
- [He et al., CAVD, Scientific Data, 2020](https://doi.org/10.1038/s41597-020-0491-x)：从 CIF 提取间隙、通道和瓶颈的成熟方法。

因此，最严谨的表述应是：

> 这些是“有已发表机制和方法依据、但精确离散定义尚未被系统检验”的候选量。

对候选池也需要稍作区别：

- 路径冗余：可保留为较强的 `selection-ready` 候选。
- 笼—窗口：可保留，但应改名为“净空/收窄剖面”；创新点是完整剖面分类，而不是“大瓶颈”本身。
- rim 化学：有很强机制依据，但只适合完全有序且窗口确有化学变化的 CIF。
- 中心线形态：目前更适合探索层，不能预设直或弯哪一种更有利。

这四项仍然都必须通过你规定的体系内类别普查、双构造一致率和参数稳定性检验，才能决定是否进入最终 5–6 条主检验。


# Na 固态电解质晶体学信息文件（CIF）结构分类量扩展分析

## 1. 研究目的与使用方式

本研究从晶体结构中提取一组可审计的分类量，用于比较不同 Na 固态电解质中可能与钠离子长程传输有关的结构现象。在导入室温电导率前，先冻结描述符、计算参数、候选保留规则和统计方案，以避免根据结果反向调整结构定义或筛选阈值，把偶然相关写成机制结论。

M01–M10 是预留淘汰余量的主候选池，X11–X15 是探索候选池。每个主候选仍须独立通过筛选，最终仅有 5–6 项进入预先指定的主检验；探索候选不占主检验名额，即使出现统计信号，也只作为预先注册的探索性结果报告。M01 是已有 Na 体系正对照，不作为创新主张；其余项目只能称为待检验的跨体系 CIF 分类量。

本文将结构现象、可能作用、判断方法和结论限定分开叙述。结构上的贯通、净空或位点能连续性都是近似指标，不能直接等同于低迁移势垒、真实自由能或高电导率。后续统计只能检验关联是否稳定；物理验证只能校准关联的适用边界，不能把结构相关性表述为已证实的因果规律。

## 2. 基本概念与三级计算流程

晶体学信息文件（CIF）记录晶胞、原子位置、占位和对称性，是本研究的统一输入。每个结构先规范化为原胞表示，并保留部分占位、材料/文献来源和测量条件。输入不完整、定义域外、合理构造不一致或计算失败的情况均单独标记，避免以单一数值掩盖结构信息的不确定性。

配位数（CN）表示一个原子附近被认定为相邻原子的数目，用来描述钠位点的局域配位环境；高配位或低配位本身不预先代表好坏。沃罗诺伊空隙分析把去除 Na 后的宿主骨架划分为空隙网络，用于观察几何自由空间；通道净空是可通行空间尺度，通道颈部是最窄的关键位置，窗缘原子是围绕该位置的原子。键价位点能方法（BVSE）根据键价失配构造静态位点能景观，可比较能量起伏，但不是自由能计算。

周期贯通维数表示网络中彼此独立的长程延展方向；不同连通部分分别判断，不合并为一个结果 [R22]。对称等价组则是由晶体对称性联系起来的一整组位置或连接。空位缺陷是原应由 Na 占据的位置留空，间隙缺陷是 Na 进入常规位点之外的空间；两者都可能改变迁移网络，但单一静态构型不足以说明实际缺陷迁移。可接收空位是同时满足几何容纳、位点能和近邻排斥条件、可供钠离子迁入的候选空位。

计算按成本分为三级。一级全库初筛（L1）只使用 CIF、元素、晶格、几何和固定经验表，适合快速处理全库。二级结构复核（L2）不使用密度泛函理论（DFT），而以第二种局域环境定义、BVSE 或代表路径核对 L1 判断。三级物理验证（L3）仅针对小样本，可采用 DFT、爬山弹性带法（NEB，用于估算迁移势垒）、从头算分子动力学（AIMD）、声子或机器学习势动力学。若复核成本超出预设范围，项目转入 L3；表示冲突保留为结果的一部分。

## 3. 候选结构分类量

下表是本文唯一的 15 项总表。“可能影响”均为待检验的结构解释；“材料调控”是后续可尝试的方向，不是已证实的设计结论。

| 编号 | 中文名称与核心问题 | 为什么可能影响钠离子传输 | 一级初筛如何判断 | 后续如何复核 | 可尝试的材料调控 | 已有证据与结论边界 |
|---|---|---|---|---|---|---|
| M01 | 相邻配位多面体以一个面相接（面共享）的高配位钠位点是否长程贯通？ | 相似位点连续排列可能形成迁移连续段。 | 构建相邻配位多面体以一个面相接（面共享）的高配位钠位点网络，并判断其是否沿一个或多个方向长程贯通。 | 用第二种 CN 定义复核。 | 保持连续高配位段。 | Na 正对照 [R1]，关联仍待复验。 |
| M02 | 多方向迁移通道的净空开启阈值：何时开启新方向？ | 狭窄窗口可能限制新增方向。 | 比较不同净空下的贯通方向。 | 用 BVSE 连通性核对。 | 改善最后开启方向的窗口。 | 几何贯通不等于低势垒 [R2] [R3]。 |
| M03 | 长程迁移中的局域环境切换必要性：是否需要切换？ | 环境转换可能造成失配，也可能中性。 | 比较保留或去除转换连接后的贯通性。 | 检查代表路径的局域环境。 | 降低必要转换位的失配。 | 只判断必要性，不预设其有害 [R1] [R4]。 |
| M04 | 关键迁移窗口两侧的多面体连接方式：两侧如何连接？ | 局部连接方式可能改变窗口约束。 | 分类窗口两侧多面体的连接。 | 比较代表路径的连接序列。 | 调节关键路径的连接方式。 | 锂（Li）体系有先例，Na 中的作用仍待检验 [R5]。 |
| M05 | 首次贯通通道颈部的唯一性与可替代性：是否可替代？ | 替代连接少时网络对局部变化更敏感。 | 判断首次贯通窗口是否可替代。 | 改变构图条件后复核。 | 减少对单一窗口的依赖。 | 只报告该窗口对贯通是否必要、单独是否充分，以及替代路径需要增加多少净空；这些静态结果不表示动态并联路径数。 |
| M06 | 钠迁移网络与宿主骨架的维度关系：维度是否失配？ | 两类网络的延展方向可能不一致。 | 比较两类网络的贯通维数。 | 用第二种成键规则复核。 | 保留迁移网络的多方向连通。 | 失配不预设有利 [R6]。 |
| M07 | 迁移通道的宽窄变化类型：通道如何变宽窄？ | 连续收窄可能累积几何限制。 | 沿代表通道比较各位置净空，区分近似均匀、单一狭窄处、连续收窄、宽窄交替或歧义。 | 检查代表路径的净空变化。 | 降低主通道颈部或减小起伏。 | 净空变化不足以说明自由能 [R7] [R8]。 |
| M08 | 迁移网络的备用连接能力：是否保留替代连接？ | 替代连接可反映静态冗余。 | 去除一个对称等价组后比较贯通性。 | 整组删除对称等价钠位点后复核。 | 增加不共用关键连接的通路。 | 不代表动态路径熵或缺陷容错 [R9]。 |
| M09 | 低起伏键价能量网络的贯通性：低起伏区域能否贯通？ | 连续低位点能可能提示较平缓的静态景观。 | 先在候选钠位点和关键连接位置估算静态位点能及起伏。 | 检查低起伏区域能否贯通。 | 提高关键位置的位点能连续性。 | BVSE 不是自由能 [R10] [R11]。 |
| M10 | 关键迁移窗口的阴离子组成与排列：窗缘如何排列？ | 局域阴离子环境可能改变窗口条件。 | 记录窗缘组成和净空。 | 比较唯一窗口的排列。 | 调节窗缘组成和局域软度。 | 精确排列规则仍待检验 [R12] [R13]。 |
| X11 | 孤立阴离子形成的钠离子笼贯通性：能否形成贯通笼？ | 局域空隙可能形成独立迁移单元。 | 识别孤立阴离子与笼的贯通性。 | 构建完整笼网络。 | 探索定向构建孤立阴离子笼。 | Na 跨体系结论仅作探索 [R14]。 |
| X12 | 刚性结构单元的转动开窗倾向：转动能否开窗？ | 结构单元转动可能改变局部开口。 | 比较转动前后的窗口变化。 | 只统计从 CIF 初始取向连续、无原子碰撞可达的状态；无法确认连通时记为未解决。 | 选择可能协助开窗的单元。 | 静态结构不足以证明桨轮机制 [R15] [R16] [R17]。 |
| X13 | 宿主骨架的协同开窗能力：能否协同开窗？ | 协同微动可能改变窗口开口。 | 将相连多面体视作彼此约束的结构单元，检查是否存在可同时放大多个窗口的微小协同位移。 | 用刚性几何模型复核。 | 引入可能协同开窗的连接。 | 这是几何近似，不是声子计算 [R6] [R18]。 |
| X14 | 钠填充、离子排斥与可接收空位的平衡：可接收空位是否保持平衡？ | 填充、排斥和可供钠离子迁入的候选空位可能呈非单调关系。 | 比较不同填充下同时满足几何容纳、位点能和近邻排斥条件的可接收空位。 | 用 BVSE 估计的可接收位点范围和近邻排斥条件复核。 | 寻找填充与可接收空位的平衡。 | 可直接对应合成变量的结果用于调控；需数据库计算才能区分材料的结果用于筛选；其余结果仅解释机理 [R19] [R20]。 |
| X15 | 空位或间隙缺陷开启新迁移方向的能力：缺陷能否开辟新方向？ | 缺陷可能改变可连通方向。 | 记录候选缺陷位。 | 在 L3 检查缺陷迁移。 | 将经验证缺陷位作为掺杂方向。 | 单粒子删位不代表缺陷迁移 [R21]。 |

M01–M10 有 L1 结果并不表示自动入选。若 L2 未得到稳定标签，结果保留为 L1 近似指标或转入 L3；X11–X15 维持探索定位，X15 的完整验证留在 L3。

## 4. 四道解盲前筛选关与候选淘汰流程

### 第一关：这个分类量的定义和实现是否固定且可重复？

判定方法是先固定分类对象和主要参数，再检查原点平移、原子排序和等价晶胞变换后标签是否一致。相互独立的连通部分分别判断贯通维数，同一阈值下出现的连接按同一事件处理。重复计算和小型已知结构的核对用于确认实现稳定性。

### 第二关：合理的结构构造变化后，结论是否仍稳定？

判定方法是在预先列出的对称容差、半径表、成键规则和探针尺度变化下，比较标签平台、缺失或歧义比例及不同构造的一致性。本关不看电导率，也不以电导率选择阈值。没有稳定平台、存在表示冲突或材料来源质量不足的项目不得进入主候选严格池。

### 第三关：在不知道电导率时，这个分类量是否可执行且有足够样本支持？

判定方法是在不读取响应变量的条件下，按材料体系和来源层统计类别支持、稀有类别、共线性、CIF 完整性及 L1/L2 成本。每个待比较类别均需达到预先指定的体系内支持数；支持不足的类别合并为预定的“不可判定”类别或转为探索。L2 的候选选择和成本受限时的抽样均在不看响应变量的条件下预先确定，统计解释范围限于实际纳入的合格总体。

### 第四关：解盲前，主检验方案是否已经锁定？

判定方法是在读取任何室温电导率前，锁定 5–6 项 M 项的预先指定主检验、协变量、排除规则、多重比较方案、代码和结构清单。效果方向、显著性或图形不再用于改变机制、阈值、样本或主次终点；后续改动另作探索性分析。描述符定义和类别边界在不含响应变量的 CIF 上全局冻结，主检验与交叉验证均沿用该定义。

前三关结束且尚未读取电导率时，必须冻结并发布候选淘汰流程表，逐项展示 M01–M10 的输入数、各筛选关的排除或降级数及理由、各体系内类别支持数、存在歧义或未解决的比例，以及预计 L1/L2 成本。表格不能只留下最终通过者。

| 候选池 | 输入数 | 第一关排除/降级及理由 | 第二关排除/降级及理由 | 第三关排除/降级及理由 | 各体系内类别支持 | 歧义/未解决比例 | 预计 L1/L2 成本 | 最终去向 |
|---|---:|---|---|---|---|---|---|---|
| M01–M10（逐项填写） | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 主检验候选、降为 L3 或不纳入 |
| X11–X15（逐项填写） | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 待运行 | 仅探索或 L3 |

## 5. 统计、机器学习与物理验证的报告规则

统计观测单位是“确定组成、相或结构、测量条件和来源”的组合，不是一条 CIF，也不是同一材料的重复报道。室温电导率采用预先统一口径，并记录温度窗、电极与压实条件、相纯度和不确定度，不能把这些差异静默吸收到结构标签中。

每项预先指定主检验至少控制材料体系，例如钠超离子导体型结构（NASICON）、硫化物和卤化物，以及材料/文献来源之间不可拆分的依赖关系。每项检验报告效应量、区间、类别支持、稳定性、缺失率和负结果。入选的 5–6 项 M 项统一校正多重比较；X11–X15 的探索检验控制错误发现率，并以探索性措辞报告。

同一机制的几何图、BVSE 图、第二种 CN 定义或第二种成键规则只用于可重复性核查，不构成独立发现，也不增加主假设次数。机器学习只作为第二层证据：先完成可解释统计，再评价增量预测、校准程度和失效模式。

机器学习按材料—文献来源二部图的连通分量分组：一条观测将其材料和文献来源相连，同一连通分量整体进入训练集或测试集。因此，同一材料的不同 CIF 或不同来源不应分散到两者之间。预测模型的决策阈值、缺失处理、标准化、特征选择和超参数均在训练数据内部学习；全数据性能不足以选择表示或机制。若独立分组过少，交叉验证和体系留出结果仅作探索性压力测试。

物理验证从每个稳定类别中选择代表结构和反例，优先用 L2 的 BVSE 或刚性结果检查静态近似指标是否一致。只有预设的小样本 L3 才可使用 NEB、AIMD、声子或机器学习势动力学检查势垒、相关运动、软模和温度效应。L3 的肯定或否定结果只能校准机制边界，不能回溯改变已经冻结的主检验定义。

## 6. 执行优先级与主张边界

先建立 CIF 规范化、局域环境、空隙网络和周期贯通维数的基础计算，并完成小型周期网络核查；随后优先运行 M01、M02、M03、M05、M06、M08、M10 的 L1，再处理 M04、M07、M09 的受限复核。X11–X14 只有在 L1 初步分流达到第三关样本支持要求后才进入 L2。

M03 的否定结果同样有信息：局域环境切换可以是中性、必要或可替代，不能预先称为惩罚。M05 只报告窗口对贯通是否必要、单独是否充分，以及替代路径需要增加多少净空；这些静态结果不表示动态并联路径数。M08 是周期对称等价组的静态删除敏感性，解释范围不包括动态路径熵、真实缺陷浓度或失效寿命。M09 的计算参数在文末计算附录中固定并说明；该结果不足以说明“自由能平台”或“真实势垒”。

X12 称为“转动开窗倾向”，并同时承认关于桨轮机制普适性的支持和质疑文献 [R15] [R16] [R17]。X13 是刚性或几何协同开口的近似指标，不能称为声子或软模计算。X14 应报告区间和非单调关系，Na 含量、空位数或高能位占用都不宜孤立解释为越大越好。X15 在 L3 构型图、缺陷化学和动力学边界均明确后，才进入掺杂或缺陷设计的讨论。

本文所谓“未见同一定义先例”仅表示有限文献审计范围内的观察，不是世界范围的绝对新颖性声明。以下 22 篇为正文 [R1]–[R22] 实际引用的一手方法或机制来源；新增文献时应同步更新正文引用与本清单。

[R1] Wang et al.（2023），中文译题：钠超离子导体的设计原则（[Design principles for sodium superionic conductors](https://doi.org/10.1038/s41467-023-43436-3)）。
[R2] He et al.（2020），中文译题：CAVD：迈向用于离子输运分析的更优空隙空间表征（[CAVD, towards better characterization of void space for ionic transport analysis](https://doi.org/10.1038/s41597-020-0491-x)）。
[R3] Shen et al.（2023），中文译题：固态离子迁移的拓扑图分析（[Topological graph-based analysis of solid-state ion migration](https://doi.org/10.1038/s41524-023-01051-2)）。
[R4] Deng et al.（2018），中文译题：钪取代钠超离子导体型固态电解质的晶体结构、局域原子环境与离子扩散机制（[Crystal Structures, Local Atomic Environments, and Ion Diffusion Mechanisms of Scandium-Substituted Sodium Superionic Conductor (NASICON) Solid Electrolytes](https://doi.org/10.1021/acs.chemmater.7b05237)）。
[R5] Jun et al.（2022），中文译题：具有共顶连接骨架的锂超离子导体（[Lithium superionic conductors with corner-sharing frameworks](https://doi.org/10.1038/s41563-022-01222-4)）。
[R6] Gupta et al.（2021），中文译题：超离子 Na3PS4 中的快速 Na 扩散与非谐声子动力学（[Fast Na diffusion and anharmonic phonon dynamics in superionic Na3PS4](https://doi.org/10.1039/D1EE01509E)）。
[R7] Xiao et al.（2021），中文译题：受石榴石和钠超离子导体型结构启发的锂氧化物超离子导体（[Lithium Oxide Superionic Conductors Inspired by Garnet and NASICON Structures](https://doi.org/10.1002/aenm.202101437)）。
[R8] Pivarníková et al.（2025），中文译题：理解钠超离子导体型固态电解质中 Na+ 扩散的结构与机制，以及 Sc 和 Al/Y 取代效应（[Understanding the structure and mechanism of Na+ diffusion in NASICON solid-state electrolytes and the effect of Sc- and Al/Y-substitution](https://doi.org/10.1039/D5TA00826C)）。
[R9] Guan et al.（2026），中文译题：路径熵驱动的固态电解质设计（[Path entropy-driven design of solid-state electrolytes](https://doi.org/10.1038/s41467-026-71316-z)）。
[R10] Adams and Rao（2009），中文译题：由能量标度键价失配景观分析无序固体中移动离子的传输路径（[Transport pathways for mobile ions in disordered solids from the analysis of energy-scaled bond-valence mismatch landscapes](https://doi.org/10.1039/B901753D)）。
[R11] Zeng et al.（2022），中文译题：提升离子电导率的高熵机制（[High-entropy mechanism to boost ionic conductivity](https://doi.org/10.1126/science.abq1346)）。
[R12] Krauskopf et al.（2017），中文译题：晶格动力学对固态电解质 Na3PS4−xSex 中 Na+ 传输的影响（[Influence of Lattice Dynamics on Na+ Transport in the Solid Electrolyte Na3PS4−xSex](https://doi.org/10.1021/acs.chemmater.7b03474)）。
[R13] Landgraf et al.（2025），中文译题：不可约固态电解质中由无序介导的离子电导率（[Disorder-Mediated Ionic Conductivity in Irreducible Solid Electrolytes](https://doi.org/10.1021/jacs.5c02784)）。
[R14] Yang et al.（2025），中文译题：通过涉及孤立阴离子的结构特征发现的新型快离子导体（[New fast ion conductors discovered through the structural characteristic involving isolated anions](https://doi.org/10.1038/s41524-025-01559-9)）。
[R15] Zhang et al.（2019），中文译题：耦合阳离子—阴离子动力学增强室温超离子固态电解质中的阳离子迁移率（[Coupled Cation–Anion Dynamics Enhances Cation Mobility in Room-Temperature Superionic Solid-State Electrolytes](https://doi.org/10.1021/jacs.9b09343)）。
[R16] Li et al.（2025），中文译题：用于固态电池的桨轮机制驱动钠超离子氯化物电解质（[A sodium superionic chloride electrolyte driven by paddle wheel mechanism for solid state batteries](https://doi.org/10.1038/s41467-025-61738-6)）。
[R17] Jun et al.（2024），中文译题：超离子导体中不存在桨轮效应（[The nonexistence of a paddlewheel effect in superionic conductors](https://doi.org/10.1073/pnas.2316493121)）。
[R18] Power（2014），中文译题：晶体骨架多项式与刚性单元模谱（[Polynomials for crystal frameworks and the rigid unit mode spectrum](https://doi.org/10.1098/rsta.2012.0030)）。
[R19] Zhang et al.（2019），中文译题：相关迁移引发钠超离子导体型固态电解质中更高的 Na+ 离子电导率（[Correlated Migration Invokes Higher Na+-Ion Conductivity in NaSICON-Type Solid Electrolytes](https://doi.org/10.1002/aenm.201902373)）。
[R20] Zou et al.（2020），中文译题：菱方钠超离子导体型结构中 Na+ 分布、协同迁移与扩散性质的关系（[Relationships Between Na+ Distribution, Concerted Migration, and Diffusion Properties in Rhombohedral NASICON](https://doi.org/10.1002/aenm.202001486)）。
[R21] Jalem et al.（2020），中文译题：W 和 Mo 掺杂 Na3SbS4 固态电解质中 Na+ 超离子传导机制的第一性原理计算研究（[First-Principles Calculation Study of Na+ Superionic Conduction Mechanism in W- and Mo-Doped Na3SbS4 Solid Electrolytes](https://doi.org/10.1021/acs.chemmater.0c02318)）。
[R22] Gao et al.（2020），中文译题：确定晶体网络的维数与重数（[Determining dimensionalities and multiplicities of crystal nets](https://doi.org/10.1038/s41524-020-00409-0)）。

## 7. 计算附录

本附录集中登记并规定计算对象、状态、参数和统计口径；生产参数须经第一道筛选关的盲态基准后另行冻结，它不改变正文对任何分类量的科学边界。

### A1. 程序输入、状态与共享计算

输入为晶体学信息文件（CIF），包括元素、原子坐标、晶格、占位、空间群信息和来源。结构哈希只由规范化晶格、元素/占位、分数坐标及冻结的排序和舍入规则生成；来源单独保存，不进入哈希，也不把哈希自身作为输入字段。

导入时不补造缺失结构字段；来源字段与结构哈希共同用于识别重复记录和后续按来源分组。

主状态按 `missing → not-applicable → ambiguous → unresolved → algorithm-failure` 的最早可达判定关取得，副原因另列：必要输入缺失为 `missing`；不适用于该结构为 `not-applicable`；合理构造不一致为 `ambiguous`；限额内无法判定为 `unresolved`；程序或数值失败为 `algorithm-failure`。异常可记为副原因，但不覆盖先前已经能够判定的主状态；状态不以数值替代，也不与阴性结果混同。

共享结果按层缓存：C0 为输入规范化和质量检查；C1 为邻居、配位数、宿主骨架和多面体；C2 为空隙、通道颈部、窗缘原子和跨胞连接；C3 为节点和连接的空间群对称等价组；C4 为单调阈值扫描、连通分量和整数标准形。

缓存标识至少包含结构哈希、对称性识别容差 `symprec`、半径/价态/成键表、探针球、图版本和全部容差，确保缓存复用不会隐去构图条件。

任一缓存字段不同即视为不同计算对象，必须重新计算或明确记录其复用依据。

### A2. 周期网络与贯通维数

为保留跨晶胞连通，原胞压缩图记为 `Q=(V,E,gamma)`：节点集为 `V`，连接集为 `E`，平移标签映射为 `gamma:E→Z^3`。商连接写为 `(i,j,t)`，其中 `t∈Z^3` 记录跨越的晶胞数，反向连接必须同时为 `(j,i,-t)`。

平行连接和跨胞自环均保留；图简化不得丢弃它们。将平移标签展开后得到无限周期图，并对每个无限展开连通分量 `alpha` 单独处理。

分量谱按照原胞图中可追溯的节点和连接等价组输出，使各维数判断可回查至 C2 和 C3。

下式回答“该分量有多少个彼此独立的长程方向”：在原胞商图中，取回到同一商节点、但提升到无限图后终点是起点某个平移像的游走；其标签净和生成平移子格 `L_alpha`。等价地，`L_alpha={t∈Z^3:T_t(alpha)=alpha}`，其中 `T_t` 是平移 `t`；不在无限图中要求真正回到同一顶点。定义 `D_alpha=rank_Z(L_alpha)`；`D_alpha=0/1/2/3` 依次为无长程贯通、一维、二维、三维贯通。

结构层报告分量谱及 `D_max=max_alpha D_alpha`。只有该表示中的全部在域周期分量都成功构造时才报精确 `D_max`；任一分量为 `unresolved` 或失败时，报告可证明的上下界，不能形成界时则报结构级 `unresolved`，绝不静默排除。例：同一分量中两商节点有三条连接 `(1,2,(0,0,0))`、`(1,2,(1,0,0))` 与 `(1,2,(0,1,0))`；胞内边分别与两条跨胞边构成回路，其标签生成 `e1`、`e2`，故该分量 `D_alpha=2`。若另一个断开分量使用不同节点（如胞内边 `(3,4,(0,0,0))` 与跨胞边 `(3,4,(0,0,1))`），它只给自己的 `e3` 与 `D_alpha=1`；只有错误地池化断开分量才会把 `e3` 同前一分量的 `e1/e2` 合成三维。候选图对象包括：`G_occ`（已占据 Na 位网络）、`G_void(r)`（半径为 `r` 的探针仍可通行的空隙网络）、`G_bvse(E)`（位点能不高于 `E` 的键价能网络）、`G_host`（去 Na 的宿主骨架网络）和 `G_col`（附带配位、几何、化学、能量标签的网络）。

整数计算使用厄米特标准形（HNF，用于给出平移子格基）和史密斯标准形（SNF，用于给出子格秩）；以整数晶格换基群 `GL(3,Z)` 检查结果在整数晶格换基下不变。

| 符号 | 中文含义 |
|---|---|
| `rank_Z` | 整数子格的秩，即独立整数平移方向数 |
| `sup` / `inf` | 分别为上确界/下确界，用于定义临界阈值 |
| `∪` / `\` | 分别为集合并/集合差 |
| `Z^3` | 三维整数平移向量集合 |

### A3. M01–M10 的计算定义

**M01。** `D_full` 是全部候选连接的最大贯通维数；`D_H` 仅保留高配位节点，`D_HF` 再仅保留高配位且面共享连接。三者均输出分量谱，而非只给一个全局数值。

高配位、两套 CN 定义和面共享判据均以 A5 登记表为准；相关生产值尚未冻结时，完整标签不运行并输出 `unresolved`，不由电导率或结果分布调整。

**M02。** 下式回答“多维贯通在多大几何尺度下仍保持”：`r_k=sup{r:D_max(G_void(r))>=k}`，`k=1,2,3`，即至少保持 `k` 维贯通的最大探针半径。同阈值连接整批加入，并记录“新启用的完整连接等价组→维度变化”的开启序列；`K` 是每个结构或分支可保留代表路径的上限。

若代表路径超过 `K`，保留规则必须按预先固定的对称不等价和排序条件截断。

**M03。** 删除连接不同配位环境的边，对原有各分量重算同环境子网络的 `D_same`，再与原维数 `D` 比较；各原分量仍彼此独立。

配位环境标签从 C1 的同一冻结邻居规则取得，不能在删除后重新选择使结果更有利的标签。

**M04。** 先按 A5 登记的窗口归属和唯一规则，把关键迁移窗口归属于相邻宿主多面体，再记录两多面体是共顶、共棱、面共享或无直接连接。按预定规则最多复核 `K` 条对称不等价代表路径；规则未冻结时输出 `unresolved`。

窗口无法唯一归属时，不强行指定连接类型，并依 A1 的状态规则报告。

**M05。** 此定义回答“首次目标贯通由哪些等价连接触发及维持”：对每个原分量从严到松扫描通道净空，令首次达到目标维度 `d` 的阈值批次为 `lambda*`，并令 `c*=clearance(lambda*)`。该批之前的图为 `G^-`，该批全部新连接为 `B*`，批后图为 `G*=G^-∪B*`。

对完整等价组 `O⊆B*`，若 `G^-∪O` 已使该分量达到 `d`，则纳入充分组集合 `S`；若 `G*\O` 不能使该分量达到 `d`，则纳入必要组集合 `N`。永久删除 `O` 后继续整批加入后续阈值连接；首次恢复目标维度的阈值净空记为 `c_rec(O)`，一旦恢复便有 `c_rec(O)≤c*`，且 `gap(O)=c*-c_rec(O)≥0`。扫描范围内未恢复时，`c_rec(O)` 未定义并记 `gap(O)=+∞`；若只扫描至有限下界 `c_min`，另报告右删失下界 `gap(O)≥c*-c_min`，不把它误作已知的 `c_rec(O)`。输出 `S`、`N`、`nS=|S|`、`nN=|N|` 与 `unique_essential=(nN=1)`；没有任何单组可判时明确输出该类别。

同一阈值批次的其他连接不得被任意拆散后作为背景，从而避免把并发开启误判为唯一因果连接。

**M06。** `D_mobile` 为移动网络贯通维数，`D_host` 为去 Na 宿主骨架贯通维数。宿主至少以强键原子图和刚性单元图两种构造复核；两者不一致即为 `ambiguous`。

输出同时保留两种宿主构造各自的分量谱，避免将不一致压缩成单一维数。

**M07。** `Di` 是最大内含球直径，`Df` 是按目标维度可长程通过的最大自由球直径，`Dif` 是承载该路径的限制路线上的最大内含球直径。为说明沿程收窄，`c(s)` 记录代表路径位置 `s` 的通道净空。

响应盲态的类别映射只使用代表路径净空曲线和 A5 登记的起伏、显著性、连续段阈值：按冻结的互斥判据输出近似均匀、单一显著狭窄处、连续收窄、宽窄交替或 `ambiguous`。映射固定后才定义何为显著局部最窄处、单调连续段和交替段；参数未冻结时完整分类不运行并输出 `unresolved`。代表路径只用于呈现限制路线，不被解释为实际离子在有限温度下的唯一动力学轨迹。

**M08。** 删除 C3 中每个连接对称等价组的全部副本，并对每个原分量重算贯通维数。节点对称等价组删除是复核方式：整组删除钠位点节点的全部对称等价副本；小图在预设上限内可求有界多组切断，但不外推为动态冗余。

删除操作总是作用于完整对称等价组，以免因原胞表示任意性制造伪冗余。

**M09。** 一级 `M09_sparse_proxy` 以冻结采样集合为对象：集合包含候选 Na/空隙节点及 C2 中的关键连接点，并以冻结规则在每条候选连接上取沿边采样点。对这些稀疏位点能和连接采样能，先取相对最低点 `e_min`；随后以冻结的边纳入规则形成稀疏图 `G_sparse(t)`，仅保留能量不高于 `e_min+t` 的采样节点及其满足规则的连接。这回答“低成本近似网络在相对最低点上方多大起伏时首次贯通”：`t_perc,sparse=inf{t≥0:D_max(G_sparse(t))>=d}`，并输出该阈值和代表贯通子图相对 `e_min` 的能量起伏。它是低成本稀疏近似，不是自由能。

二级完整网格首先回答“位点能不高于何值时首次贯通”：键价位点能（BVSE，提供静态能景观近似）的 `E_perc=inf{E:D_max(G_bvse(E))>=d}`，其中下确界是满足条件能量集合的最低界。再回答“在何种最窄能量带内能贯通”：对预注册能量域内的起点 `a` 与宽度 `w≥0`，`G_band(a,w)` 仅纳入能量在 `[a,a+w]` 的节点，以及端点和全部沿边采样值均在 `[a,a+w]` 的边；`E_flat-perc=inf{w≥0:exists a,D_max(G_band(a,w))>=d}`。两者均非自由能。

一级采样集合、沿边规则、目标维度 `d`、分类阈值以及二级网格、能量步长、插值和能量带边界均在 A5 的预设范围内冻结，不能以观测响应选取；任一相关参数未冻结时完整标签不运行并输出 `unresolved`。

**M10。** 一级记录可靠窗缘的元素多重集、固定表极化率和净空。仅在 A5 登记的关键窗口唯一规则成立、窗缘至少四原子且标签非单一时，按旋转/反向等价关系输出循环排列语法；规则未冻结时输出 `unresolved`。

不满足任一前提时只保留一级记录，不输出看似精确但不可比较的排列标签。

### A4. X11–X15 的计算定义

**X11。** 强键图识别孤立阴离子后，一级输出元素、间距和贯通维数；二级构建 Na/空隙笼及笼连接图。合理笼构造不一致时标记 `ambiguous`。

孤立性和笼连接均基于预定强键规则，不以材料类别作例外处理。

**X12。** 识别窗口旁刚性单元，在特殊正交群 `SO(3)`，即三维刚体旋转空间内有限采样；至多 `n_unit,max` 个共同转动单元在 `SO(3)^n` 中联合采样。CIF 初始取向是显式节点，且按同一无碰撞连续插值规则连边。取向图邻接规则预先登记，只统计从该初始节点可达的连通区域，不可达孤岛不计；超过 `n_unit,max`、取向节点数 `N_orientation` 或已验证边数 `N_edge` 的预注册上限，或连通性未能在限额内判定时为 `unresolved`。逐单元结果只能称为单元级近似。

有限采样只给出该固定采样分辨率下的倾向标签，不宣称覆盖所有连续取向。

**X13。** 此计算只检查固定晶格、Γ 点胞周期运动，不允许晶格应变；有限波矢和特征覆盖留给 L3。构造刚性约束矩阵 `R`，令 `T` 为允许的平凡运动子空间，并严格取 `U=ker R∩T^⊥`；固定晶格至少令三个整体平移属于 `T`，不允许的整体转动不纳入。若 `dim U=0`，单列“无非平凡 Γ 点一阶运动”，不套用下述最大化。

当 `dim U>0` 时取 `||u||2=1`。对 CIF 几何 `x0` 的每个窗口，冻结容差 `epsilon`，令一侧方向导数为 `a_j(u)=D^+c_j(x0;u)`。计算 `A_common=max_{u∈U}min_j a_j(u)`、`A_j=max_{u∈U}a_j(u)` 与 `B_j=max_{u∈U}|a_j(u)|`：所有 `B_j≤epsilon` 为全一阶中性；`A_common>epsilon` 为共同开窗；`A_common≤epsilon` 且所有 `A_j>epsilon` 为仅能取舍；其余且至少一项 `A_j≤epsilon` 为部分受阻；不能完成计算为未解决（`unresolved`）。它是固定晶格的几何近似，不是声子频率或软模。

**X14。** 在冻结的有限周期展开中，以二元变量 `x_i∈{0,1}` 表示候选位集合 `I` 的占位，接收位集合为 `I_rec⊆I`，冲突边为 `C`。若 `I_rec` 为空，输出 `not-applicable`。混合整数线性规划（MILP，用于枚举满足离散约束的占位）施加 `x_i+x_j≤1`（`(i,j)∈C`）、位点容量、固定占位、能量允许集，以及总 Na 数 `Σx_i=N_Na`；仅当组成/电荷给出预注册闭区间时才可用 `Nmin≤Σx_i≤Nmax`。部分占位无法映射至冻结分母超胞时为 `ambiguous`。

令满足全部约束的可行集为 `F`，并令 `q(x)=Σ_{i∈I_rec}(1-x_i)/|I_rec|`，则 `readiness=[q_min,q_max]=[min_F q(x),max_F q(x)]`。证明 `F` 为空时的 `no-feasible-assignment` 是数值结果标签，不是第六主状态；求解器超时或未能证明结论才是 `unresolved`，两者绝不混同。该区间不等同于热力学平衡空位浓度。

**X15。** 先以缺陷化学筛查允许的 Na 空位、间隙 Na 或间隙顶替迁移。三级在预定的小型有限周期展开 `characteristic cover`（特征覆盖，用于保留周期交换约束）上建立 Na–空位交换/间隙顶替构型图；超过展开上限时仅保留一级筛查。

三级构型图的结论仅限于该有限展开及已列缺陷类型，不外推为宏观扩散系数。

### A5. 参数平台、计算成本与稳定性

下表是版本化参数登记表，登记中还必须保存参数集版本号、冻结日期和配置哈希。所有“尚未冻结”项的相关完整标签在第一道筛选关的盲态基准确定生产值前均不运行，并输出 `unresolved`；不得由响应数据补定。

| 参数组 | 登记内容 | 当前状态 |
|---|---|---|
| 对称与局域 | `symprec`、两套 CN 定义、高配位阈值、配位多面体面共享判据 | 尚未冻结 |
| 几何构图 | 原子半径表、成键规则、探针范围与步长 | 尚未冻结 |
| 路径与窗口 | 路径上限 `K`、窗口归属/唯一规则、目标维度 `d` | 尚未冻结 |
| 能量网络 | 一级稀疏采样集合、沿连接采样及连接纳入规则、响应盲态分类阈值、BVSE 网格、能量步长、插值、能量域、目标维度 `d` | 尚未冻结 |
| 通道形态 | M07 起伏阈值、显著性阈值、连续段阈值、响应盲态类别映射 | 尚未冻结 |
| 转动与刚性 | 转动采样数 `N_orientation`、邻接阈值、联合单元上限 `n_unit,max`、边上限 `N_edge`、刚性约束、刚性自由度上限、`epsilon` | 尚未冻结 |
| 占位优化 | MILP 展开、能量允许集、优化迭代上限、求解时间/内存限额 | 尚未冻结 |

`symprec` 是对称性识别容差；导入电导率前，二道构造稳定性检查的登记版本、状态码和标签一并保存，以区分稳定标签、构造冲突与资源限额导致的未解决。

一级验收目标（非实测生产值）为中位数 P50≤3 s/CIF、95 分位数 P95≤20 s/CIF、超时 60 s、每进程常驻集大小峰值（RSS）≤1 GB；P50/P95 描述耗时分布，RSS 表示常驻物理内存。

二级单分支验收目标（非实测生产值）为 P50≤120 s、P95≤600 s、超时 900 s、RSS≤4 GB/进程。记录无缓存首次计算时间、复用缓存后新增时间、峰值内存、状态码分布和 CIF/核时；超时和内存超限不得编码为零、空白或“不存在”。完整描述符超限时转入 L3 小样本验证，不作为 L1/L2 阴性结果。

### A6. 统计、抽样与机器学习缩写

响应为室温离子电导率的十为底对数 `log10(sigma_RT)`；观测单位为“组成+相/结构+测量条件+文献来源”，不是单一 CIF。

同一观测的所有结构标签在读取响应前生成；响应仅用于冻结后定义的验证性或探索性分析。

验证性主检验的 5–6 项假设组成同一家族，采用 Holm 逐步校正以控制家族错误率 FWER；FWER 表示至少一次第一类错误的概率。探索性 X11–X15 控制错误发现率 FDR，报告 `q` 值和完整假设族；FDR 表示被报告发现中预期错误发现的比例。

机器学习采用嵌套交叉验证（nested CV）：内层选择特征和超参数，外层只评价。内层选定后，必须在完整外层训练折重新拟合全部预处理和模型，并且只评价一次外层测试折。材料—文献来源二部图的连通分量是不可拆分的外层分组；独立组过少时，嵌套交叉验证和按材料体系逐一留出（LOSO，逐体系留出）仅作压力测试。

任何标准化、缺失处理和特征选择均只在训练数据拟合，再应用至相应验证或外层测试数据。

数据库部署时，二级可只复核不读电导率规则选出的 10%–20% 候选。带电导率的验证性数据原则上对全部合格结构运行二级；若不可行，以唯一结构 `s` 为抽样单位、以观测 `o` 为分析单位，并预先冻结每条 `o` 到 `s(o)` 的唯一映射；不能唯一映射时按预先规则标为 `ambiguous` 或排除。

分层随机抽样预先给出结构入选率 `pi_s>0` 与观测权重 `w_o=1/pi_s`。类别 `g` 的 Hájek 均值为 `Σ_{o∈sample}1(G_o=g)w_oy_o / Σ_{o∈sample}1(G_o=g)w_o`，其中 `sample` 为被抽中的观测、`G_o` 是观测类别、`1(G_o=g)` 是类别指示量、`y_o` 是响应、`w_o` 是其反入选率权重。回归用同权重估计方程，方差按抽样分层及材料—来源连通分量作聚类稳健估计。抽样框、分层变量和入选概率表随结构清单冻结；权重不能恢复确定性排除、零入选概率或二级计算失败，二级计算失败也不能靠权重恢复。

估计目标（estimand）只限前三道关合格、可唯一映射且 `pi_s>0` 的总体；映射失败另报外推边界。所有抽样、映射、权重与方差规则在读取响应前冻结。
