"""Extract conductor-family sheets from the legacy XLS workbook into CSV."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

CONDUCTOR_SHEETS = [
    "HD Copper",
    "AAAC",
    "AAC",
    "ACAR",
    "ACCC",
    "ACCR",
    "ACSSTW",
    "ACSR",
    "AACSR",
    "AACTW",
    "ACSS",
    "ACSRTW",
]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _clean_header(value: object, fallback: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    text = text.replace("˚", "deg")
    text = text.replace("°", "deg")
    text = text.replace("Ω", "ohm")
    text = text.replace("/", "_per_")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return text or fallback


def extract_sheet(workbook: Path, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
    header_row = raw.iloc[1].tolist()

    columns = ["display_name", "code_word"]
    for idx in range(2, raw.shape[1]):
        columns.append(_clean_header(header_row[idx], f"col_{idx}"))

    data = raw.iloc[2:].copy()
    data.columns = columns
    data = data[data["size"].notna()].copy()
    data = data.dropna(axis=1, how="all")
    data.insert(0, "family", sheet_name)
    for redundant in ("display_name", "col_19"):
        if redundant in data.columns:
            data = data.drop(columns=[redundant])
    for col in data.columns:
        data[col] = data[col].map(lambda value: "" if pd.isna(value) else str(value).strip())
    return data.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to .xls workbook")
    parser.add_argument(
        "--output-dir",
        default="conductor_library/data/conductors",
        help="Output directory for generated CSV files",
    )
    args = parser.parse_args()

    workbook = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, str]] = []
    for sheet in CONDUCTOR_SHEETS:
        df = extract_sheet(workbook, sheet)
        slug = _slugify(sheet)
        out_path = output_dir / f"{slug}.csv"
        df.to_csv(out_path, index=False)
        manifest_rows.append(
            {
                "family": sheet,
                "file": out_path.name,
                "records": str(len(df)),
            }
        )
        print(f"Exported {sheet}: {len(df)} rows -> {out_path}")

    pd.DataFrame(manifest_rows).to_csv(output_dir / "manifest.csv", index=False)
    print(f"Wrote manifest: {output_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
