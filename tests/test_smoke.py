from conductor_library import default_catalog, get_conductor
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
