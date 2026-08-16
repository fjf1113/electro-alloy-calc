---
name: electro-alloy-calc
description: 电热合金（铁铬铝 Fe-Cr-Al、镍铬 Ni-Cr）米电阻及电热元件设计计算 Agent。覆盖圆丝/扁带/螺旋丝/波浪元件的正向米电阻、尺寸反推、质量核算、电阻反算长度、电参数核算（功率/电压/表面负荷），以及螺旋丝/波浪扁带/波浪圆丝的元件设计与核算。内置 255、1560、2080、21al6nb、HRE 等牌号自动识别，并带密度/电阻温度系数工程库。当用户咨询合金丝/带材米电阻、元件长度/质量、表面负荷、或给定功率电压反推规格时使用。
agent_created: true
---

# 电热合金米电阻 & 元件设计计算 Agent

针对铁铬铝（Fe-Cr-Al）与镍铬（Ni-Cr）合金的**米电阻**与**电热元件设计**专业计算工具。
计算逻辑全部由 Python 脚本实现，**必须实际运行脚本得到结果，不要凭记忆心算**。

---

## 1. 触发场景

- **米电阻 / 尺寸反推**：「2080 丝径 0.27 米阻多少」「255 宽 3.5 厚 0.3 扁带米阻」「21al6nb 扁丝米阻 4.25、宽 2.0，厚度要多少」。
- **质量 / 电阻核算**：「HRE Ф3.5 长 600m 多重、电阻多少」「0Cr25Al5A 30×3 扁带 300m 质量」。
- **已知电阻反算长度**：「Cr20Ni80 直径 12、电阻 0.3785Ω 需要多长」。
- **电参数核算**：「给定功率 15kW、电压 220V、丝径 5.7，求长度/质量/表面负荷」「Ni80 13.33kW 110V 丝径 3.8 的螺旋丝」。
- **螺旋丝核算**：已知丝径、螺距、螺旋高度、螺旋外径 → 展开长度、质量、常温/高温电阻、功率、表面负荷。
- **波浪元件核算**：已知波高、折弯半径、波距、波数 → 圆丝或扁带波浪元件的展开长度/质量/电阻/功率/表面负荷。
- **元件设计（逆问题）**：给定设计功率、电压、目标表面负荷 → 理论丝径/扁带厚宽、螺旋尺寸或波浪波数。

---

## 2. 牌号与材料库（自动识别）

- 牌号别名自动归一化：`255→0Cr25Al5A`、`1560→Cr15Ni60`、`2080→Cr20Ni80`、`21al6nb→0Cr21Al6Nb`、`HRE/HYZ`、`235/195/193/134/277` 等。
- 传入 `alloy` 时自动带出**常温电阻率、密度、电阻温度系数(temp_factor)、最高使用温度、推荐表面负荷上限**；也可显式用 `rho`/`density`/`alpha` 覆盖。
- 扁带经验截面系数 `k`：默认 **0.98**；米电阻场景圆丝/扁丝仍可用原系数（0.97/0.95/0.92），以 `shape_factor` 或 `k` 指定。

> 说明：`temp_factor` = 高温电阻率 / 常温电阻率（约在设计温度下的比值，参考值）；设计结果请以对应牌号标准与工况校核。

---

## 3. 固定工作流（路由逻辑）

用户提问 → 抽取槽位（牌号 / 形状 / 尺寸 / 功率 / 电压 / 电阻 / 表面负荷 / 几何）→ 按下表选 action → 运行 `agent_tool.py` → 自然语言回写。

```
[用户提问]
   │ 抽取：alloy、shape(wire/ribbon)、尺寸(d / w,t)、P、U、R、w(表面负荷)、几何
   ▼
┌──────────────┬───────────────────┬──────────────────┬────────────────────┐
│ 米电阻/尺寸  │ 质量/长度/电参数  │ 元件核算(已知几何) │ 元件设计(逆问题)    │
├──────────────┼───────────────────┼──────────────────┼────────────────────┤
│calc_resistance│ calc_mass         │ account_spiral_   │ design_spiral_wire  │
│reverse_solve │ calc_length        │   wire            │ design_wavy_ribbon  │
│              │ calc_electric_     │ account_wavy_     │ design_wavy_         │
│              │   params           │   ribbon/round    │   round_wire        │
└──────────────┴───────────────────┴──────────────────┴────────────────────┘
   │                      │                      │                    │
   └──────────────────────┴──────────────────────┴────────────────────┘
                          ▼
               [自然语言回写：关键数值 + 单位 + 工程提示]
```

**判定要点**
- 问“米阻/丝径/厚度” → `calc_resistance` / `reverse_solve`。
- 问“多重/电阻多少（已知尺寸+长度）” → `calc_mass`。
- 问“给定电阻求长度” → `calc_length`。
- 问“功率/电压 → 长度/质量/表面负荷”或“功率/电阻 → 电压/长度” → `calc_electric_params`（mode=`pu`/`pr`）。
- 给了完整螺旋/波浪几何尺寸 → `account_*`。
- 给了设计功率/电压/目标表面负荷，要反推规格 → `design_*`。

