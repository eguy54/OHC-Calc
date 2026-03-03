"""Streamlit frontend for OHC Calculator."""

from __future__ import annotations

import math
import altair as alt
import numpy as np
import pandas as pd

import streamlit as st

from conductor_library import (
    format_conductor_name,
    list_conductor_families,
    load_conductor_family,
    load_family_materials,
)
from thermal_engine import (
    IEEE738Inputs,
    calculate_ieee738_ampacity_batch,
    calculate_ieee738_steady_state,
)


def _to_int(value: str) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_unit_interval(value: str, fallback: float) -> tuple[float, bool]:
    try:
        numeric = float(value)
    except ValueError:
        return fallback, False
    if numeric < 0.0 or numeric > 1.0:
        return fallback, False
    return numeric, True


def _parse_bounded_float(
    value: str, fallback: float, min_value: float, max_value: float
) -> tuple[float, bool]:
    try:
        numeric = float(value)
    except ValueError:
        return fallback, False
    if numeric < min_value or numeric > max_value:
        return fallback, False
    return numeric, True


def _parse_min_int(value: str, fallback: int, min_value: int) -> tuple[int, bool]:
    try:
        numeric = int(float(value))
    except ValueError:
        return fallback, False
    if numeric < min_value:
        return fallback, False
    return numeric, True


def _hex_points(count: int) -> list[tuple[float, float]]:
    if count <= 1:
        return [(0.0, 0.0)]
    span = max(2, int(math.sqrt(count)) + 3)
    points: list[tuple[float, float]] = []
    for r in range(-span, span + 1):
        for q in range(-span, span + 1):
            x = q + (r / 2.0)
            y = r * (math.sqrt(3.0) / 2.0)
            points.append((x, y))
    points.sort(key=lambda p: (p[0] ** 2 + p[1] ** 2, abs(p[1]), abs(p[0])))
    return points[:count]


