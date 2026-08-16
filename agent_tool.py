import sys
import json
from core.calculator import calc_resistance, reverse_solve_size
from core.element_design import (
    calc_mass, calc_length, calc_electric_params,
    account_spiral_wire, account_wavy, design_spiral_wire, design_wavy,
)
from core.alloy_db import get_alloy_props

def _resolve_mat(payload: dict):
    """从 alloy 名称或显式参数解析 rho/density/alpha。
    返回 (rho, density, alpha, alloy_standard)。alpha 缺省 1.0。"""
    alloy = payload.get("alloy")
    rho = payload.get("rho")
    density = payload.get("density")
    alpha = payload.get("alpha", 1.0)
    std = alloy
    if alloy:
        p = get_alloy_props(alloy, custom_rho=rho)
        rho = p["resistivity"] if rho is None else rho
        density = p["density"] if density is None else density
        alpha = p["temp_factor"] if (alpha is None or alpha == 1.0) and p["temp_factor"] else alpha
        std = p["alloy_standard"]
    if rho is None:
        raise ValueError("需提供 alloy 牌号或显式 rho（电阻率）")
    if density is None:
        raise ValueError("需提供 alloy 牌号或显式 density（密度 g/cm³）以计算质量")
    return rho, density, alpha, std

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "请提供 JSON 参数"}))
        return
    try:
        payload = json.loads(sys.argv[1])
        action = payload.get("action", "calc_resistance")

        if action == "calc_resistance":
            result = calc_resistance(
                alloy_input=payload.get("alloy"), shape_type=payload.get("shape_type", "wire"),
                diameter_mm=payload.get("diameter_mm"), width_mm=payload.get("width_mm"),
                thickness_mm=payload.get("thickness_mm"), shape_factor=payload.get("shape_factor", 0.97),
                custom_rho=payload.get("rho"), tolerance=payload.get("tolerance", 0.05))
        elif action == "reverse_solve":
            result = reverse_solve_size(
                target_r_per_meter=payload.get("target_r"), alloy_input=payload.get("alloy"),
                shape_type=payload.get("shape_type", "wire"), fixed_width_mm=payload.get("fixed_width_mm"),
                shape_factor=payload.get("shape_factor", 0.95), custom_rho=payload.get("rho"))
        elif action == "calc_mass":
            rho, density, alpha, std = _resolve_mat(payload)
            result = calc_mass(
                shape=payload.get("shape", "wire"), length_m=payload.get("length_m"),
                rho=rho, density=density, d=payload.get("d"), w=payload.get("w"),
                t=payload.get("t"), k=payload.get("k", 0.98))
            result["alloy"] = std
        elif action == "calc_length":
            rho, density, alpha, std = _resolve_mat(payload)
            result = calc_length(
                shape=payload.get("shape", "wire"), R_target=payload.get("R"),
                rho=rho, density=density, d=payload.get("d"), w=payload.get("w"),
                t=payload.get("t"), k=payload.get("k", 0.98))
            result["alloy"] = std
        elif action == "calc_electric_params":
            rho, density, alpha, std = _resolve_mat(payload)
            result = calc_electric_params(
                mode=payload.get("mode", "pu"), shape=payload.get("shape", "wire"),
                P_kW=payload.get("P_kW"), rho=rho, density=density, alpha=alpha,
                U=payload.get("U"), R=payload.get("R"),
                d=payload.get("d"), w=payload.get("w"), t=payload.get("t"), k=payload.get("k", 0.98))
            result["alloy"] = std
        elif action == "account_spiral_wire":
            rho, density, alpha, std = _resolve_mat(payload)
            result = account_spiral_wire(
                d=payload.get("d"), pitch=payload.get("pitch"), height_axial_mm=payload.get("height_axial_mm"),
                helix_outer_dia=payload.get("helix_outer_dia"), rho=rho, density=density, alpha=alpha,
                U=payload.get("U"), lead1_mm=payload.get("lead1_mm", 0), lead2_mm=payload.get("lead2_mm", 0),
                bridge_mm=payload.get("bridge_mm", 0))
            result["alloy"] = std
        elif action == "account_wavy_ribbon":
            rho, density, alpha, std = _resolve_mat(payload)
            result = account_wavy(
                shape="ribbon", rho=rho, density=density, alpha=alpha, U=payload.get("U"),
                wave_height_mm=payload.get("wave_height_mm"), bend_radius_mm=payload.get("bend_radius_mm"),
                wave_pitch_mm=payload.get("wave_pitch_mm"), wave_count=payload.get("wave_count"),
                w=payload.get("w"), t=payload.get("t"), k=payload.get("k", 0.98),
                lead1_mm=payload.get("lead1_mm", 0), lead2_mm=payload.get("lead2_mm", 0),
                bridge_mm=payload.get("bridge_mm", 0))
            result["alloy"] = std
        elif action == "account_wavy_round_wire":
            rho, density, alpha, std = _resolve_mat(payload)
            result = account_wavy(
                shape="wire", rho=rho, density=density, alpha=alpha, U=payload.get("U"),
                wave_height_mm=payload.get("wave_height_mm"), bend_radius_mm=payload.get("bend_radius_mm"),
                wave_pitch_mm=payload.get("wave_pitch_mm"), wave_count=payload.get("wave_count"),
                d=payload.get("d"), k=payload.get("k", 0.98),
                lead1_mm=payload.get("lead1_mm", 0), lead2_mm=payload.get("lead2_mm", 0),
                bridge_mm=payload.get("bridge_mm", 0))
            result["alloy"] = std
        elif action == "design_spiral_wire":
            rho, density, alpha, std = _resolve_mat(payload)
            result = design_spiral_wire(
                rho=rho, alpha=alpha, P_kW=payload.get("P_kW"), U=payload.get("U"),
                target_SL=payload.get("target_SL"), density=density,
                helix_outer_dia=payload.get("helix_outer_dia"), pitch=payload.get("pitch"),
                D_over_d=payload.get("D_over_d", 5.5), S_over_d=payload.get("S_over_d", 3.0))
            result["alloy"] = std
        elif action == "design_wavy_ribbon":
            rho, density, alpha, std = _resolve_mat(payload)
            result = design_wavy(
                shape="ribbon", rho=rho, alpha=alpha, P_kW=payload.get("P_kW"), U=payload.get("U"),
                target_SL=payload.get("target_SL"), density=density, width_ratio=payload.get("width_ratio", 10.0),
                k=payload.get("k", 0.98), wave_height_mm=payload.get("wave_height_mm"),
                bend_radius_mm=payload.get("bend_radius_mm"), wave_pitch_mm=payload.get("wave_pitch_mm"))
            result["alloy"] = std
        elif action == "design_wavy_round_wire":
            rho, density, alpha, std = _resolve_mat(payload)
            result = design_wavy(
                shape="wire", rho=rho, alpha=alpha, P_kW=payload.get("P_kW"), U=payload.get("U"),
                target_SL=payload.get("target_SL"), density=density,
                wave_height_mm=payload.get("wave_height_mm"), bend_radius_mm=payload.get("bend_radius_mm"),
                wave_pitch_mm=payload.get("wave_pitch_mm"))
            result["alloy"] = std
        else:
            result = {"error": f"未知 action: {action}"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