---

## 4. 各 action 调用方式

入口脚本 `agent_tool.py` 接收一段 JSON（命令行第一个参数），通过 `action` 分发。
`PYTHON` 指任意 Python 3 解释器，命令行直接写 `python` 即可。

### 4.1 米电阻（正向）`calc_resistance`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"calc_resistance\",\"alloy\":\"2080\",\"shape_type\":\"wire\",\"diameter_mm\":0.27}"
# 扁带：shape_type=ribbon + width_mm + thickness_mm + shape_factor(默认0.97)
```

### 4.2 尺寸反推（逆向）`reverse_solve`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"reverse_solve\",\"target_r\":4.25,\"alloy\":\"21al6nb\",\"shape_type\":\"ribbon\",\"fixed_width_mm\":2.0,\"shape_factor\":0.95}"
```

### 4.3 质量/电阻核算 `calc_mass`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"calc_mass\",\"alloy\":\"HRE\",\"shape\":\"wire\",\"length_m\":600,\"d\":3.5}"
# 扁带：shape=ribbon + w + t + k(默认0.98)
```

### 4.4 电阻反算长度 `calc_length`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"calc_length\",\"alloy\":\"Cr20Ni80\",\"shape\":\"wire\",\"R\":0.3785,\"d\":12}"
```

### 4.5 电参数核算 `calc_electric_params`
```bash
# 已知功率+电压：mode=pu
PYTHON ".../agent_tool.py" "{\"action\":\"calc_electric_params\",\"alloy\":\"HRE\",\"mode\":\"pu\",\"shape\":\"wire\",\"P_kW\":15,\"U\":220,\"d\":5.7}"
# 已知功率+电阻：mode=pr（返回电压、长度、质量、表面负荷）
PYTHON ".../agent_tool.py" "{\"action\":\"calc_electric_params\",\"alloy\":\"255\",\"mode\":\"pr\",\"shape\":\"ribbon\",\"P_kW\":13.33,\"R\":0.9,\"w\":20,\"t\":1.5}"
```

### 4.6 螺旋丝核算 `account_spiral_wire`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"account_spiral_wire\",\"alloy\":\"HRE\",\"d\":2.8,\"pitch\":4.5,\"height_axial_mm\":2520,\"helix_outer_dia\":15,\"U\":110}"
```

### 4.7 波浪扁带核算 `account_wavy_ribbon` / 波浪圆丝 `account_wavy_round_wire`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"account_wavy_ribbon\",\"alloy\":\"HRE\",\"U\":19.87,\"wave_height_mm\":97.5,\"bend_radius_mm\":11.25,\"wave_pitch_mm\":50,\"wave_count\":60,\"w\":25,\"t\":2.5}"
PYTHON ".../agent_tool.py" "{\"action\":\"account_wavy_round_wire\",\"alloy\":\"HRE\",\"U\":220,\"wave_height_mm\":170,\"bend_radius_mm\":27,\"wave_pitch_mm\":67,\"wave_count\":7,\"d\":6.5}"
```

### 4.8 螺旋丝设计（逆）`design_spiral_wire`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"design_spiral_wire\",\"alloy\":\"255\",\"P_kW\":12,\"U\":220,\"target_SL\":1.2,\"density\":7.1}"
# 可另传 helix_outer_dia / pitch 锁定螺旋尺寸；D_over_d(默认5.5)、S_over_d(默认3.0) 给出推荐螺旋径/螺距
```

### 4.9 波浪元件设计（逆）`design_wavy_ribbon` / `design_wavy_round_wire`
```bash
PYTHON ".../agent_tool.py" "{\"action\":\"design_wavy_ribbon\",\"alloy\":\"255\",\"P_kW\":10,\"U\":110,\"target_SL\":0.7,\"width_ratio\":10}"
PYTHON ".../agent_tool.py" "{\"action\":\"design_wavy_round_wire\",\"alloy\":\"HRE\",\"P_kW\":15,\"U\":220,\"target_SL\":1.5}"
# 再给波高/折弯半径/波距可一并算每波展开长度与所需波数
```

---

## 5. 输出约定

脚本返回 JSON（含 `status`、`alloy`、`area_mm2`、`length_m`、`mass_kg`、`resistance_room_ohm`、
`resistance_high_ohm`、`power_room_kW`/`power_high_kW`、`surface_load_room_Wcm2`/`surface_load_high_Wcm2` 等）。
把关键结果（中值米电阻/长度/质量/表面负荷、对应牌号与电阻率、常温vs高温）用自然语言回给用户即可，无需复述整个 JSON。
表面负荷偏高（如 >2.0~2.5 W/cm²，视牌号与温度）或 D/d、S/d 比值越界时，主动提示工程风险。

## 6. 工程边界（Guardrails）

- 遇还原性/渗碳/含硫气氛，优先铁铬铝；高温抗蠕变与支撑注意。
- 计算值为理论参考，实际受炉膛保温、辐射系数、元件排布影响。
- `temp_factor`、最高使用温度、推荐表面负荷为工程参考值，关键选型以牌号标准与研发复核为准。
