"""IEEE 738 steady-state thermal rating calculations."""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np

FT_PER_M = 3.280839895013123
M2_PER_FT2 = 0.09290304


@dataclass(slots=True, frozen=True)
class IEEE738Inputs:
    conductor_temp_c: float
    ambient_temp_c: float
    diameter_m: float
    resistance_low_ohm_per_m: float
    resistance_high_ohm_per_m: float
    resistance_low_temp_c: float
    resistance_high_temp_c: float
    emissivity: float
    absorptivity: float
    wind_speed_mps: float
    wind_angle_deg: float
    elevation_m: float
    solar_radiation_w_per_m2: float
    wind_sheltering_factor_pct: float


@dataclass(slots=True, frozen=True)
class IEEE738Result:
    ampacity_a: float
    resistance_ohm_per_m: float
    q_conv_w_per_m: float
    q_rad_w_per_m: float
    q_solar_w_per_m: float
    wind_effective_mps: float


def _resistance_at_temp(inputs: IEEE738Inputs) -> float:
    t1 = inputs.resistance_low_temp_c
    t2 = inputs.resistance_high_temp_c
    if t2 == t1:
        return inputs.resistance_low_ohm_per_m
    ratio = (inputs.conductor_temp_c - t1) / (t2 - t1)
    return inputs.resistance_low_ohm_per_m + ratio * (
        inputs.resistance_high_ohm_per_m - inputs.resistance_low_ohm_per_m
    )


def calculate_ieee738_steady_state(inputs: IEEE738Inputs) -> IEEE738Result:
    """Return IEEE 738 steady-state ampacity using user-supplied weather inputs."""
    delta_t = max(0.0, inputs.conductor_temp_c - inputs.ambient_temp_c)
    resistance_ohm_per_m = _resistance_at_temp(inputs)
    if delta_t <= 0.0 or resistance_ohm_per_m <= 0.0:
        return IEEE738Result(
            ampacity_a=0.0,
            resistance_ohm_per_m=max(resistance_ohm_per_m, 0.0),
            q_conv_w_per_m=0.0,
            q_rad_w_per_m=0.0,
            q_solar_w_per_m=0.0,
            wind_effective_mps=0.0,
        )

    diameter_ft = max(inputs.diameter_m * FT_PER_M, 1e-9)
    temp_film_c = 0.5 * (inputs.conductor_temp_c + inputs.ambient_temp_c)
    elev_ft = max(0.0, inputs.elevation_m * FT_PER_M)

    wind_speed_effective_mps = max(
        0.0, inputs.wind_speed_mps * (1.0 - (inputs.wind_sheltering_factor_pct / 100.0))
    )
    wind_speed_ft_per_s = wind_speed_effective_mps * FT_PER_M
    wind_speed_ft_per_hr = wind_speed_ft_per_s * 3600.0

    wind_angle_rad = math.radians(max(0.0, min(90.0, inputs.wind_angle_deg)))
    k_angle = (
        1.194
        - math.cos(wind_angle_rad)
        + 0.194 * math.cos(2.0 * wind_angle_rad)
        + 0.368 * math.sin(2.0 * wind_angle_rad)
    )

    # IEEE 738 air property equations (imperial).
    mu_f = 0.00353 * ((temp_film_c + 273.0) ** 1.5) / (temp_film_c + 383.4)
    rho_f = (0.080695 - 2.901e-6 * elev_ft + 3.7e-11 * elev_ft**2) / (
        1.0 + 0.00367 * temp_film_c
    )
    k_f = 7.388e-3 + 2.279e-5 * temp_film_c - 1.343e-9 * temp_film_c**2

    reynolds = diameter_ft * rho_f * wind_speed_ft_per_hr / max(mu_f, 1e-12)
    q_c_forced_1 = k_angle * (1.01 + 1.35 * reynolds**0.52) * k_f * delta_t
    q_c_forced_2 = k_angle * 0.0754 * reynolds**0.60 * k_f * delta_t
    q_c_natural = 1.825 * (rho_f**0.5) * (diameter_ft**0.75) * (delta_t**1.25)
    q_c_w_per_ft = max(q_c_natural, q_c_forced_1, q_c_forced_2)

    q_r_w_per_ft = (
        1.656
        * diameter_ft
        * inputs.emissivity
        * (((inputs.conductor_temp_c + 273.0) / 100.0) ** 4 - ((inputs.ambient_temp_c + 273.0) / 100.0) ** 4)
    )

    solar_w_per_ft2 = max(inputs.solar_radiation_w_per_m2 * M2_PER_FT2, 0.0)
    q_s_w_per_ft = inputs.absorptivity * solar_w_per_ft2 * diameter_ft

    resistance_ohm_per_ft = resistance_ohm_per_m / FT_PER_M
    net_w_per_ft = q_c_w_per_ft + q_r_w_per_ft - q_s_w_per_ft
    ampacity = math.sqrt(max(net_w_per_ft, 0.0) / resistance_ohm_per_ft)

    return IEEE738Result(
        ampacity_a=ampacity,
        resistance_ohm_per_m=resistance_ohm_per_m,
        q_conv_w_per_m=q_c_w_per_ft * FT_PER_M,
        q_rad_w_per_m=q_r_w_per_ft * FT_PER_M,
        q_solar_w_per_m=q_s_w_per_ft * FT_PER_M,
        wind_effective_mps=wind_speed_effective_mps,
    )