def _cross_section_svg(
    cond_count: int,
    core_count: int,
    cond_wire_dia_in: float,
    core_wire_dia_in: float,
    diameter_cm: float | None,
    outer_label: str,
    core_label: str,
) -> str:
    total = max(1, cond_count + core_count)
    pts = _hex_points(total)
    max_od_cm = 6.0
    px_per_cm = 40.0
    cx = 170.0
    cy = 182.0

    cond_wire_dia_cm = cond_wire_dia_in * 2.54 if cond_wire_dia_in > 0 else 0.0
    core_wire_dia_cm = core_wire_dia_in * 2.54 if core_wire_dia_in > 0 else 0.0
    if cond_wire_dia_cm <= 0:
        cond_wire_dia_cm = 0.12
    if core_count > 0 and core_wire_dia_cm <= 0:
        core_wire_dia_cm = cond_wire_dia_cm

    cond_r_px = max(1.2, 0.5 * cond_wire_dia_cm * px_per_cm)
    core_r_px = (
        cond_r_px if core_count <= 0 else max(1.2, 0.5 * core_wire_dia_cm * px_per_cm)
    )

    od_display_cm = diameter_cm if diameter_cm and diameter_cm > 0 else max_od_cm * 0.7
    od_display_cm = min(max_od_cm, od_display_cm)
    border_r = 0.5 * od_display_cm * px_per_cm

    max_center_dist_units = max(math.hypot(x, y) for x, y in pts) if pts else 0.0
    gap_px = 0.8
    pitch_px = max(cond_r_px + core_r_px + gap_px, 2 * cond_r_px + gap_px, 2 * core_r_px + gap_px)
    required_pack_r = max_center_dist_units * pitch_px + max(cond_r_px, core_r_px)
    max_pack_r = 0.95 * border_r
    if required_pack_r > max_pack_r and required_pack_r > 0:
        scale = max_pack_r / required_pack_r
        cond_r_px *= scale
        core_r_px *= scale
        pitch_px *= scale

    core_indices = {
        idx
        for idx, _ in sorted(
            enumerate(pts), key=lambda item: item[1][0] ** 2 + item[1][1] ** 2
        )[: min(core_count, total)]
    }

    circles = []
    core_fill = "#374151"
    outer_fill = "#ffffff"
    stroke = "#111827"

    for idx, (x, y) in enumerate(pts):
        px = cx + (x * pitch_px)
        py = cy + (y * pitch_px)
        is_core = idx in core_indices and core_count > 0
        fill = core_fill if is_core else outer_fill
        wire_r_px = core_r_px if is_core else cond_r_px
        circles.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{wire_r_px:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.15" />'
        )

    diameter_text = f"{diameter_cm:.2f} cm" if diameter_cm else "n/a"
    legend_items = [
        (outer_fill, outer_label),
        (core_fill, core_label),
    ]
    if core_count <= 0:
        legend_items = [(outer_fill, outer_label)]

    legend_svg = []
    legend_x = 22
    legend_y = 14
    legend_row_h = 24
    for idx, (fill, label) in enumerate(legend_items):
        cy_legend = legend_y + 16 + (idx * legend_row_h)
        legend_svg.append(
            f'<circle cx="{legend_x + 7}" cy="{cy_legend:.2f}" r="5.5" fill="{fill}" stroke="{stroke}" stroke-width="1.1" />'
        )
        legend_svg.append(
            f'<text x="{legend_x + 18}" y="{cy_legend:.2f}" font-size="11" dominant-baseline="middle" fill="#111827">{label}</text>'
        )
    legend_h = 14 + (len(legend_items) * legend_row_h)
    dim_y = 324.0
    golf_ball_diameter_cm = 4.267
    golf_ball_r_px = 0.5 * golf_ball_diameter_cm * px_per_cm

    return f"""
<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="360" height="360" fill="#f9fafb"/>
  <rect x="10" y="{legend_y - 8}" width="340" height="{legend_h}" rx="10" fill="rgba(238,242,255,0.72)" stroke="#c7d2fe" stroke-width="1"/>
  <circle cx="{cx}" cy="{cy}" r="{golf_ball_r_px:.2f}" fill="none" stroke="#cbd5e1" stroke-width="1.0" stroke-dasharray="1.5,4" />
  <text x="{cx + golf_ball_r_px - 4:.2f}" y="{cy - golf_ball_r_px + 10:.2f}" text-anchor="end" font-size="9" fill="#94a3b8">golf ball</text>
  <circle cx="{cx}" cy="{cy}" r="{border_r:.2f}" fill="none" stroke="#9ca3af" stroke-width="1.2" />
  {''.join(circles)}
  {''.join(legend_svg)}
  <line x1="{cx - border_r:.2f}" y1="{dim_y:.2f}" x2="{cx + border_r:.2f}" y2="{dim_y:.2f}" stroke="#111827" stroke-width="1.3" />
  <line x1="{cx - border_r:.2f}" y1="{dim_y - 9:.2f}" x2="{cx - border_r:.2f}" y2="{dim_y + 9:.2f}" stroke="#111827" stroke-width="1.3" />
  <line x1="{cx + border_r:.2f}" y1="{dim_y - 9:.2f}" x2="{cx + border_r:.2f}" y2="{dim_y + 9:.2f}" stroke="#111827" stroke-width="1.3" />
  <text x="{cx:.2f}" y="{dim_y - 12:.2f}" text-anchor="middle" font-size="16" fill="#111827">{diameter_text}</text>
</svg>
"""


st.set_page_config(page_title="OHC Calculator", layout="wide")
st.title("OHC Calculator")
st.markdown(
    """
<style>
div.block-container {
  padding-top: 2.4rem;
  padding-bottom: 1.2rem;
  padding-left: 0;
  padding-right: 0;
  width: min(1220px, calc(100% - 2.4rem));
  margin-left: auto;
  margin-right: auto;
}
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stHorizontalBlock"]) {gap: 0.6rem;}
div[data-testid="stMarkdownContainer"] p {margin-bottom: 0.35rem;}
div[data-testid="stTextInput"] {margin-bottom: 0.35rem;}
</style>
""",
    unsafe_allow_html=True,
)

families = list_conductor_families()
if not families:
    st.error("No conductor datasets found in conductor_library/data/conductors.")
    st.stop()

default_idx = families.index("ACSR") if "ACSR" in families else 0
materials_map = load_family_materials()
if "selected_family" not in st.session_state:
    st.session_state["selected_family"] = families[default_idx]

