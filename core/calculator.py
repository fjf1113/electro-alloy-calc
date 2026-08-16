import math
from typing import Optional, Dict, Any
from core.alloy_db import get_alloy_resistivity

def calc_resistance(alloy_input: str, shape_type: str = "wire", diameter_mm: Optional[float] = None, width_mm: Optional[float] = None, thickness_mm: Optional[float] = None, shape_factor: float = 0.97, custom_rho: Optional[float] = None, tolerance: float = 0.05) -> Dict[str, Any]:
    std_name, rho = get_alloy_resistivity(alloy_input, custom_rho)
    if shape_type == "wire":
        if not diameter_mm or diameter_mm <= 0:
            raise ValueError("圆丝必须输入有效丝径 (mm)")
        area = math.pi * (diameter_mm ** 2) / 4.0
        spec_text = f"Ф{diameter_mm} mm"
        type_text = "圆丝"
    else:
        if not (width_mm and thickness_mm and width_mm > 0 and thickness_mm > 0):
            raise ValueError("扁带/扁丝必须输入有效的宽和厚 (mm)")
        area = width_mm * thickness_mm * shape_factor
        spec_text = f"{width_mm} × {thickness_mm} mm (系数 {shape_factor})"
        type_text = "扁带/扁丝"
    r_mid = rho / area
    return {"status": "success", "alloy_standard": std_name, "resistivity": rho, "spec_type": type_text, "spec_size": spec_text, "area_mm2": round(area, 6), "r_mid": round(r_mid, 4), "r_upper": round(r_mid * (1 + tolerance), 4), "r_lower": round(r_mid * (1 - tolerance), 4), "tolerance": f"±{int(tolerance * 100)}%"}

def reverse_solve_size(target_r_per_meter: float, alloy_input: str, shape_type: str = "wire", fixed_width_mm: Optional[float] = None, shape_factor: float = 0.95, custom_rho: Optional[float] = None) -> Dict[str, Any]:
    std_name, rho = get_alloy_resistivity(alloy_input, custom_rho)
    if target_r_per_meter <= 0:
        raise ValueError("目标米电阻必须大于 0")
    if shape_type == "wire":
        d = math.sqrt((4 * rho) / (math.pi * target_r_per_meter))
        return {"status": "success", "alloy_standard": std_name, "target_r": target_r_per_meter, "recommended_diameter_mm": round(d, 4)}
    else:
        if not fixed_width_mm or fixed_width_mm <= 0:
            raise ValueError("扁丝/扁带逆向推算必须提供固定宽度 (mm)")
        t = rho / (target_r_per_meter * fixed_width_mm * shape_factor)
        return {"status": "success", "alloy_standard": std_name, "target_r": target_r_per_meter, "fixed_width_mm": fixed_width_mm, "recommended_thickness_mm": round(t, 4)}
