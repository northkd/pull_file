"""descriptors 包共享异常定义。

ConfigurationError 从 family_h_symmetry.py 移出到此，避免：
1. featurizer 与 family_h_symmetry 形成错误的反向依赖（featurizer 为 catch 配置异常
   而 import 一个具体描述符族模块）；
2. _base.py 混入非物理/几何的配置语义。

选择独立 exceptions.py 而非 _base.py：_base.py 是物理/几何 helper 集合，
放配置异常类语义不当。
"""
from __future__ import annotations


class ConfigurationError(ValueError):
    """配置类异常（如 symprec 缺失），必须穿透 featurizer 的 except Exception。

    继承 ValueError 以保持既有 test_symprec_fail_loud 测试通过
    （那些测试断言 ValueError，ConfigurationError 是 ValueError 的子类）。
    """