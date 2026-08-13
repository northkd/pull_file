# -*- coding: utf-8 -*-
"""
阶段 4 CIF 结构描述符生成模块
- 解析 103 个 CIF, 生成 Na-Na 网络 / 空位接入 / 通道各向异性 / 骨架柔性 4 类描述符
- 不修改原始 CIF, 不重算 SoftBV/Zeo++
"""
import os, re, warnings, numpy as np
from pymatgen.core import Structure
from scipy.spatial.distance import cdist
import networkx as nx
warnings.filterwarnings("ignore")

# Shannon 半径 (Na+, 常见阴离子) - 与表格 Shannon 列对齐
SHANNON_NA = 1.02  # Na+ VI 配位, Å
SHANNON_ANION = {"O": 1.40, "S": 1.84, "Se": 1.98, "Cl": 1.81, "Br": 1.96,
                 "I": 2.20, "H": 1.35, "F": 1.33, "N": 1.46, "B": 0.27, "C": 0.16}

# 阴离子候选 (用于识别 Na 的近邻阴离子)
ANIONS = {"O","S","Se","Cl","Br","I","H","F","N"}

def get_na_sites(s):
    """提取 Na 位点索引, 兼容 Na / Na+ 形式"""
    na = []
    for i, site in enumerate(s):
        elts = [e.symbol for e in site.species.elements]
        if "Na" in elts:
            na.append(i)
    return na

def na_occupancy(site):
    """Na 位点的占位率"""
    comp = site.species.as_dict()
    return sum(v for k, v in comp.items() if k.replace("+","") == "Na")

def get_anion_neighbors(s, na_idx, cutoff=4.0):
    """获取每个 Na 位点的阴离子近邻 (cutoff Å 内), 全部用 species.elements 避免混合占位报错"""
    results = []
    for idx in na_idx:
        nbrs = []
        for j, site in enumerate(s):
            if j == idx: continue
            elts = [e.symbol for e in site.species.elements]
            anion = next((e for e in elts if e in ANIONS), None)
            if anion is None: continue
            try:
                d = s.get_distance(idx, j)
                if not np.isnan(d) and d <= cutoff:
                    nbrs.append((anion, site.frac_coords, j))
            except Exception:
                pass
        results.append(nbrs)
    return results

def parse_one_cif(cif_path):
    """解析单个 CIF, 返回结构 + 元信息"""
    res = {"解析状态": "成功", "错误原因": "", "structure": None}
    try:
        s = Structure.from_file(cif_path)
        s = s.get_primitive_structure() if len(s) > 200 else s
        res["structure"] = s
        res["原子数"] = len(s)
        na = get_na_sites(s)
        res["Na位点数_CIF"] = len(na)
        res["部分占位Na位点数"] = sum(1 for i in na if na_occupancy(s[i]) < 0.999)
        res["是否部分占位_CIF"] = "是" if res["部分占位Na位点数"] > 0 else "否"
        res["能提取Na位点"] = "是" if len(na) > 0 else "否"
    except Exception as e:
        res["解析状态"] = "失败"
        res["错误原因"] = str(e)[:120]
        res["structure"] = None
    return res

