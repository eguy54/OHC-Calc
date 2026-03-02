"""Thermal engine public API."""

from .core import ThermalInput, ThermalResult, estimate_ohc
from .ieee738 import (
    IEEE738Inputs,
    IEEE738Result,
    calculate_ieee738_ampacity_batch,
    calculate_ieee738_steady_state,
)

__all__ = [
    "ThermalInput",
    "ThermalResult",
    "estimate_ohc",
    "IEEE738Inputs",
    "IEEE738Result",
    "calculate_ieee738_ampacity_batch",
    "calculate_ieee738_steady_state",
]
