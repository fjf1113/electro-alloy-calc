import re
from typing import Optional, Tuple, Dict, Any

# ---------------------------------------------------------------------------
# 基础电阻率库（常温 20℃，单位 μΩ·m == Ω·mm²/m）
# 供米电阻正向/逆向计算使用（与既有 calc_resistance / reverse_solve 兼容）
# ---------------------------------------------------------------------------
ALLOY_RESISTIVITY_DB = {
    "HRE": 1.45,
    "HYZ": 1.45,
    "0Cr21Al6Nb": 1.43,
    "0Cr25Al5A": 1.40,
    "0Cr23Al5": 1.35,
    "0Cr19Al5": 1.33,
    "0Cr19Al3": 1.23,
    "1Cr13Al4": 1.25,
    "Cr20Ni80": 1.09,
    "Cr15Ni60": 1.12,
    "Cr30Ni70": 1.18,
    "Cr20Ni40": 1.05,
}

# ---------------------------------------------------------------------------
# 材料工程属性库（用于元件设计计算）
# 字段说明：
#   resistivity  常温电阻率 μΩ·m
#   density      密度 g/cm³
#   temp_factor  电阻温度系数 = 高温电阻率 / 常温电阻率（约在设计温度下的比值，参考值）
#   max_use_temp 最高推荐使用温度 ℃（参考值）
#   max_surface_load 推荐表面负荷上限 W/cm²（参考值，随温度/气氛变化）
# 注：temp_factor / max_use_temp / max_surface_load 为工程参考值，
#     实际选型请以对应牌号标准与工况为准。
# ---------------------------------------------------------------------------
ALLOY_PROPS = {
    # 铁铬铝系 (Fe-Cr-Al)
    "HRE":        {"resistivity": 1.45, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1300, "max_surface_load": 1.6},
    "HYZ":        {"resistivity": 1.45, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1300, "max_surface_load": 1.6},
    "0Cr21Al6Nb": {"resistivity": 1.43, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1350, "max_surface_load": 1.7},
    "0Cr25Al5A":  {"resistivity": 1.40, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1250, "max_surface_load": 1.5},
    "0Cr23Al5":   {"resistivity": 1.35, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1250, "max_surface_load": 1.5},
    "0Cr19Al5":   {"resistivity": 1.33, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1150, "max_surface_load": 1.4},
    "0Cr19Al3":   {"resistivity": 1.23, "density": 7.1, "temp_factor": 1.04, "max_use_temp": 1100, "max_surface_load": 1.3},
    "1Cr13Al4":   {"resistivity": 1.25, "density": 7.2, "temp_factor": 1.05, "max_use_temp": 950,  "max_surface_load": 1.2},
    "0Cr27Al7Mo2":{"resistivity": 1.53, "density": 7.1, "temp_factor": 1.05, "max_use_temp": 1400, "max_surface_load": 1.8},
    # 镍铬系 (Ni-Cr)
    "Cr20Ni80":   {"resistivity": 1.09, "density": 8.4, "temp_factor": 1.11, "max_use_temp": 1200, "max_surface_load": 1.5},
    "Cr15Ni60":   {"resistivity": 1.12, "density": 8.2, "temp_factor": 1.11, "max_use_temp": 1150, "max_surface_load": 1.4},
    "Cr30Ni70":   {"resistivity": 1.18, "density": 8.1, "temp_factor": 1.11, "max_use_temp": 1250, "max_surface_load": 1.6},
    "Cr20Ni40":   {"resistivity": 1.05, "density": 8.5, "temp_factor": 1.11, "max_use_temp": 1100, "max_surface_load": 1.3},
}