# ============================================================
# Na-Na 网络描述符
# ============================================================
def nana_network(s, na_idx, na_cutoff=6.0):
    """构建 Na-Na 网络 (周期性距离), 用 networkx 算连通性"""
    n = len(na_idx)
    if n < 2:
        return {"Na位点数_CIF": n, "Na-Na最近距离_CIF": np.nan,
                "Na-Na平均最近邻距离_CIF": np.nan, "Na-Na距离标准差_CIF": np.nan,
                "每个Na平均Na邻居数": np.nan, "Na邻居数最大值": np.nan,
                "Na邻居数最小值": np.nan, "Na网络连通分量数": np.nan,
                "最大Na连通分量占比": np.nan, "Na网络是否贯通": "无法判断",
                "Na网络维度估计": "无法判断", "Na网络维度置信度": "低",
                "Na-Na路径瓶颈近似值": np.nan}
    # 全部 Na-Na 距离 (含周期性)
    coords = np.array([s[i].frac_coords for i in na_idx])
    lattice = s.lattice
    # 用 get_distance 逐对 (n<=50 可接受)
    dists_all = []
    nn_dists = []  # 每个 Na 的最近邻距离
    neighbors = [[] for _ in range(n)]  # 邻居索引
    for i in range(n):
        di = []
        for j in range(n):
            if i == j: continue
            try:
                d = s.get_distance(na_idx[i], na_idx[j])
            except Exception:
                d = np.nan
            di.append((j, d))
            if not np.isnan(d):
                dists_all.append(d)
        di = [(j,d) for j,d in di if not np.isnan(d)]
        if di:
            di.sort(key=lambda x: x[1])
            nn_dists.append(di[0][1])
            # 邻居: 距离 < cutoff 的 (迁移跳跃距离通常<6Å)
            for j, d in di:
                if d <= na_cutoff:
                    neighbors[i].append(j)
    # 全部距离统计
    da = np.array(dists_all)
    nn = np.array(nn_dists) if nn_dists else np.array([np.nan])
    # 最近距离 = 全局最小
    nn_min = da.min() if len(da) else np.nan
    # 邻居数统计
    nn_counts = [len(nb) for nb in neighbors]
    # 连通分量 (networkx)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for i in range(n):
        for j in neighbors[i]:
            G.add_edge(i, j)
    components = list(nx.connected_components(G))
    n_comp = len(components)
    largest = max(len(c) for c in components) if components else 0
    largest_frac = largest / n if n else 0
    percolated = "是" if largest_frac >= 0.8 and n_comp <= 3 else "否"
    # 维度估计: 用 Na 位点在三个晶轴方向的跨度 + 连通性
    # 简化规则: 若最大连通分量占比高且三轴均有 Na, 估计 3D; 否则按跨度判断
    spans = []
    for ax in range(3):
        coord_ax = coords[:, ax]
        span = coord_ax.max() - coord_ax.min()
        spans.append(span)
    span_arr = np.array(spans)
    if percolated == "是" and all(spans) and n >= 5:
        dim_est = "3D"; conf = "中"
    elif largest_frac >= 0.5:
        # 看主要连通分量的各向异性
        dim_est = "2D/3D"; conf = "低"
    else:
        dim_est = "1D/2D"; conf = "低"
    # 路径瓶颈近似: Na-Na 距离的中位数 (近似跳跃瓶颈)
    path_bottleneck = float(np.median(nn)) if len(nn) else np.nan
    return {
        "Na位点数_CIF": n, "Na-Na最近距离_CIF": round(nn_min, 4),
        "Na-Na平均最近邻距离_CIF": round(float(np.mean(nn)), 4),
        "Na-Na距离标准差_CIF": round(float(np.std(da)), 4) if len(da) else np.nan,
        "每个Na平均Na邻居数": round(float(np.mean(nn_counts)), 3),
        "Na邻居数最大值": int(max(nn_counts)) if nn_counts else 0,
        "Na邻居数最小值": int(min(nn_counts)) if nn_counts else 0,
        "Na网络连通分量数": n_comp,
        "最大Na连通分量占比": round(largest_frac, 3),
        "Na网络是否贯通": percolated,
        "Na网络维度估计": dim_est, "Na网络维度置信度": conf,
        "Na-Na路径瓶颈近似值": round(path_bottleneck, 4),
    }

# ============================================================
# 空位通道接入描述符
# ============================================================
def vacancy_channel(s, na_idx, na_cutoff=6.0):
    """空位接入判断: 部分占位 Na 位点 = 候选空位"""
    n = len(na_idx)
    # 候选空位 = 占位率<1 的 Na 位点
    vacancies = []  # (idx, vacancy_frac)
    for i in na_idx:
        occ = na_occupancy(s[i])
        if occ < 0.999:
            vacancies.append((i, 1.0 - occ))
    n_vac_sites = len(vacancies)
    total_vac = sum(v for _, v in vacancies)
    has_partial = "是" if n_vac_sites > 0 else "否"
    if n_vac_sites == 0 or n == 0:
        return {"是否存在部分占位Na位点": has_partial,
                "候选空位数_CIF": n_vac_sites, "空位总量_CIF": round(total_vac, 4),
                "Na-空位最近距离_CIF": np.nan, "Na-空位平均距离_CIF": np.nan,
                "空位-Na连接数": np.nan, "空位是否接入Na主网络": "无空位",
                "空位接入主网络比例": np.nan, "Na-空位网络维度估计": "无空位",
                "空位接入状态": "无空位"}
    # Na-空位距离 (空位=部分占位位点, 距离所有其他Na位点, 含其他部分占位)
    vac_idxs = [i for i, _ in vacancies]
    all_na = na_idx  # 全部 Na 位点
    dists = []
    connected = 0
    for vi in vac_idxs:
        best = np.nan
        for ni in all_na:
            if ni == vi: continue
            try:
                d = s.get_distance(vi, ni)
                if not np.isnan(d):
                    if np.isnan(best) or d < best:
                        best = d
            except Exception:
                pass
        if not np.isnan(best):
            dists.append(best)
            if best <= na_cutoff:
                connected += 1
    nn_dist = min(dists) if dists else np.nan
    avg_dist = float(np.mean(dists)) if dists else np.nan
    ratio = connected / n_vac_sites if n_vac_sites else np.nan
    # 接入状态
    if ratio >= 0.8:
        status = "接入主通道"; access = "是"
    elif ratio >= 0.3:
        status = "部分接入"; access = "部分"
    else:
        status = "局部孤立"; access = "否"
    # 网络维度估计 (空位接入主网络后)
    if access == "是":
        dim = "3D"; conf = "中"
    elif access == "部分":
        dim = "1D/2D"; conf = "低"
    else:
        dim = "0D(孤立)"; conf = "中"
    return {
        "是否存在部分占位Na位点": has_partial,
        "候选空位数_CIF": n_vac_sites, "空位总量_CIF": round(total_vac, 4),
        "Na-空位最近距离_CIF": round(nn_dist, 4) if not np.isnan(nn_dist) else np.nan,
        "Na-空位平均距离_CIF": round(avg_dist, 4) if not np.isnan(avg_dist) else np.nan,
        "空位-Na连接数": connected,
        "空位是否接入Na主网络": access,
        "空位接入主网络比例": round(ratio, 3) if not np.isnan(ratio) else np.nan,
        "Na-空位网络维度估计": dim,
        "空位接入状态": status,
    }