with st.container(border=True):
    st.subheader("Line Setup")

    left_col, right_col = st.columns([1.1, 0.9], gap="small")

    with left_col:
        selector_col1, selector_col2 = st.columns(2, gap="small")
        with selector_col1:
            family = st.selectbox(
                "Type",
                options=families,
                key="selected_family",
                help="Conductor family/type (for example ACSR, AAC, AAAC).",
            )
        family_rows = load_conductor_family(family)
        name_to_row: dict[str, dict[str, str]] = {}
        for idx, row in enumerate(family_rows):
            label = format_conductor_name(row)
            if label in name_to_row:
                label = f"{label} [{idx + 1}]"
            name_to_row[label] = row

        name_options = list(name_to_row.keys())
        if ("selected_name" not in st.session_state) or (
            st.session_state["selected_name"] not in name_options
        ):
            if family == "ACSR":
                drake = next(
                    (name for name in name_options if "795 26/7 Drake" in name),
                    None,
                )
                st.session_state["selected_name"] = drake or name_options[0]
            else:
                st.session_state["selected_name"] = name_options[0]

        with selector_col2:
            selected_name = st.selectbox(
                "Name",
                options=name_options,
                key="selected_name",
                help="Specific conductor from the selected type.",
            )
        selected_row = name_to_row[selected_name]

        properties_col1, properties_col2, properties_col3 = st.columns(3, gap="small")
        with properties_col1:
            emissivity_text = st.text_input(
                "Emissivity",
                value="0.7",
                key="emissivity_text",
                help="Surface emissivity. Valid range: 0 to 1.",
            )
        with properties_col2:
            absorptivity_text = st.text_input(
                "Absorptivity",
                value="0.7",
                key="absorptivity_text",
                help="Solar absorptivity. Valid range: 0 to 1.",
            )
        with properties_col3:
            conductors_per_phase_text = st.text_input(
                "# Conductors Per Phase",
                value="1",
                key="conductors_per_phase_text",
                help="Bundle count per phase. Integer >= 1.",
            )

        emissivity, emissivity_ok = _parse_unit_interval(emissivity_text, 0.7)
        absorptivity, absorptivity_ok = _parse_unit_interval(absorptivity_text, 0.7)
        if not emissivity_ok:
            st.warning("Emissivity must be a number between 0 and 1.")
        if not absorptivity_ok:
            st.warning("Absorptivity must be a number between 0 and 1.")
        conductors_per_phase, conductors_ok = _parse_min_int(
            conductors_per_phase_text, fallback=1, min_value=1
        )
        if not conductors_ok:
            st.warning("# Conductors Per Phase must be an integer >= 1.")

        setup_col1, setup_col2, setup_col3 = st.columns(3, gap="small")
        with setup_col1:
            mot_text = st.text_input(
                "MOT (C)",
                value="100",
                key="mot_text",
                help="Maximum operating temperature. Valid range: 50 to 200 C.",
            )
        with setup_col2:
            line_angle_text = st.text_input(
                "Wind Angle (deg)",
                value="90",
                key="line_angle_text",
                help="Wind incidence angle to conductor axis. Valid range: 0 to 90 deg (0=parallel, 90=perpendicular).",
            )
        with setup_col3:
            wind_shelter_text = st.text_input(
                "Wind Sheltering Factor (%)",
                value="0",
                key="wind_shelter_text",
                help="Terrain sheltering. Valid range: 0 to 100% (0=open terrain, 100=fully sheltered).",
            )
        mot_c, mot_ok = _parse_bounded_float(mot_text, fallback=100.0, min_value=50.0, max_value=200.0)
        line_angle_deg, angle_ok = _parse_bounded_float(
            line_angle_text, fallback=90.0, min_value=0.0, max_value=90.0
        )
        wind_shelter_pct, shelter_ok = _parse_bounded_float(
            wind_shelter_text, fallback=0.0, min_value=0.0, max_value=100.0
        )
        if not mot_ok:
            st.warning("MOT must be a number between 50 and 200 C.")
        if not angle_ok:
            st.warning("Wind Angle must be a number between 0 and 90 deg.")
        if not shelter_ok:
            st.warning("Wind Sheltering Factor must be a number between 0 and 100%.")

    with right_col:
        material = materials_map.get(family, {})
        outer_material = material.get("outer_material", "Outer layer")
        core_material = material.get("core_material", "Core")
        cond_count = _to_int(selected_row.get("cond_strand", "0"))
        core_count = _to_int(selected_row.get("core_strand", "0"))
        cond_wire_dia_in = _to_float(selected_row.get("cond_wire_dia", "0"))
        core_wire_dia_in = _to_float(selected_row.get("core_wire_dia", "0"))
        diameter_in = _to_float(selected_row.get("metal_od", "0"))
        diameter_cm = diameter_in * 2.54 if diameter_in > 0 else None

        svg_markup = _cross_section_svg(
            cond_count=cond_count,
            core_count=core_count,
            cond_wire_dia_in=cond_wire_dia_in,
            core_wire_dia_in=core_wire_dia_in,
            diameter_cm=diameter_cm,
            outer_label=outer_material,
            core_label=core_material,
        )
        st.markdown(
            f'<div style="width: 360px; max-width: 360px;">{svg_markup}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)

diameter_m = _to_float(selected_row.get("metal_od", "0")) * 0.0254
r_low_ohm_per_m = _to_float(selected_row.get("low_resistance_ohm_per_mile", "0")) / 1609.344
r_high_ohm_per_m = _to_float(selected_row.get("hi_resistance_ohm_per_mile", "0")) / 1609.344
t_low_c = _to_float(selected_row.get("low_temp_degc", "25"))
t_high_c = _to_float(selected_row.get("hi_temp_degc", "75"))
if r_high_ohm_per_m <= 0:
    r_high_ohm_per_m = r_low_ohm_per_m
if t_high_c <= t_low_c:
    t_high_c = t_low_c + 1.0

with st.container(border=True):
    st.subheader("Single DLR / Static Rating")
    amb_col1, amb_col2, amb_col3, amb_col4 = st.columns([1.0, 1.0, 1.2, 0.9], gap="small")
    with amb_col1:
        ambient_text = st.text_input(
            "Ambient Temp (C)",
            value="25",
            key="ambient_text",
            help="Ambient air temperature. Valid range: -20 to 50 C.",
        )
    with amb_col2:
        windspeed_text = st.text_input(
            "Windspeed (m/s)",
            value="1",
            key="windspeed_text",
            help="Wind speed magnitude. Valid range: 0 to 10 m/s.",
        )
    with amb_col3:
        ghi_text = st.text_input(
            "Global Horizontal Irradiance (W/m2)",
            value="1000",
            key="ghi_text",
            help="Solar irradiance input. Valid range: 0 to 1000 W/m2.",
        )
    ambient_c, ambient_ok = _parse_bounded_float(
        ambient_text, fallback=25.0, min_value=-20.0, max_value=50.0
    )
    windspeed_mps, wind_ok = _parse_bounded_float(
        windspeed_text, fallback=1.0, min_value=0.0, max_value=10.0
    )
    ghi_wm2, ghi_ok = _parse_bounded_float(
        ghi_text, fallback=1000.0, min_value=0.0, max_value=1000.0
    )
    if not ambient_ok:
        st.warning("Ambient Temp must be a number between -20 and 50 C.")
    if not wind_ok:
        st.warning("Windspeed must be a number between 0 and 10 m/s.")
    if not ghi_ok:
        st.warning("GHI must be a number between 0 and 1000 W/m2.")

    dlr = calculate_ieee738_steady_state(
        IEEE738Inputs(
            conductor_temp_c=mot_c,
            ambient_temp_c=ambient_c,
            diameter_m=max(diameter_m, 1e-6),
            resistance_low_ohm_per_m=max(r_low_ohm_per_m, 1e-9),
            resistance_high_ohm_per_m=max(r_high_ohm_per_m, 1e-9),
            resistance_low_temp_c=t_low_c,
            resistance_high_temp_c=t_high_c,
            emissivity=emissivity,
            absorptivity=absorptivity,
            wind_speed_mps=windspeed_mps,
            wind_angle_deg=line_angle_deg,
            elevation_m=0.0,
            solar_radiation_w_per_m2=float(ghi_wm2),
            wind_sheltering_factor_pct=float(wind_shelter_pct),
        )
    )
    with amb_col4:
        st.metric("DLR (A)", f"{dlr.ampacity_a:,.0f}")

with st.container(border=True):
    st.subheader("Sensitivity Analysis")
    st.caption("Default sweep ranges (10 even steps each): Ambient -20 to 50 C, Windspeed 0 to 5 m/s, GHI 0 to 1,000 W/m2.")

    step_index = np.arange(11, dtype=np.int64)
    amb_steps = np.linspace(-20.0, 50.0, 11, dtype=np.float64)
    wind_steps = np.linspace(0.0, 5.0, 11, dtype=np.float64)
    ghi_steps = np.linspace(0.0, 1000.0, 11, dtype=np.float64)

    amb_curve = calculate_ieee738_ampacity_batch(
        conductor_temp_c=np.full_like(amb_steps, mot_c),
        ambient_temp_c=amb_steps,
        wind_speed_mps=np.full_like(amb_steps, windspeed_mps),
        wind_angle_deg=np.full_like(amb_steps, line_angle_deg),
        solar_radiation_w_per_m2=np.full_like(amb_steps, ghi_wm2),
        wind_sheltering_factor_pct=np.full_like(amb_steps, wind_shelter_pct),
        diameter_m=max(diameter_m, 1e-6),
        resistance_low_ohm_per_m=max(r_low_ohm_per_m, 1e-9),
        resistance_high_ohm_per_m=max(r_high_ohm_per_m, 1e-9),
        resistance_low_temp_c=t_low_c,
        resistance_high_temp_c=t_high_c,
        emissivity=emissivity,
        absorptivity=absorptivity,
        elevation_m=0.0,
    )
    wind_curve = calculate_ieee738_ampacity_batch(
        conductor_temp_c=np.full_like(wind_steps, mot_c),
        ambient_temp_c=np.full_like(wind_steps, ambient_c),
        wind_speed_mps=wind_steps,
        wind_angle_deg=np.full_like(wind_steps, line_angle_deg),
        solar_radiation_w_per_m2=np.full_like(wind_steps, ghi_wm2),
        wind_sheltering_factor_pct=np.full_like(wind_steps, wind_shelter_pct),
        diameter_m=max(diameter_m, 1e-6),
        resistance_low_ohm_per_m=max(r_low_ohm_per_m, 1e-9),
        resistance_high_ohm_per_m=max(r_high_ohm_per_m, 1e-9),
        resistance_low_temp_c=t_low_c,
        resistance_high_temp_c=t_high_c,
        emissivity=emissivity,
        absorptivity=absorptivity,
        elevation_m=0.0,
    )
    ghi_curve = calculate_ieee738_ampacity_batch(
        conductor_temp_c=np.full_like(ghi_steps, mot_c),
        ambient_temp_c=np.full_like(ghi_steps, ambient_c),
        wind_speed_mps=np.full_like(ghi_steps, windspeed_mps),
        wind_angle_deg=np.full_like(ghi_steps, line_angle_deg),
        solar_radiation_w_per_m2=ghi_steps,
        wind_sheltering_factor_pct=np.full_like(ghi_steps, wind_shelter_pct),
        diameter_m=max(diameter_m, 1e-6),
        resistance_low_ohm_per_m=max(r_low_ohm_per_m, 1e-9),
        resistance_high_ohm_per_m=max(r_high_ohm_per_m, 1e-9),
        resistance_low_temp_c=t_low_c,
        resistance_high_temp_c=t_high_c,
        emissivity=emissivity,
        absorptivity=absorptivity,
        elevation_m=0.0,
    )

    amb_grid, wind_grid, ghi_grid = np.meshgrid(amb_steps, wind_steps, ghi_steps, indexing="ij")
    hist_ampacity = calculate_ieee738_ampacity_batch(
        conductor_temp_c=np.full(amb_grid.size, mot_c, dtype=np.float64),
        ambient_temp_c=amb_grid.ravel(),
        wind_speed_mps=wind_grid.ravel(),
        wind_angle_deg=np.full(amb_grid.size, line_angle_deg, dtype=np.float64),
        solar_radiation_w_per_m2=ghi_grid.ravel(),
        wind_sheltering_factor_pct=np.full(amb_grid.size, wind_shelter_pct, dtype=np.float64),
        diameter_m=max(diameter_m, 1e-6),
        resistance_low_ohm_per_m=max(r_low_ohm_per_m, 1e-9),
        resistance_high_ohm_per_m=max(r_high_ohm_per_m, 1e-9),
        resistance_low_temp_c=t_low_c,
        resistance_high_temp_c=t_high_c,
        emissivity=emissivity,
        absorptivity=absorptivity,
        elevation_m=0.0,
    )

    hist_counts, hist_edges = np.histogram(hist_ampacity, bins=30)
    hist_df = pd.DataFrame(
        {
            "rating_amps": np.round(hist_edges[:-1], 0),
            "count": hist_counts,
        }
    )

    line_df = pd.DataFrame(
        {
            "step_index": step_index,
            "Wind": wind_curve,
            "Temp": amb_curve,
            "GHI": ghi_curve,
        }
    )
    line_long = line_df.melt(
        id_vars=["step_index"], value_vars=["Wind", "Temp", "GHI"], var_name="Series", value_name="rating_amps"
    )
    line_chart = (
        alt.Chart(line_long)
        .mark_line(strokeWidth=2.5)
        .encode(
            x=alt.X(
                "step_index:Q",
                title="Step Index",
                axis=alt.Axis(values=list(range(11)), tickMinStep=1),
            ),
            y=alt.Y("rating_amps:Q", title="Rating (Amps)"),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Wind", "Temp", "GHI"],
                    range=["#2563eb", "#dc2626", "#f59e0b"],
                ),
                legend=alt.Legend(
                    orient="top-left",
                    title=None,
                    fillColor="rgba(255,255,255,0.72)",
                    strokeColor="#d1d5db",
                    cornerRadius=6,
                    padding=8,
                    symbolStrokeWidth=3,
                ),
            ),
        )
        .properties(height=325)
    )
    hist_chart = (
        alt.Chart(hist_df)
        .mark_bar(color="#64748b")
        .encode(
            x=alt.X("rating_amps:Q", title="Rating (Amps)", axis=alt.Axis(format=".0f")),
            y=alt.Y("count:Q", title="Count"),
            tooltip=[
                alt.Tooltip("rating_amps:Q", title="Rating (A)", format=".0f"),
                alt.Tooltip("count:Q", title="Count"),
            ],
        )
        .properties(height=325)
    )

    static_hist_rule = alt.Chart(
        pd.DataFrame({"x": [dlr.ampacity_a]})
    ).mark_rule(color="#6b7280", strokeDash=[4, 4], size=1.5).encode(x="x:Q")
    static_hist_label = alt.Chart(
        pd.DataFrame(
            {
                "x": [dlr.ampacity_a],
                "y": [float(hist_df["count"].max()) if len(hist_df) else 0.0],
                "label": ["Static Rating"],
            }
        )
    ).mark_text(color="#6b7280", dx=6, dy=-6, align="left", fontSize=10).encode(
        x="x:Q", y="y:Q", text="label:N"
    )

    static_line_rule = alt.Chart(
        pd.DataFrame({"y": [dlr.ampacity_a]})
    ).mark_rule(color="#6b7280", strokeDash=[4, 4], size=1.5).encode(y="y:Q")
    static_line_label = alt.Chart(
        pd.DataFrame({"x": [0], "y": [dlr.ampacity_a], "label": ["Static Rating"]})
    ).mark_text(color="#6b7280", dx=6, dy=-6, align="left", fontSize=10).encode(
        x="x:Q", y="y:Q", text="label:N"
    )

    plot_col1, plot_col2 = st.columns(2, gap="small")
    with plot_col1:
        st.altair_chart(hist_chart + static_hist_rule + static_hist_label, use_container_width=True)
    with plot_col2:
        st.altair_chart(line_chart + static_line_rule + static_line_label, use_container_width=True)
