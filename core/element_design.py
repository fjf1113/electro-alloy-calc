"""
电热元件设计计算模块
===================
复刻《电热元件设计计算公式.xlsx》中的确定性公式。所有长度单位：mm；
电阻率 rho：μΩ·m (== Ω·mm²/m)；密度：g/cm³；功率：kW / W；电压：V；
表面负荷：W/cm²。

关键恒等式（便于核对）：
  - 截面积 A (mm²)：圆丝 = π·d²/4；扁带 = 宽·厚·k (k 默认 0.98)
  - 电阻 R (Ω) = rho · L(m) / A(mm²)
  - 体积 V (cm³) = L(m) · A(mm²)        （1 m·mm² = 1 cm³）
  - 质量 m (kg) = V(cm³) · 密度(g/cm³) / 1000
  - 表面积 S (cm²) = 截面周长(mm) · L(m) · 10
  - 表面负荷 w = P(W) / S(cm²)
  - 高温电阻率 rho_h = rho · temp_factor（temp_factor = 电阻温度系数，约在设计温度下的比值）
"""
import math
from typing import Optional, Dict, Any

PI = math.pi

# --------------------------- 基础几何 ---------------------------
def _round_area(d: float) -> float:
    return PI * d * d / 4.0

def _round_perim(d: float) -> float:
    return PI * d

def _ribbon_area(w: float, t: float, k: float) -> float:
    return w * t * k

def _ribbon_perim(w: float, t: float, k: float) -> float:
    return (w + t) * 2.0 * k


# --------------------------- 1. 质量 / 电阻核算 ---------------------------
def calc_mass(shape: str, length_m: float, rho: float, density: float,
              d: Optional[float] = None, w: Optional[float] = None,
              t: Optional[float] = None, k: float = 0.98) -> Dict[str, Any]:
    """已知尺寸与长度，求截面积、体积、质量、常温电阻。"""
    if shape == "wire":
        if not (d and d > 0):
            raise ValueError("圆丝需输入有效丝径 d (mm)")
        area, perim = _round_area(d), _round_perim(d)
        spec = f"Ф{d} mm"
    else:
        if not (w and t and w > 0 and t > 0):
            raise ValueError("扁带需输入有效宽 w 与厚 t (mm)")
        area, perim = _ribbon_area(w, t, k), _ribbon_perim(w, t, k)
        spec = f"{w} × {t} mm (系数 {k})"
    vol = length_m * area                 # cm³
    mass = vol * density / 1000.0         # kg
    R = rho * length_m / area             # Ω
    return {
        "status": "success", "shape": shape, "spec": spec,
        "length_m": round(length_m, 4), "area_mm2": round(area, 6),
        "perimeter_mm": round(perim, 4), "volume_cm3": round(vol, 4),
        "mass_kg": round(mass, 4), "resistance_room_ohm": round(R, 6),
    }


# --------------------------- 2. 由电阻反算长度 ---------------------------
def calc_length(shape: str, R_target: float, rho: float, density: float,
                d: Optional[float] = None, w: Optional[float] = None,
                t: Optional[float] = None, k: float = 0.98) -> Dict[str, Any]:
    """已知目标电阻与尺寸，反推所需长度与质量。"""
    if shape == "wire":
        if not (d and d > 0):
            raise ValueError("圆丝需输入有效丝径 d (mm)")
        area = _round_area(d)
        spec = f"Ф{d} mm"
    else:
        if not (w and t and w > 0 and t > 0):
            raise ValueError("扁带需输入有效宽 w 与厚 t (mm)")
        area = _ribbon_area(w, t, k)
        spec = f"{w} × {t} mm (系数 {k})"
    if R_target <= 0:
        raise ValueError("目标电阻必须大于 0")
    L = R_target * area / rho             # m
    vol = L * area
    mass = vol * density / 1000.0
    return {
        "status": "success", "shape": shape, "spec": spec,
        "target_resistance_ohm": R_target, "area_mm2": round(area, 6),
        "length_m": round(L, 4), "volume_cm3": round(vol, 4),
        "mass_kg": round(mass, 4),
    }


