<!-- sha: fbd5917 -->

# 描述符源码抽取 — 批次 1

本批覆盖第 1–11 条（共 41 条，分 4 批）。

## a2_max_dist

### 字段

- name: `a2_max_dist`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_a2_max_dist`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:109-116`

```python
def compute_a2_max_dist(struct: Structure) -> float:
    """Na-X 最长键长均值 (Å)。

    即局域宽松因子的分子部分。
    已知 Spearman 相关: 0.597 (与 log10 电导率)。
    """
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_max"])
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## poly_distortion_mean

### 字段

- name: `poly_distortion_mean`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_poly_distortion_mean`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:119-134`

```python
def compute_poly_distortion_mean(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> float:
    """Na 多面体畸变均值。

    每个Na位点 Na-X 键长的变异系数(CV)，然后对所有Na位点取均值。
    参数透传到 _collect_na_x_data → _shell_neighbors，默认值与参数化前逐位一致。
    """
    data = _collect_na_x_data(
        struct,
        shell_tolerance=shell_tolerance,
        min_shell_size=min_shell_size,
    )
    return _safe_mean(data["per_site_distortion"])
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## max_bond_length

### 字段

- name: `max_bond_length`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_max_bond_length`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `False`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:137-139`

```python
def compute_max_bond_length(struct: Structure) -> float:
    """Na-X 最长键长均值 (Å) — a2_max_dist 的别名。"""
    return compute_a2_max_dist(struct)
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_a2_max_dist` → [附录: helper 源码](#helper-compute_a2_max_dist)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## min_bond_length

### 字段

- name: `min_bond_length`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_min_bond_length`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:142-145`

```python
def compute_min_bond_length(struct: Structure) -> float:
    """Na-X 最短键长均值 (Å)。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_min"])
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## mean_bond_length

### 字段

- name: `mean_bond_length`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_mean_bond_length`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:148-151`

```python
def compute_mean_bond_length(struct: Structure) -> float:
    """Na-X 平均键长均值 (Å)。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_mean"])
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## target_bond_center

### 字段

- name: `target_bond_center`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_target_bond_center`  (source: descriptor_registry.yaml)
- dimension: `length`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:154-174`

```python
def compute_target_bond_center(struct: Structure) -> float:
    """Na-X 目标键长中心 (Å)。

    R0 = R_Na(CN_mode) + R_anion_avg，
    由 Shannon 有效离子半径加权得到。
    """
    data = _collect_na_x_data(struct)
    if not data["per_site_cn"]:
        return float("nan")

    # 众数配位数
    from collections import Counter
    cn_counter = Counter(data["per_site_cn"])
    mode_cn = cn_counter.most_common(1)[0][0]

    na_r = _effective_na_radius(mode_cn)
    anion_r = _effective_anion_radius(data["anions"])
    if anion_r is None:
        return float("nan")

    return float(na_r + anion_r)
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_effective_anion_radius` → [附录: helper 源码](#helper-_effective_anion_radius)
- `_effective_na_radius` → [附录: helper 源码](#helper-_effective_na_radius)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## poly_volume_mean

### 字段

- name: `poly_volume_mean`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_poly_volume_mean`  (source: descriptor_registry.yaml)
- dimension: `volume`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `angstrom^3`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:177-180`

```python
def compute_poly_volume_mean(struct: Structure) -> float:
    """Na 多面体体积均值 (Å³)，基于 Voronoi 分配。"""
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_volume"])
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## coordination_number_mean

### 字段

- name: `coordination_number_mean`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_coordination_number_mean`  (source: descriptor_registry.yaml)
- dimension: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `count`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:183-188`

```python
def compute_coordination_number_mean(struct: Structure) -> float:
    """Na 主配位数均值，基于 VoronoiNN 第一壳层。"""
    data = _collect_na_x_data(struct)
    if not data["per_site_cn"]:
        return float("nan")
    return float(np.mean(data["per_site_cn"]))
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## ellipsoid_oblateness

### 字段

- name: `ellipsoid_oblateness`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_ellipsoid_oblateness`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:191-222`

```python
def compute_ellipsoid_oblateness(struct: Structure) -> float:
    """Na-X 键向量椭球扁率。

    对每个 Na 位点的 Na-X 键向量做 PCA，
    取 λ_max / λ_min 后对所有 Na 位点取均值。
    值越大说明配位越扁平/各向异性。
    """
    data = _collect_na_x_data(struct)
    if not data["per_site_bonds"]:
        return float("nan")

    oblateness_list: list[float] = []
    for bonds in data["per_site_bonds"]:
        if len(bonds) < 3:
            continue
        vecs = np.array([bv[2] for bv in bonds], dtype=float)
        # 中心化
        vecs_centered = vecs - vecs.mean(axis=0)
        # 协方差矩阵
        cov = np.cov(vecs_centered.T)
        if cov.ndim != 2 or cov.shape[0] < 2:
            continue
        try:
            eigenvalues = np.linalg.eigvalsh(cov)
            eigenvalues = np.sort(eigenvalues)
            eigenvalues = eigenvalues[eigenvalues > 1e-12]
            if len(eigenvalues) >= 2:
                oblateness_list.append(float(eigenvalues[-1] / eigenvalues[0]))
        except np.linalg.LinAlgError:
            continue

    return _safe_mean(oblateness_list)
```

### 仓内 helper（AST 传递闭包）

- `_collect_na_x_data` → [附录: helper 源码](#helper-_collect_na_x_data)
- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `compute_polyhedron_volume` → [附录: helper 源码](#helper-compute_polyhedron_volume)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

（无模块级常量引用）

---

## direction_ratio

### 字段

- name: `direction_ratio`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_direction_ratio`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `True`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:225-244`

```python
def compute_direction_ratio(struct: Structure) -> float:
    """方向比: 每个Na位点最长键 / 次长键，然后取均值。

    反映瓶颈通道的方向性。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return float("nan")

    ratios: list[float] = []
    for na_idx in na_indices:
        shell = _shell_neighbors(struct, na_idx, anions)
        distances = sorted([float(n["distance"]) for n in shell])
        if len(distances) >= 2:
            ratios.append(distances[-1] / distances[-2])

    return _safe_mean(ratios)
```

### 仓内 helper（AST 传递闭包）

- `_safe_mean` → [附录: helper 源码](#helper-_safe_mean)
- `_shell_neighbors` → [附录: helper 源码](#helper-_shell_neighbors)
- `element_symbol` → [附录: helper 源码](#helper-element_symbol)
- `get_na_sites` → [附录: helper 源码](#helper-get_na_sites)

### 引用的模块级常量

- `ANION_ELEMENTS` → [附录: 常量定义](#const-ANION_ELEMENTS)

---

## bottleneck_anisotropy

### 字段

- name: `bottleneck_anisotropy`  (source: descriptor_registry.yaml)
- family: `A`  (source: descriptor_registry.yaml)
- module: `family_a_polyhedron.py`  (source: descriptor_registry.yaml)
- implementation_symbol: `compute_bottleneck_anisotropy`  (source: descriptor_registry.yaml)
- dimension: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- unit: `dimensionless`  (source: STRUCTURE_DESCRIPTOR_METADATA)
- in_searchable: `False`  (source: descriptor_registry.yaml)

### compute_* 函数源码

文件: `descriptors/family_a_polyhedron.py:247-253`

```python
def compute_bottleneck_anisotropy(struct: Structure) -> float:
    """瓶颈各向异性 (BVSE 依赖)。

    需要 BVSE 势能面数据，当前返回 NaN。
    未来可集成 SoftBV 计算结果。
    """
    return float("nan")
```

### 仓内 helper（AST 传递闭包）

（无仓内 helper）

### 引用的模块级常量

（无模块级常量引用）

---

## 附录

### A. helper 源码

<a id="helper-_collect_na_x_data"></a>
#### `_collect_na_x_data` — `descriptors/family_a_polyhedron.py:24-106`

```python
def _collect_na_x_data(
    struct: Structure,
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> dict:
    """收集所有 Na 位点的 Na-X 键信息，返回中间数据字典。

    参数透传到 _shell_neighbors，默认值与参数化前逐位一致。
    """
    na_indices = get_na_sites(struct)
    species_symbols = {element_symbol(el) for el in struct.composition.elements}
    anions = species_symbols & ANION_ELEMENTS

    if not na_indices or not anions:
        return {
            "all_distances": [],
            "per_site_max": [],
            "per_site_min": [],
            "per_site_mean": [],
            "per_site_distortion": [],
            "per_site_cn": [],
            "per_site_volume": [],
            "per_site_bonds": [],
            "anions": anions,
            "na_indices": na_indices,
        }

    all_distances: list[float] = []
    per_site_max: list[float] = []
    per_site_min: list[float] = []
    per_site_mean: list[float] = []
    per_site_distortion: list[float] = []
    per_site_cn: list[int] = []
    per_site_volume: list[float] = []
    per_site_bonds: list[list[tuple]] = []

    for na_idx in na_indices:
        shell = _shell_neighbors(
            struct, na_idx, anions,
            shell_tolerance=shell_tolerance,
            min_shell_size=min_shell_size,
        )
        distances = [float(n["distance"]) for n in shell]

        if not distances:
            continue

        # 键向量 (用于 PCA 分析)
        center_coords = np.array(struct[na_idx].coords, dtype=float)
        bond_vectors = []
        for n in shell:
            vec = np.array(n["coords"], dtype=float) - center_coords
            bond_vectors.append((n["symbol"], n["distance"], vec))

        all_distances.extend(distances)
        per_site_max.append(max(distances))
        per_site_min.append(min(distances))
        per_site_mean.append(float(np.mean(distances)))
        per_site_cn.append(len(shell))
        per_site_bonds.append(bond_vectors)

        # 畸变 = 变异系数 (CV)
        if len(distances) > 1:
            cv = float(np.std(distances, ddof=0) / np.mean(distances))
            per_site_distortion.append(cv)

        # 多面体体积
        vol = compute_polyhedron_volume(struct, na_idx)
        if not np.isnan(vol):
            per_site_volume.append(vol)

    return {
        "all_distances": all_distances,
        "per_site_max": per_site_max,
        "per_site_min": per_site_min,
        "per_site_mean": per_site_mean,
        "per_site_distortion": per_site_distortion,
        "per_site_cn": per_site_cn,
        "per_site_volume": per_site_volume,
        "per_site_bonds": per_site_bonds,
        "anions": anions,
        "na_indices": na_indices,
    }
```

<a id="helper-_effective_anion_radius"></a>
#### `_effective_anion_radius` — `descriptors/_base.py:266-283`

```python
def _effective_anion_radius(anion_symbols: set[str]) -> float | None:
    """计算阴离子有效离子半径加权平均值 (Å)。

    若阴离子中包含 N（无经典值），返回 None。
    """
    if not anion_symbols:
        return None
    values: list[tuple[str, float]] = []
    missing: list[str] = []
    for sym in sorted(anion_symbols):
        r = ANION_EFFECTIVE_RADII_A.get(sym)
        if r is None:
            missing.append(sym)
        else:
            values.append((sym, r))
    if missing or not values:
        return None
    return sum(r for _, r in values) / len(values)
```

<a id="helper-_effective_na_radius"></a>
#### `_effective_na_radius` — `descriptors/_base.py:256-263`

```python
def _effective_na_radius(cn: int | None) -> float:
    """根据配位数返回 Na+ 有效离子半径 (Å)。

    未列入的 CN 使用 CN=6 的默认值。
    """
    if cn is not None and cn in NA_EFFECTIVE_RADII_A:
        return NA_EFFECTIVE_RADII_A[cn]
    return NA_EFFECTIVE_RADII_A[NA_FALLBACK_CN]
```

<a id="helper-_safe_mean"></a>
#### `_safe_mean` — `descriptors/_base.py:385-389`

```python
def _safe_mean(values: list[float]) -> float:
    """安全求均值，空列表返回 NaN。"""
    if not values:
        return float("nan")
    return float(np.mean(values))
```

<a id="helper-_shell_neighbors"></a>
#### `_shell_neighbors` — `descriptors/_base.py:210-253`

```python
def _shell_neighbors(
    struct: Structure,
    center_index: int,
    anion_symbols: set[str],
    shell_tolerance: float = 0.70,
    min_shell_size: int = 4,
) -> list[dict]:
    """提取 Na 位点的第一配位壳层 Na-X 近邻。

    沿用 part1.py 的简化规则: 取最短键长 +shell_tolerance Å 内的阴离子，
    若不足 min_shell_size 个则补至 min_shell_size。

    参数:
        shell_tolerance: 截断增量 (Å)，默认 0.70（与 part1.py 一致）
        min_shell_size: 最小壳层大小，不足时补至此数，默认 4
    """
    center = struct[center_index]
    cutoff = _anion_cutoff(anion_symbols)
    raw = struct.get_sites_in_sphere(
        center.coords, cutoff, include_index=True, include_image=True
    )
    center_coords = np.array(center.coords, dtype=float)
    neighbors: list[dict] = []
    for item in raw:
        site = item[0]
        dist = float(item[1])
        idx = int(item[2]) if len(item) >= 3 and item[2] is not None else None
        if idx == center_index and dist < 1e-6:
            continue
        sym = _major_species(site)
        if sym in ANION_ELEMENTS:
            coords_arr = np.array(site.coords, dtype=float)
            neighbors.append({
                "symbol": sym, "distance": dist,
                "coords": coords_arr, "index": idx,
            })
    neighbors.sort(key=lambda x: x["distance"])
    if not neighbors:
        return []
    first = neighbors[0]["distance"]
    kept = [n for n in neighbors if n["distance"] <= first + shell_tolerance]
    if len(kept) < min_shell_size and len(neighbors) > len(kept):
        kept = neighbors[:min(min_shell_size, len(neighbors))]
    return kept
```

<a id="helper-compute_a2_max_dist"></a>
#### `compute_a2_max_dist` — `descriptors/family_a_polyhedron.py:109-116`

```python
def compute_a2_max_dist(struct: Structure) -> float:
    """Na-X 最长键长均值 (Å)。

    即局域宽松因子的分子部分。
    已知 Spearman 相关: 0.597 (与 log10 电导率)。
    """
    data = _collect_na_x_data(struct)
    return _safe_mean(data["per_site_max"])
```

<a id="helper-compute_polyhedron_volume"></a>
#### `compute_polyhedron_volume` — `descriptors/_base.py:368-382`

```python
def compute_polyhedron_volume(struct: Structure, na_idx: int) -> float:
    """计算 Na 位点的 Voronoi 多面体体积 (Å³)。

    使用 pymatgen 的 VoronoiNN 计算配位多面体体积。
    """
    try:
        from pymatgen.analysis.local_env import VoronoiNN
        vnn = VoronoiNN()
        poly_info = vnn.get_voronoi_polyhedra(struct, na_idx)
        total_vol = 0.0
        for neighbor_info in poly_info.values():
            total_vol += neighbor_info.get("volume", 0.0)
        return float(total_vol) if total_vol > 0 else float("nan")
    except Exception:
        return float("nan")
```

<a id="helper-element_symbol"></a>
#### `element_symbol` — `descriptors/_base.py:106-111`

```python
def element_symbol(value: object) -> str:
    """Return an element symbol for an Element, Species, or species name."""
    symbol = getattr(value, "symbol", None)
    if symbol is not None:
        return str(symbol)
    return str(value).rstrip("+-0123456789")
```

<a id="helper-get_na_sites"></a>
#### `get_na_sites` — `descriptors/_base.py:122-132`

```python
def get_na_sites(struct: Structure) -> list[int]:
    """获取结构中 Na 位点的索引列表。

    Na 位点 = 主要物种为 Na 的位点（考虑部分占位）。
    """
    na_indices: list[int] = []
    for i, site in enumerate(struct):
        na_occ = site_occupancies_by_symbol(site).get("Na", 0.0)
        if na_occ > 1e-6:
            na_indices.append(i)
    return na_indices
```

### B. 模块级常量定义

<a id="const-ANION_ELEMENTS"></a>
#### `ANION_ELEMENTS` — `descriptors/_base.py:18-18`

```python
ANION_ELEMENTS: set[str] = {"O", "S", "Se", "F", "Cl", "Br", "I", "N", "H"}
```
