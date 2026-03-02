"""Conductor and material data primitives."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConductorSpec:
    name: str
    resistance_ohm_per_km: float


def default_catalog() -> dict[str, ConductorSpec]:
    """Seed catalog for early development and wiring tests."""
    entries = [
        ConductorSpec(name="ACSR 300", resistance_ohm_per_km=0.094),
        ConductorSpec(name="AAAC 300", resistance_ohm_per_km=0.102),
        ConductorSpec(name="AAC 300", resistance_ohm_per_km=0.109),
    ]
    return {item.name: item for item in entries}


def get_conductor(name: str) -> ConductorSpec:
    """Lookup helper for UI/services."""
    catalog = default_catalog()
    if name not in catalog:
        raise KeyError(f"Unknown conductor: {name}")
    return catalog[name]