# --------------------------- 3. 电参数核算 ---------------------------
def calc_electric_params(mode: str, shape: str, P_kW: float, rho: float, density: float,
                         alpha: float = 1.0, U: Optional[float] = None, R: Optional[float] = None,
                         d: Optional[float] = None, w: Optional[float] = None,
                         t: Optional[float] = None, k: float = 0.98) -> Dict[str, Any]:
    """
    给定功率与电压（mode='pu'）或功率与电阻（mode='pr'），求电阻、长度、质量、表面负荷（常温/高温）。
    mode='pu': 输入 P_kW, U；  mode='pr': 输入 P_kW, R。
    """
    if P_kW <= 0:
        raise ValueError("功率必须大于 0")
    P_W = P_kW * 1000.0
    if mode == "pu":
        if not (U and U > 0):
            raise ValueError("mode='pu' 需输入电压 U (V)")
        R_calc = U * U / P_W
        U_calc = U
    elif mode == "pr":
        if not (R and R > 0):
            raise ValueError("mode='pr' 需输入电阻 R (Ω)")
        R_calc = R
        U_calc = math.sqrt(P_W * R_calc)
    else:
        raise ValueError("mode 仅支持 'pu' 或 'pr'")

    if shape == "wire":
        if not (d and d > 0):
            raise ValueError("圆丝需输入有效丝径 d (mm)")
        area, perim = _round_area(d), _round_perim(d)
        spec = f"Ф{d} mm"
    else:
        if not (w and t and w > 0 and t > 0):
            raise ValueError("扁带需输入有效宽 w 与厚 t (mm)")
        area, perim = _ribbon_area(w, t, k), _ribbon_perim(w, t, k)
        spec = f"{w} × {t} mm (系数 {k})"

    L = R_calc * area / rho
    vol = L * area
    mass = vol * density / 1000.0
    R_high = R_calc * alpha
    P_high_kW = U_calc * U_calc / R_high / 1000.0   # 固定电压下，高温电阻变大→功率变小
    surf_cm2 = perim * L * 10.0
    SL_room = P_W / surf_cm2
    SL_high = P_high_kW * 1000.0 / surf_cm2
    return {
        "status": "success", "mode": mode, "shape": shape, "spec": spec,
        "voltage_V": round(U_calc, 4), "resistance_room_ohm": round(R_calc, 6),
        "resistance_high_ohm": round(R_high, 6),
        "length_m": round(L, 4), "volume_cm3": round(vol, 4),
        "mass_kg": round(mass, 4),
        "power_room_kW": round(P_kW, 4), "power_high_kW": round(P_high_kW, 4),
        "surface_load_room_Wcm2": round(SL_room, 4),
        "surface_load_high_Wcm2": round(SL_high, 4),
        "surface_area_cm2": round(surf_cm2, 2),
    }


# --------------------------- 4. 螺旋丝核算 ---------------------------
def account_spiral_wire(d: float, pitch: float, height_axial_mm: float, helix_outer_dia: float,
                        rho: float, density: float, alpha: float = 1.0, U: Optional[float] = None,
                        lead1_mm: float = 0.0, lead2_mm: float = 0.0,
                        bridge_mm: float = 0.0) -> Dict[str, Any]:
    """已知螺旋丝几何尺寸，求展开长度、质量、常温/高温电阻、功率、表面负荷。"""
    helix_dia = helix_outer_dia - d
    per_turn = math.sqrt((PI * helix_dia) ** 2 + pitch ** 2)
    turns = height_axial_mm / pitch
    L_mm = per_turn * turns + lead1_mm + lead2_mm + bridge_mm
    L = L_mm / 1000.0
    area, perim = _round_area(d), _round_perim(d)
    vol = L * area
    mass = vol * density / 1000.0
    R = rho * L / area
    R_high = R * alpha
    out: Dict[str, Any] = {
        "status": "success", "element": "spiral_wire",
        "wire_dia_mm": d, "pitch_mm": pitch, "height_axial_mm": height_axial_mm,
        "helix_outer_dia_mm": helix_outer_dia, "helix_dia_mm": round(helix_dia, 4),
        "turns": round(turns, 3), "area_mm2": round(area, 6),
        "length_m": round(L, 4), "volume_cm3": round(vol, 4),
        "mass_kg": round(mass, 4),
        "resistance_room_ohm": round(R, 6), "resistance_high_ohm": round(R_high, 6),
    }
    if U and U > 0:
        P_room = U * U / R / 1000.0
        P_high = U * U / R_high / 1000.0
        surf_cm2 = perim * L * 10.0
        out.update({
            "voltage_V": U,
            "power_room_kW": round(P_room, 4), "power_high_kW": round(P_high, 4),
            "surface_load_room_Wcm2": round(P_room * 1000.0 / surf_cm2, 4),
            "surface_load_high_Wcm2": round(P_high * 1000.0 / surf_cm2, 4),
            "surface_area_cm2": round(surf_cm2, 2),
        })
    return out


