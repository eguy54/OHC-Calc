"""Streamlit frontend for OHC Calculator."""

from __future__ import annotations

import math

import streamlit as st

from conductor_library import (
    format_conductor_name,
    list_conductor_families,
    load_conductor_family,
    load_family_materials,
)
from thermal_engine import IEEE738Inputs, calculate_ieee738_steady_state


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

    return f"""
<svg width="360" height="360" viewBox="0 0 360 360" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="360" height="360" fill="#f9fafb"/>
  <rect x="10" y="{legend_y - 8}" width="340" height="{legend_h}" rx="10" fill="rgba(238,242,255,0.72)" stroke="#c7d2fe" stroke-width="1"/>
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
st.caption("Conductor setup and DLR inputs")

families = list_conductor_families()
if not families:
    st.error("No conductor datasets found in conductor_library/data/conductors.")
    st.stop()

default_idx = families.index("ACSR") if "ACSR" in families else 0
materials_map = load_family_materials()
if "selected_family" not in st.session_state:
    st.session_state["selected_family"] = families[default_idx]

with st.container(border=True):
    st.subheader("Conductor Details")

    left_col, right_col = st.columns([1.1, 0.9], gap="small")

    with left_col:
        selector_col1, selector_col2 = st.columns(2, gap="small")
        with selector_col1:
            family = st.selectbox("Type", options=families, key="selected_family")
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
            st.session_state["selected_name"] = name_options[0]

        with selector_col2:
            selected_name = st.selectbox("Name", options=name_options, key="selected_name")
        selected_row = name_to_row[selected_name]

        st.caption(
            f"Size `{selected_row.get('size', '')}` | Cond `{selected_row.get('cond_strand', '')}` | Core `{selected_row.get('core_strand', '')}`"
        )

        properties_col1, properties_col2, properties_col3 = st.columns(3, gap="small")
        with properties_col1:
            emissivity_text = st.text_input("Emissivity", value="0.7", key="emissivity_text")
        with properties_col2:
            absorptivity_text = st.text_input("Absorptivity", value="0.7", key="absorptivity_text")
        with properties_col3:
            conductors_per_phase = st.number_input(
                "# Conductors Per Phase",
                min_value=1,
                step=1,
                value=1,
                key="conductors_per_phase",
            )

        emissivity, emissivity_ok = _parse_unit_interval(emissivity_text, 0.7)
        absorptivity, absorptivity_ok = _parse_unit_interval(absorptivity_text, 0.7)
        if not emissivity_ok:
            st.warning("Emissivity must be a number between 0 and 1.")
        if not absorptivity_ok:
            st.warning("Absorptivity must be a number between 0 and 1.")
        st.caption(
            f"Using emissivity `{emissivity:.3f}` | absorptivity `{absorptivity:.3f}` | conductors/phase `{int(conductors_per_phase)}`"
        )

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

with st.container(border=True):
    st.subheader("DLR Inputs")
    dlr_col1, dlr_col2, dlr_col3 = st.columns(3, gap="small")
    with dlr_col1:
        mot_c = st.number_input("MOT (C)", value=100.0, step=1.0, key="mot_c")
        ambient_c = st.number_input("Ambient Temp (C)", value=25.0, step=1.0, key="ambient_c")
    with dlr_col2:
        windspeed_mps = st.number_input(
            "Windspeed (m/s)",
            min_value=0.0,
            value=1.0,
            step=0.1,
            key="windspeed_mps",
        )
        ghi_wm2 = st.slider(
            "Global Horizontal Irradiance (W/m2)",
            min_value=0,
            max_value=1000,
            value=1000,
            step=10,
            key="ghi_wm2",
        )
    with dlr_col3:
        wind_incidence_angle_deg = st.slider(
            "Windspeed Incidence Angle (deg)",
            min_value=0,
            max_value=90,
            value=90,
            key="perp_wind_factor_deg",
            help="0 = always parallel, 90 = always perpendicular",
        )
        wind_shelter_pct = st.slider(
            "Wind Sheltering Factor (%)",
            min_value=0,
            max_value=100,
            value=0,
            key="wind_shelter_pct",
            help="0 = open terrain, 100 = fully sheltered",
        )
    st.caption(
        f"MOT `{mot_c:.1f} C` | Wind `{windspeed_mps:.1f} m/s` | Ambient `{ambient_c:.1f} C` | GHI `{ghi_wm2} W/m2` | Angle `{wind_incidence_angle_deg} deg` | Shelter `{wind_shelter_pct}%`"
    )

    diameter_m = _to_float(selected_row.get("metal_od", "0")) * 0.0254
    r_low_ohm_per_m = _to_float(selected_row.get("low_resistance_ohm_per_mile", "0")) / 1609.344
    r_high_ohm_per_m = _to_float(selected_row.get("hi_resistance_ohm_per_mile", "0")) / 1609.344
    t_low_c = _to_float(selected_row.get("low_temp_degc", "25"))
    t_high_c = _to_float(selected_row.get("hi_temp_degc", "75"))
    if r_high_ohm_per_m <= 0:
        r_high_ohm_per_m = r_low_ohm_per_m
    if t_high_c <= t_low_c:
        t_high_c = t_low_c + 1.0

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
            wind_angle_deg=wind_incidence_angle_deg,
            elevation_m=0.0,
            solar_radiation_w_per_m2=float(ghi_wm2),
            wind_sheltering_factor_pct=float(wind_shelter_pct),
        )
    )

    out_col1, out_col2, out_col3 = st.columns(3, gap="small")
    out_col1.metric("IEEE 738 DLR (A)", f"{dlr.ampacity_a:,.1f}")
    out_col2.metric("Effective Wind (m/s)", f"{dlr.wind_effective_mps:.2f}")
    out_col3.metric("Resistance @ MOT (ohm/km)", f"{dlr.resistance_ohm_per_m * 1000:.4f}")
    st.caption(
        f"Heat terms (W/m): convection `{dlr.q_conv_w_per_m:.1f}` | radiation `{dlr.q_rad_w_per_m:.1f}` | solar `{dlr.q_solar_w_per_m:.1f}`"
    )
