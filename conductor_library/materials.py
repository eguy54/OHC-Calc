"""Conductor and material data primitives."""

import csv
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "conductors"
MATERIALS_FILE = Path(__file__).resolve().parent / "data" / "conductor_family_materials.csv"


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


def list_conductor_families() -> list[str]:
    """List available conductor data families from extracted CSV files."""
    if not DATA_DIR.exists():
        return []
    manifest = DATA_DIR / "manifest.csv"
    if manifest.exists():
        with manifest.open(newline="", encoding="utf-8") as f:
            return [row["family"] for row in csv.DictReader(f)]
    families = []
    for path in sorted(DATA_DIR.glob("*.csv")):
        if path.name != "manifest.csv":
            families.append(path.stem.upper().replace("_", " "))
    return families


def load_conductor_family(family: str) -> list[dict[str, str]]:
    """Load one extracted conductor family CSV."""
    filename = family.lower().replace(" ", "_") + ".csv"
    csv_path = DATA_DIR / filename
    if not csv_path.exists():
        raise FileNotFoundError(f"No extracted family CSV found: {csv_path}")
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def format_conductor_name(row: dict[str, str]) -> str:
    """Build UI name label: size cond/core code_word."""
    def normalize_token(token: str) -> str:
        text = token.strip()
        if not text:
            return ""
        try:
            num = float(text)
            if num.is_integer():
                return str(int(num))
        except ValueError:
            return text
        return text

    size = normalize_token(row.get("size", ""))
    cond = normalize_token(row.get("cond_strand", ""))
    core = normalize_token(row.get("core_strand", ""))
    code = row.get("code_word", "").strip()
    strand = cond
    if core:
        strand = f"{cond}/{core}" if cond else core
    label = " ".join(part for part in [size, strand, code] if part)
    return label or size or code or "Unknown conductor"


def load_family_materials() -> dict[str, dict[str, str]]:
    """Load material composition metadata keyed by family."""
    if not MATERIALS_FILE.exists():
        return {}
    with MATERIALS_FILE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {row["family"]: row for row in rows}