def calculate_ieee738_ampacity_batch(
    *,
    conductor_temp_c: np.ndarray,
    ambient_temp_c: np.ndarray,
    wind_speed_mps: np.ndarray,
    wind_angle_deg: np.ndarray,
    solar_radiation_w_per_m2: np.ndarray,
    wind_sheltering_factor_pct: np.ndarray,
    diameter_m: float,
    resistance_low_ohm_per_m: float,
    resistance_high_ohm_per_m: float,
    resistance_low_temp_c: float,
    resistance_high_temp_c: float,
    emissivity: float,
    absorptivity: float,
    elevation_m: float,
) -> np.ndarray:
    """Vectorized IEEE 738 ampacity for large sensitivity sweeps."""
    t_c = np.asarray(conductor_temp_c, dtype=np.float64)
    t_a = np.asarray(ambient_temp_c, dtype=np.float64)
    w_mps = np.asarray(wind_speed_mps, dtype=np.float64)
    w_deg = np.asarray(wind_angle_deg, dtype=np.float64)
    q_solar = np.asarray(solar_radiation_w_per_m2, dtype=np.float64)
    shelter_pct = np.asarray(wind_sheltering_factor_pct, dtype=np.float64)

    delta_t = np.maximum(0.0, t_c - t_a)
    t_span = max(resistance_high_temp_c - resistance_low_temp_c, 1e-9)
    resistance_ohm_per_m = resistance_low_ohm_per_m + (
        ((t_c - resistance_low_temp_c) / t_span)
        * (resistance_high_ohm_per_m - resistance_low_ohm_per_m)
    )
    resistance_ohm_per_m = np.maximum(resistance_ohm_per_m, 1e-12)

    diameter_ft = max(diameter_m * FT_PER_M, 1e-12)
    temp_film_c = 0.5 * (t_c + t_a)
    elev_ft = max(0.0, elevation_m * FT_PER_M)
    wind_eff_mps = np.maximum(0.0, w_mps * (1.0 - (shelter_pct / 100.0)))
    wind_ft_per_hr = wind_eff_mps * FT_PER_M * 3600.0

    angle_rad = np.radians(np.clip(w_deg, 0.0, 90.0))
    k_angle = (
        1.194
        - np.cos(angle_rad)
        + 0.194 * np.cos(2.0 * angle_rad)
        + 0.368 * np.sin(2.0 * angle_rad)
    )

    mu_f = 0.00353 * ((temp_film_c + 273.0) ** 1.5) / (temp_film_c + 383.4)
    rho_f = (0.080695 - 2.901e-6 * elev_ft + 3.7e-11 * elev_ft**2) / (
        1.0 + 0.00367 * temp_film_c
    )
    k_f = 7.388e-3 + 2.279e-5 * temp_film_c - 1.343e-9 * temp_film_c**2

    reynolds = diameter_ft * rho_f * wind_ft_per_hr / np.maximum(mu_f, 1e-12)
    q_c_forced_1 = k_angle * (1.01 + 1.35 * (reynolds**0.52)) * k_f * delta_t
    q_c_forced_2 = k_angle * 0.0754 * (reynolds**0.60) * k_f * delta_t
    q_c_natural = 1.825 * np.sqrt(np.maximum(rho_f, 0.0)) * (diameter_ft**0.75) * (
        delta_t**1.25
    )
    q_c_w_per_ft = np.maximum(np.maximum(q_c_natural, q_c_forced_1), q_c_forced_2)

    q_r_w_per_ft = (
        1.656
        * diameter_ft
        * emissivity
        * (((t_c + 273.0) / 100.0) ** 4 - ((t_a + 273.0) / 100.0) ** 4)
    )
    q_s_w_per_ft = absorptivity * np.maximum(q_solar * M2_PER_FT2, 0.0) * diameter_ft
    resistance_ohm_per_ft = resistance_ohm_per_m / FT_PER_M
    net_w_per_ft = q_c_w_per_ft + q_r_w_per_ft - q_s_w_per_ft
    ampacity = np.sqrt(np.maximum(net_w_per_ft, 0.0) / np.maximum(resistance_ohm_per_ft, 1e-12))
    return ampacity
