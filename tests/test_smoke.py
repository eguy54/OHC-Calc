from conductor_library import (
    default_catalog,
    format_conductor_name,
    get_conductor,
    load_family_materials,
    list_conductor_families,
    load_conductor_family,
)
from thermal_engine import ThermalInput, estimate_ohc
from thermal_engine.ieee738 import (
    IEEE738Inputs,
    calculate_ieee738_ampacity_batch,
    calculate_ieee738_steady_state,
)
import numpy as np


def test_smoke_estimate_ohc() -> None:
    catalog = default_catalog()
    conductor = catalog["ACSR 300"]
    result = estimate_ohc(
        ThermalInput(
            ambient_c=25.0,
            current_a=300.0,
            resistance_ohm_per_km=conductor.resistance_ohm_per_km,
        )
    )
    assert result.ohc_value > 0.0
    assert result.trace == "thermal_engine.estimate_ohc"


def test_get_conductor() -> None:
    catalog = default_catalog()
    name = next(iter(catalog))
    conductor = get_conductor(name)
    assert conductor.name == name


def test_load_extracted_family() -> None:
    families = list_conductor_families()
    assert "AAAC" in families
    rows = load_conductor_family("AAAC")
    assert len(rows) > 0
    assert "size" in rows[0]


def test_format_conductor_name() -> None:
    label = format_conductor_name(
        {"size": "795", "cond_strand": "26", "core_strand": "7", "code_word": "Drake"}
    )
    assert label == "795 26/7 Drake"


def test_family_materials_load() -> None:
    materials = load_family_materials()
    assert materials["ACSR"]["outer_material"]
    assert materials["ACSR"]["core_material"]


def test_ieee738_reference_case() -> None:
    # Reference values from IEEE 738 worked example mirrored in public implementations.
    result = calculate_ieee738_steady_state(
        IEEE738Inputs(
            conductor_temp_c=100.0,
            ambient_temp_c=40.0,
            diameter_m=1.108 * 0.0254,
            resistance_low_ohm_per_m=(8.688e-5) * 3.280839895013123,
            resistance_high_ohm_per_m=(10.120e-5) * 3.280839895013123,
            resistance_low_temp_c=25.0,
            resistance_high_temp_c=75.0,
            emissivity=0.5,
            absorptivity=0.5,
            wind_speed_mps=2.0 / 3.280839895013123,
            wind_angle_deg=90.0,
            elevation_m=0.0,
            solar_radiation_w_per_m2=95.437 / 0.09290304,
            wind_sheltering_factor_pct=0.0,
        )
    )
    q_conv_w_per_ft = result.q_conv_w_per_m / 3.280839895013123
    assert 24.0 < q_conv_w_per_ft < 26.0
    assert result.ampacity_a > 0.0


def test_ieee738_batch_matches_scalar() -> None:
    base = IEEE738Inputs(
        conductor_temp_c=100.0,
        ambient_temp_c=25.0,
        diameter_m=0.0281432,
        resistance_low_ohm_per_m=2.85e-4,
        resistance_high_ohm_per_m=3.32e-4,
        resistance_low_temp_c=25.0,
        resistance_high_temp_c=75.0,
        emissivity=0.7,
        absorptivity=0.7,
        wind_speed_mps=1.5,
        wind_angle_deg=90.0,
        elevation_m=0.0,
        solar_radiation_w_per_m2=800.0,
        wind_sheltering_factor_pct=10.0,
    )
    scalar = calculate_ieee738_steady_state(base).ampacity_a
    batch = calculate_ieee738_ampacity_batch(
        conductor_temp_c=np.array([base.conductor_temp_c]),
        ambient_temp_c=np.array([base.ambient_temp_c]),
        wind_speed_mps=np.array([base.wind_speed_mps]),
        wind_angle_deg=np.array([base.wind_angle_deg]),
        solar_radiation_w_per_m2=np.array([base.solar_radiation_w_per_m2]),
        wind_sheltering_factor_pct=np.array([base.wind_sheltering_factor_pct]),
        diameter_m=base.diameter_m,
        resistance_low_ohm_per_m=base.resistance_low_ohm_per_m,
        resistance_high_ohm_per_m=base.resistance_high_ohm_per_m,
        resistance_low_temp_c=base.resistance_low_temp_c,
        resistance_high_temp_c=base.resistance_high_temp_c,
        emissivity=base.emissivity,
        absorptivity=base.absorptivity,
        elevation_m=base.elevation_m,
    )[0]
    assert abs(batch - scalar) < 1e-9