# --------------------------- 5. 波浪元件核算（圆丝/扁带通用） ---------------------------
def account_wavy(shape: str, rho: float, density: float, alpha: float, U: float,
                 wave_height_mm: float, bend_radius_mm: float, wave_pitch_mm: float,
                 wave_count: int, d: Optional[float] = None, w: Optional[float] = None,
                 t: Optional[float] = None, k: float = 0.98,
                 lead1_mm: float = 0.0, lead2_mm: float = 0.0,
                 bridge_mm: float = 0.0) -> Dict[str, Any]:
    """已知波浪元件几何尺寸，求展开长度、质量、常温/高温电阻、功率、表面负荷。"""
    th = d if shape == "wire" else t
    if th is None or th <= 0:
        raise ValueError("波浪元件需输入有效直径 d(圆丝) 或厚度 t(扁带)")
    bend_mid = bend_radius_mm + th / 2.0
    bend_out = bend_radius_mm + th
    arc = PI * bend_mid                         # 单侧半圆弧长
    leg = math.sqrt((wave_pitch_mm / 2.0 - 2.0 * bend_mid) ** 2 +
                    (wave_height_mm - 2.0 * bend_out) ** 2)
    per_wave = 2.0 * arc + 2.0 * leg
    L_mm = per_wave * wave_count + lead1_mm + lead2_mm + bridge_mm
    L = L_mm / 1000.0

    if shape == "wire":
        area, perim = _round_area(d), _round_perim(d)
        spec = f"Ф{d} mm"
    else:
        area, perim = _ribbon_area(w, t, k), _ribbon_perim(w, t, k)
        spec = f"{w} × {t} mm (系数 {k})"

    vol = L * area
    mass = vol * density / 1000.0
    R = rho * L / area
    R_high = R * alpha
    P_room = U * U / R / 1000.0
    P_high = U * U / R_high / 1000.0
    surf_cm2 = perim * L * 10.0
    return {
        "status": "success", "element": f"wavy_{shape}",
        "spec": spec, "wave_height_mm": wave_height_mm, "bend_radius_mm": bend_radius_mm,
        "wave_pitch_mm": wave_pitch_mm, "wave_count": wave_count,
        "per_wave_length_mm": round(per_wave, 3),
        "area_mm2": round(area, 6), "length_m": round(L, 4),
        "volume_cm3": round(vol, 4), "mass_kg": round(mass, 4),
        "resistance_room_ohm": round(R, 6), "resistance_high_ohm": round(R_high, 6),
        "voltage_V": U, "power_room_kW": round(P_room, 4), "power_high_kW": round(P_high, 4),
        "surface_load_room_Wcm2": round(P_room * 1000.0 / surf_cm2, 4),
        "surface_load_high_Wcm2": round(P_high * 1000.0 / surf_cm2, 4),
        "surface_area_cm2": round(surf_cm2, 2),
    }


