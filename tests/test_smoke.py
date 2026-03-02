from conductor_library import (
    default_catalog,
    format_conductor_name,
    get_conductor,
    load_family_materials,
    list_conductor_families,
    load_conductor_family,
)
from thermal_engine import ThermalInput, estimate_ohc


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
