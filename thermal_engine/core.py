"""Core thermal calculations.

Keep this layer pure Python and independent from UI/data concerns.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class ThermalInput:
    ambient_c: float
    current_a: float
    resistance_ohm_per_km: float


@dataclass(slots=True)
class ThermalResult:
    ohc_value: float
    notes: str
    trace: str


def estimate_ohc(inputs: ThermalInput) -> ThermalResult:
    """Minimal placeholder equation for OHC.

    Replace this with validated domain equations when available.
    """
    joule_term = inputs.current_a**2 * inputs.resistance_ohm_per_km
    normalized = joule_term / 10000.0
    ohc = max(0.0, normalized + (inputs.ambient_c / 100.0))
    return ThermalResult(
        ohc_value=ohc,
        notes="Placeholder formula: (I^2 * R / 10000) + ambient/100",
        trace="thermal_engine.estimate_ohc",
    )
