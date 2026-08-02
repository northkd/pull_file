"""Na离子导体结构描述符注册表。

共 41 个描述符，分布在 8 个物理族中。
注册表格式: {name: (compute_func, family_key, is_high_risk)}

高风险族: G (电子代理), H (对称性破缺) 中的部分描述符。
"""
from __future__ import annotations

from collections.abc import Callable

from pymatgen.core import Structure

# ============================================================
# A族: Na多面体 (11个, 无高风险)
# ============================================================
from descriptors.family_a_polyhedron import (
    compute_a2_max_dist,
    compute_bottleneck_anisotropy,
    compute_coordination_number_mean,
    compute_direction_ratio,
    compute_ellipsoid_oblateness,
    compute_max_bond_length,
    compute_mean_bond_length,
    compute_min_bond_length,
    compute_poly_distortion_mean,
    compute_poly_volume_mean,
    compute_target_bond_center,
)

# ============================================================
# B族: Na-Na网络 (5个, 无高风险)
# ============================================================
from descriptors.family_b_network import (
    compute_avg_na_neighbors,
    compute_component_count,
    compute_largest_component_ratio,
    compute_nana_composite,
    compute_network_dimension,
)

# ============================================================
# C族: Na浓度 (3个, 无高风险)
# ============================================================
from descriptors.family_c_concentration import (
    compute_na_concentration,
    compute_na_occupancy_sum,
    compute_na_site_count,
)

# ============================================================
# D'族: 空位拓扑 (5个, 无高风险; BVSE依赖的返回NaN)
# ============================================================
from descriptors.family_d_vacancy_topo import (
    compute_bvse_barrier_estimate,
    compute_interstitial_channel_access,
    compute_interstitial_count,
    compute_interstitial_na_distance,
    compute_interstitial_network_dim,
)

# ============================================================
# E族: 骨架刚性 (4个, 无高风险)
# ============================================================
from descriptors.family_e_framework import (
    compute_framework_bond_rigidity,
    compute_framework_na_distance_stability,
    compute_framework_poly_distortion,
    compute_framework_sharing_topology,
)

# ============================================================
# F族: 长程关联 (4个, 无高风险)
# ============================================================
from descriptors.family_f_longrange import (
    compute_nana_nana_angle_mean,
    compute_nana_second_neighbor_dist,
    compute_nana_spacing_uniformity,
    compute_path_tortuosity,
)

# ============================================================
# G族: 电子代理 (4个, 全部高风险)
# ============================================================
from descriptors.family_g_electronic import (
    compute_charge_balance_deviation,
    compute_covalency_index,
    compute_framework_d_electron_weighted,
    compute_na_x_en_diff,
)

# ============================================================
# H族: 对称性破缺 (5个, 3个高风险)
# ============================================================
from descriptors.family_h_symmetry import (
    compute_coordination_cv,
    compute_partial_occupancy_ratio,
    compute_space_group_number,
    compute_volume_cv,
    compute_wyckoff_diversity,
)

# ============================================================
# 描述符注册表: {name: (compute_func, family_key, is_high_risk)}
# ============================================================
AVAILABLE_STRUCTURE_DESCRIPTORS: dict[str, tuple[Callable[[Structure], float], str, bool]] = {
    # --- A族: Na多面体 (11) ---
    "a2_max_dist": (compute_a2_max_dist, "A", False),
    "poly_distortion_mean": (compute_poly_distortion_mean, "A", False),
    "max_bond_length": (compute_max_bond_length, "A", False),
    "min_bond_length": (compute_min_bond_length, "A", False),
    "mean_bond_length": (compute_mean_bond_length, "A", False),
    "target_bond_center": (compute_target_bond_center, "A", False),
    "poly_volume_mean": (compute_poly_volume_mean, "A", False),
    "coordination_number_mean": (compute_coordination_number_mean, "A", False),
    "ellipsoid_oblateness": (compute_ellipsoid_oblateness, "A", False),
    "direction_ratio": (compute_direction_ratio, "A", False),
    "bottleneck_anisotropy": (compute_bottleneck_anisotropy, "A", True),

    # --- B族: Na-Na网络 (5) ---
    "nana_composite": (compute_nana_composite, "B", False),
    "avg_na_neighbors": (compute_avg_na_neighbors, "B", False),
    "largest_component_ratio": (compute_largest_component_ratio, "B", False),
    "network_dimension": (compute_network_dimension, "B", False),
    "component_count": (compute_component_count, "B", False),

    # --- C族: Na浓度 (3) ---
    "na_concentration": (compute_na_concentration, "C", False),
    "na_occupancy_sum": (compute_na_occupancy_sum, "C", False),
    "na_site_count": (compute_na_site_count, "C", False),

    # --- D'族: 空位拓扑 (5) ---
    "interstitial_count": (compute_interstitial_count, "D_prime", False),
    "interstitial_na_distance": (compute_interstitial_na_distance, "D_prime", False),
    "interstitial_channel_access": (compute_interstitial_channel_access, "D_prime", False),
    "interstitial_network_dim": (compute_interstitial_network_dim, "D_prime", False),
    "bvse_barrier_estimate": (compute_bvse_barrier_estimate, "D_prime", True),

    # --- E族: 骨架刚性 (4) ---
    "framework_bond_rigidity": (compute_framework_bond_rigidity, "E", False),
    "framework_poly_distortion": (compute_framework_poly_distortion, "E", False),
    "framework_na_distance_stability": (compute_framework_na_distance_stability, "E", False),
    "framework_sharing_topology": (compute_framework_sharing_topology, "E", False),

    # --- F族: 长程关联 (4) ---
    "nana_nana_angle_mean": (compute_nana_nana_angle_mean, "F", False),
    "nana_second_neighbor_dist": (compute_nana_second_neighbor_dist, "F", False),
    "path_tortuosity": (compute_path_tortuosity, "F", False),
    "nana_spacing_uniformity": (compute_nana_spacing_uniformity, "F", False),

    # --- G族: 电子代理 (4, 全部高风险) ---
    "na_x_en_diff": (compute_na_x_en_diff, "G", True),
    "charge_balance_deviation": (compute_charge_balance_deviation, "G", True),
    "covalency_index": (compute_covalency_index, "G", True),
    "framework_d_electron_weighted": (compute_framework_d_electron_weighted, "G", True),

    # --- H族: 对称性破缺 (5, 3高风险) ---
    "space_group_number": (compute_space_group_number, "H", True),
    "wyckoff_diversity": (compute_wyckoff_diversity, "H", True),
    "partial_occupancy_ratio": (compute_partial_occupancy_ratio, "H", True),
    "coordination_cv": (compute_coordination_cv, "H", False),
    "volume_cv": (compute_volume_cv, "H", False),
}

# 向后兼容: 保留原始名称
AVAILABLE_COMPOSITION_DESCRIPTORS = AVAILABLE_STRUCTURE_DESCRIPTORS