# --------------------------- 6. 螺旋丝设计（逆问题） ---------------------------
def design_spiral_wire(rho: float, alpha: float, P_kW: float, U: float, target_SL: float,
                       density: float, helix_outer_dia: Optional[float] = None,
                       pitch: Optional[float] = None, D_over_d: float = 5.5,
                       S_over_d: float = 3.0) -> Dict[str, Any]:
    """已知设计功率/电压/目标表面负荷，求理论丝径、圈数、螺旋尺寸、实际表面负荷。"""
    P_W = P_kW * 1000.0
    I = P_W / U
    rho_high = rho * alpha
    s = (I * I * rho_high / target_SL) ** (1 / 3.0)
    d = 0.343 * s                              # 理论丝径 mm
    area, perim = _round_area(d), _round_perim(d)
    R = U * U / P_W
    L = R * area / rho
    helix_dia = (helix_outer_dia - d) if helix_outer_dia else D_over_d * d
    p = pitch if pitch else S_over_d * d
    per_turn = math.sqrt((PI * helix_dia) ** 2 + p ** 2)
    turns = L * 1000.0 / per_turn
    height_axial_mm = turns * p
    vol = L * area
    mass = vol * density / 1000.0
    surf_cm2 = perim * L * 10.0
    SL_actual = P_W / surf_cm2
    R_high = R * alpha
    P_high = U * U / R_high / 1000.0   # 固定电压下高温功率
    return {
        "status": "success", "element": "design_spiral_wire",
        "theoretical_dia_mm": round(d, 4),
        "area_mm2": round(area, 6), "resistance_ohm": round(R, 6),
        "length_m": round(L, 4), "helix_dia_mm": round(helix_dia, 4),
        "pitch_mm": round(p, 4), "turns": round(turns, 2),
        "height_axial_mm": round(height_axial_mm, 2),
        "mass_kg": round(mass, 4),
        "target_surface_load_Wcm2": target_SL,
        "actual_surface_load_Wcm2": round(SL_actual, 4),
        "power_high_kW": round(P_high, 4),
        "surface_load_high_Wcm2": round(P_high * 1000.0 / surf_cm2, 4),
        "ratio_D_over_d": round(helix_dia / d, 3),
        "ratio_S_over_d": round(p / d, 3),
        "note": "ratio_D_over_d 推荐 5~6，ratio_S_over_d 推荐 2~4；超出请调整螺旋外径或螺距。",
    }


# --------------------------- 7. 波浪元件设计（圆丝/扁带通用） ---------------------------
def design_wavy(shape: str, rho: float, alpha: float, P_kW: float, U: float, target_SL: float,
                density: float, width_ratio: float = 10.0, k: float = 0.98,
                wave_height_mm: Optional[float] = None, bend_radius_mm: Optional[float] = None,
                wave_pitch_mm: Optional[float] = None) -> Dict[str, Any]:
    """
    已知设计功率/电压/目标表面负荷，求理论规格（圆丝:丝径；扁带:厚/宽）。
    若提供波高/折弯半径/波距，则进一步给出每波展开长度、波数、实际表面负荷。
    """
    P_W = P_kW * 1000.0
    I = P_W / U
    rho_high = rho * alpha
    s = (I * I * rho_high / target_SL) ** (1 / 3.0)
    R = U * U / P_W

    if shape == "wire":
        d = 0.343 * s
        area, perim = _round_area(d), _round_perim(d)
        th = d
        size = {"theoretical_dia_mm": round(d, 4)}
        spec = f"Ф{d:.3f} mm"
    else:
        B = (1.0 / (20.0 * width_ratio * (width_ratio + 1.0))) ** (1 / 3.0)
        C = B * width_ratio
        thickness = B * s
        width = C * s
        area, perim = _ribbon_area(width, thickness, k), _ribbon_perim(width, thickness, k)
        th = thickness
        size = {"theoretical_thickness_mm": round(thickness, 4),
                "theoretical_width_mm": round(width, 4), "width_ratio": width_ratio}
        spec = f"{width:.3f} × {thickness:.3f} mm (宽厚比 {width_ratio})"

    L = R * area / rho
    vol = L * area
    mass = vol * density / 1000.0
    surf_cm2 = perim * L * 10.0
    SL_actual = P_W / surf_cm2
    out: Dict[str, Any] = {
        "status": "success", "element": f"design_wavy_{shape}",
        "spec": spec, "area_mm2": round(area, 6),
        "resistance_ohm": round(R, 6), "length_m": round(L, 4),
        "mass_kg": round(mass, 4), "target_surface_load_Wcm2": target_SL,
        "actual_surface_load_Wcm2": round(SL_actual, 4),
    }
    out.update(size)

    if wave_height_mm and bend_radius_mm and wave_pitch_mm:
        bend_mid = bend_radius_mm + th / 2.0
        bend_out = bend_radius_mm + th
        arc = PI * bend_mid
        leg = math.sqrt((wave_pitch_mm / 2.0 - 2.0 * bend_mid) ** 2 +
                        (wave_height_mm - 2.0 * bend_out) ** 2)
        per_wave = 2.0 * arc + 2.0 * leg
        wave_count = math.ceil(L * 1000.0 / per_wave) if per_wave > 0 else None
        out.update({
            "per_wave_length_mm": round(per_wave, 3),
            "wave_count_needed": wave_count,
            "note": "wave_count_needed 为按展开长度向上取整的近似波数；层数与排布需结合空间尺寸另行校核。",
        })
    return out
