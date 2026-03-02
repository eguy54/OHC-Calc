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
from thermal_engine import ThermalInput, estimate_ohc


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
    px_per_cm = 44.0
    cx = 170.0
    cy = 150.0

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
    legend_x = 345
    legend_y = 28
    for idx, (fill, label) in enumerate(legend_items):
        y = legend_y + (idx * 18)
        label = label[:34] + "..." if len(label) > 37 else label
        legend_svg.append(
            f'<circle cx="{legend_x + 7}" cy="{y - 4}" r="5.5" fill="{fill}" stroke="{stroke}" stroke-width="1.1" />'
        )
        legend_svg.append(
            f'<text x="{legend_x + 18}" y="{y}" font-size="11" fill="#111827">{label}</text>'
        )

    return f"""
<svg width="100%" viewBox="0 0 540 290" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="540" height="290" fill="#f9fafb"/>
  <circle cx="{cx}" cy="{cy}" r="{border_r:.2f}" fill="none" stroke="#9ca3af" stroke-width="1.2" />
  {''.join(circles)}
  {''.join(legend_svg)}
  <line x1="{cx - border_r:.2f}" y1="258" x2="{cx + border_r:.2f}" y2="258" stroke="#111827" stroke-width="1.3" />
  <line x1="{cx - border_r:.2f}" y1="251" x2="{cx - border_r:.2f}" y2="265" stroke="#111827" stroke-width="1.3" />
  <line x1="{cx + border_r:.2f}" y1="251" x2="{cx + border_r:.2f}" y2="265" stroke="#111827" stroke-width="1.3" />
  <text x="{cx:.2f}" y="248" text-anchor="middle" font-size="16" fill="#111827">{diameter_text}</text>
</svg>
"""


st.set_page_config(page_title="OHC Calculator", layout="wide")
st.title("OHC Calculator")
st.caption("Type and conductor selection with geometry preview")

families = list_conductor_families()
if not families:
    st.error("No conductor datasets found in conductor_library/data/conductors.")
    st.stop()

default_idx = families.index("ACSR") if "ACSR" in families else 0
materials_map = load_family_materials()

left_col, right_col = st.columns([1.05, 1.0])

with left_col:
    selector_col1, selector_col2 = st.columns(2)
    with selector_col1:
        family = st.selectbox("Type", options=families, index=default_idx)
    family_rows = load_conductor_family(family)
    name_to_row: dict[str, dict[str, str]] = {}
    for idx, row in enumerate(family_rows):
        label = format_conductor_name(row)
        if label in name_to_row:
            label = f"{label} [{idx + 1}]"
        name_to_row[label] = row

    with selector_col2:
        selected_name = st.selectbox("Name", options=list(name_to_row.keys()))
    selected_row = name_to_row[selected_name]

    st.write(
        f"Size: `{selected_row.get('size', '')}` | Cond strands: `{selected_row.get('cond_strand', '')}` | Core strands: `{selected_row.get('core_strand', '')}`"
    )

    ambient_c = st.number_input("Ambient temperature (C)", value=25.0)
    current_a = st.number_input("Current (A)", value=300.0, min_value=0.0)

    res_mile = _to_float(selected_row.get("low_resistance_ohm_per_mile", "0"))
    res_km = (res_mile / 1.609344) if res_mile > 0 else 0.1

    if st.button("Run"):
        result = estimate_ohc(
            ThermalInput(
                ambient_c=ambient_c,
                current_a=current_a,
                resistance_ohm_per_km=res_km,
            )
        )
        st.metric("Estimated OHC", f"{result.ohc_value:.3f}")
        st.caption(f"Using resistance {res_km:.6f} ohm/km from family dataset.")

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

    st.markdown(
        _cross_section_svg(
            cond_count=cond_count,
            core_count=core_count,
            cond_wire_dia_in=cond_wire_dia_in,
            core_wire_dia_in=core_wire_dia_in,
            diameter_cm=diameter_cm,
            outer_label=outer_material,
            core_label=core_material,
        ),
        unsafe_allow_html=True,
    )
    if material.get("source_url"):
        st.caption(f"Material source: {material['source_url']}")
