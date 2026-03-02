"""Streamlit frontend for OHC Calculator."""

from conductor_library import default_catalog, get_conductor
from thermal_engine import ThermalInput, estimate_ohc

import streamlit as st


st.set_page_config(page_title="OHC Calculator", layout="centered")
st.title("OHC Calculator - E2E Hello World")
st.caption("Frontend -> Thermal Engine -> Conductor Library")
st.write(
    "This page proves all three layers are wired before business logic and full UI."
)

catalog = default_catalog()
conductor_name = st.selectbox("Conductor", options=sorted(catalog.keys()))
ambient_c = st.number_input("Ambient temperature (C)", value=25.0)
current_a = st.number_input("Current (A)", value=300.0, min_value=0.0)

if st.button("Run End-to-End"):
    conductor = get_conductor(conductor_name)
    payload = ThermalInput(
        ambient_c=ambient_c,
        current_a=current_a,
        resistance_ohm_per_km=conductor.resistance_ohm_per_km,
    )
    result = estimate_ohc(payload)

    st.success("End-to-end call succeeded.")
    st.metric("Estimated OHC", f"{result.ohc_value:.3f}")
    st.write(result.notes)
    st.json(
        {
            "frontend": "frontend/app.py",
            "conductor_library": {
                "selected_name": conductor.name,
                "resistance_ohm_per_km": conductor.resistance_ohm_per_km,
            },
            "thermal_engine": {
                "trace": result.trace,
                "ohc_value": result.ohc_value,
            },
        }
    )