ALLOY_ALIASES = {
    "hre": "HRE", "hyz": "HYZ",
    "0cr21al6nb": "0Cr21Al6Nb", "0cr21al6": "0Cr21Al6Nb", "21al6nb": "0Cr21Al6Nb", "216nb": "0Cr21Al6Nb", "216": "0Cr21Al6Nb", "0cr216": "0Cr21Al6Nb",
    "0cr25al5a": "0Cr25Al5A", "0cr25al5": "0Cr25Al5A", "255a": "0Cr25Al5A", "255": "0Cr25Al5A", "0255": "0Cr25Al5A", "25al5": "0Cr25Al5A",
    "0cr23al5": "0Cr23Al5", "235": "0Cr23Al5", "0235": "0Cr23Al5", "23al5": "0Cr23Al5",
    "0cr19al5": "0Cr19Al5", "195": "0Cr19Al5", "0195": "0Cr19Al5", "19al5": "0Cr19Al5",
    "0cr19al3": "0Cr19Al3", "193": "0Cr19Al3", "0193": "0Cr19Al3", "19al3": "0Cr19Al3",
    "1cr13al4": "1Cr13Al4", "134": "1Cr13Al4", "13al4": "1Cr13Al4",
    "0cr27al7mo2": "0Cr27Al7Mo2", "277": "0Cr27Al7Mo2",
    "cr20ni80": "Cr20Ni80", "2080": "Cr20Ni80", "8020": "Cr20Ni80", "ni80": "Cr20Ni80", "cr2080": "Cr20Ni80",
    "cr15ni60": "Cr15Ni60", "1560": "Cr15Ni60", "6015": "Cr15Ni60", "ni60": "Cr15Ni60", "cr1560": "Cr15Ni60",
    "cr30ni70": "Cr30Ni70", "3070": "Cr30Ni70", "ni70": "Cr30Ni70",
    "cr20ni40": "Cr20Ni40", "2040": "Cr20Ni40", "ni40": "Cr20Ni40",
}

def normalize_alloy_name(user_input: str) -> Optional[str]:
    if not user_input:
        return None
    clean = re.sub(r'[\s\-_—·,，]+', '', str(user_input)).lower()
    if clean in ALLOY_ALIASES:
        return ALLOY_ALIASES[clean]
    for alias, std_name in sorted(ALLOY_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in clean:
            return std_name
    return None

def get_alloy_resistivity(alloy_input: str, custom_rho: Optional[float] = None) -> Tuple[str, float]:
    """返回 (标准牌号, 常温电阻率)。custom_rho 优先，其次匹配内置库。"""
    if custom_rho is not None and custom_rho > 0:
        return (alloy_input.strip(), custom_rho)
    std_name = normalize_alloy_name(alloy_input)
    if std_name and std_name in ALLOY_RESISTIVITY_DB:
        return (std_name, ALLOY_RESISTIVITY_DB[std_name])
    raise ValueError(f"未识别到牌号 '{alloy_input}'，请检查名称或提供自定义电阻率。")

def get_alloy_props(alloy_input: str, custom_rho: Optional[float] = None) -> Dict[str, Any]:
    """返回材料完整工程属性；custom_rho 可覆盖电阻率。
    未命中属性库时回退到仅电阻率（density/alpha 需调用方自行提供）。"""
    if custom_rho is not None and custom_rho > 0:
        return {"alloy_standard": alloy_input.strip(), "resistivity": custom_rho,
                "density": None, "temp_factor": None, "max_use_temp": None, "max_surface_load": None}
    std_name = normalize_alloy_name(alloy_input)
    if std_name and std_name in ALLOY_PROPS:
        p = dict(ALLOY_PROPS[std_name])
        p["alloy_standard"] = std_name
        if custom_rho:
            p["resistivity"] = custom_rho
        return p
    # 仅命中电阻率库
    if std_name and std_name in ALLOY_RESISTIVITY_DB:
        return {"alloy_standard": std_name, "resistivity": ALLOY_RESISTIVITY_DB[std_name],
                "density": None, "temp_factor": None, "max_use_temp": None, "max_surface_load": None}
    raise ValueError(f"未识别到牌号 '{alloy_input}'，请检查名称或提供自定义电阻率/密度。")