# ============================================================
# 通道各向异性描述符
# ============================================================
def channel_anisotropy(s, na_idx):
    """Na 位点空间分布各向异性"""
    n = len(na_idx)
    if n < 3:
        return {k: np.nan for k in ["Na-Na距离各向异性","Na位点空间分布各向异性",
                "Na网络a轴跨度","Na网络b轴跨度","Na网络c轴跨度","Na网络主方向",
                "通道曲折度近似值","局部瓶颈宽度分布近似值","是否1D2D3D迁移倾向"]}
    coords = np.array([s[i].frac_coords for i in na_idx])
    # 三轴跨度 (考虑周期性, 取最小镜像)
    spans = []
    for ax in range(3):
        c = coords[:, ax]
        # 周期性: 排序后取最大间隙, 跨度=1-最大间隙
        cs = np.sort(c)
        gaps = np.diff(cs)
        gap_wrap = (cs[0] + 1) - cs[-1]
        max_gap = max(gaps.max() if len(gaps) else 0, gap_wrap)
        span = 1.0 - max_gap  # 实际覆盖比例
        spans.append(span)
    a_span, b_span, c_span = spans
    # 各向异性 = 跨度的变异系数
    spans_arr = np.array(spans)
    aniso = float(np.std(spans_arr) / (np.mean(spans_arr) + 1e-9))
    # Na-Na 距离各向异性: 用距离的变异系数近似
    dists = []
    for i in range(min(n, 20)):
        for j in range(i+1, min(n, 20)):
            try:
                d = s.get_distance(na_idx[i], na_idx[j])
                if not np.isnan(d): dists.append(d)
            except: pass
    dist_aniso = float(np.std(dists)/(np.mean(dists)+1e-9)) if dists else np.nan
    # 主方向: 跨度最大的轴
    axes = ["a", "b", "c"]
    main_dir = axes[int(np.argmax(spans))]
    # 迁移倾向: 跨度差异
    s_sorted = sorted(spans, reverse=True)
    if s_sorted[0] > 0.7 and s_sorted[1] > 0.7 and s_sorted[2] > 0.7:
        mig = "3D倾向"
    elif s_sorted[0] > 0.7 and s_sorted[1] > 0.7:
        mig = "2D倾向"
    elif s_sorted[0] > 0.7:
        mig = "1D倾向"
    else:
        mig = "低连通"
    # 通道曲折度近似 = Na-Na 距离变异系数 / 跨度均值 (越大越曲折)
    tortuosity = dist_aniso / (np.mean(spans_arr) + 1e-9) if not np.isnan(dist_aniso) else np.nan
    # 局部瓶颈宽度 = Na-Na 最近距离 (近似)
    nn_min = min(dists) if dists else np.nan
    return {
        "Na-Na距离各向异性": round(dist_aniso, 4) if not np.isnan(dist_aniso) else np.nan,
        "Na位点空间分布各向异性": round(aniso, 4),
        "Na网络a轴跨度": round(a_span, 4), "Na网络b轴跨度": round(b_span, 4),
        "Na网络c轴跨度": round(c_span, 4),
        "Na网络主方向": main_dir,
        "通道曲折度近似值": round(tortuosity, 4) if not np.isnan(tortuosity) else np.nan,
        "局部瓶颈宽度分布近似值": round(nn_min, 4) if not np.isnan(nn_min) else np.nan,
        "是否1D2D3D迁移倾向": mig,
    }

# ============================================================
# 骨架局域柔性描述符
# ============================================================
def framework_flexibility(s, na_idx, cutoff=4.0):
    """骨架局域柔性: Na 周围阴离子 + 骨架阳离子 + 桥联"""
    n = len(na_idx)
    if n == 0:
        return {k: np.nan for k in ["Na邻近阴离子类型_CIF","Na周围阴离子种类数",
                "主骨架阳离子种类数_CIF","骨架多面体连接方式近似",
                "桥联阴离子比例","Na-X-骨架阳离子角度统计","骨架局域畸变指标",
                "局域柔性代理描述符"]}
    # 收集每个Na的阴离子近邻
    anion_nbrs = get_anion_neighbors(s, na_idx, cutoff)
    # Na邻近阴离子类型 (主)
    anion_types = []
    anion_variety = []
    for nbrs in anion_nbrs:
        elts = set(e for e, _, _ in nbrs)
        anion_variety.append(len(elts))
        anion_types.extend(elts)
    # 主阴离子 (最频繁)
    from collections import Counter
    cnt = Counter(anion_types)
    main_anion = cnt.most_common(1)[0][0] if cnt else "未知"
    # 骨架阳离子 (非Na非阴离子)
    cation_types = set()
    for site in s:
        elts = [e.symbol for e in site.species.elements]
        for e in elts:
            if e not in ANIONS and e != "Na":
                cation_types.add(e)
    # 桥联阴离子比例: 被多个骨架阳离子共享的阴离子
    # 简化: 阴离子位点中被>1个骨架阳离子近邻的比例
    anion_sites = [i for i, site in enumerate(s)
                   if any(e.symbol in ANIONS for e in site.species.elements)]
    bridging = 0
    total_anion_sites = len(anion_sites)
    # 桥联判定: 该阴离子周围有>=2个骨架阳离子
    for ai in anion_sites[:50]:  # 限制计算量
        cat_count = 0
        for j, site in enumerate(s):
            if j == ai: continue
            elts = [e.symbol for e in site.species.elements]
            if any(e not in ANIONS and e != "Na" for e in elts):
                try:
                    d = s.get_distance(ai, j)
                    if not np.isnan(d) and d <= cutoff:
                        cat_count += 1
                except: pass
        if cat_count >= 2:
            bridging += 1
    bridge_ratio = bridging / total_anion_sites if total_anion_sites else np.nan
    # Na-X-骨架阳离子角度统计 (用前几个Na)
    angles = []
    for ni in na_idx[:10]:
        nbrs = anion_nbrs[na_idx.index(ni)] if ni in na_idx else []
        for elt, fcoord, ai in nbrs[:3]:
            # 找该阴离子的骨架阳离子近邻
            for j, site in enumerate(s):
                elts = [e.symbol for e in site.species.elements]
                if any(e not in ANIONS and e != "Na" for e in elts):
                    try:
                        d1 = s.get_distance(ni, ai); d2 = s.get_distance(ai, j)
                        if not np.isnan(d1) and not np.isnan(d2) and d2 <= cutoff:
                            ang = s.get_angle(ni, ai, j)
                            if not np.isnan(ang): angles.append(ang)
                    except: pass
    angle_std = float(np.std(angles)) if len(angles) > 3 else np.nan
    # 骨架局域畸变: 阴离子种类数 + 桥联比例的代理
    # 局域柔性代理: 阴离子种类数少 + 桥联高 = 刚性骨架; 多样+低桥联 = 柔性
    avg_variety = float(np.mean(anion_variety)) if anion_variety else np.nan
    flex_proxy = avg_variety * (1 - (bridge_ratio if not np.isnan(bridge_ratio) else 0.5))
    return {
        "Na邻近阴离子类型_CIF": main_anion,
        "Na周围阴离子种类数": round(avg_variety, 3) if not np.isnan(avg_variety) else np.nan,
        "主骨架阳离子种类数_CIF": len(cation_types),
        "骨架多面体连接方式近似": f"桥联比例{bridge_ratio:.2f}" if not np.isnan(bridge_ratio) else "未知",
        "桥联阴离子比例": round(bridge_ratio, 3) if not np.isnan(bridge_ratio) else np.nan,
        "Na-X-骨架阳离子角度统计": round(angle_std, 3) if not np.isnan(angle_std) else np.nan,
        "骨架局域畸变指标": round(angle_std / (avg_variety + 1e-9), 4) if not np.isnan(angle_std) else np.nan,
        "局域柔性代理描述符": round(flex_proxy, 3) if not np.isnan(flex_proxy) else np.nan,
    }
