# OHC Calculator

OHC Calculator is intentionally split into three layers:

1. Frontend: Streamlit app in `frontend/`
2. Thermal Engine: pure Python calculations in `thermal_engine/`
3. Conductor Library: data lookup in `conductor_library/`

The current app is an end-to-end "hello world" that proves those layers talk to each other.

## Conductor datasets from spreadsheet

The legacy workbook can be converted into app-ready CSV tables under
`conductor_library/data/conductors/`.

Run:

```powershell
.\.venv\Scripts\python scripts\extract_conductor_sheets.py --input "C:\Users\The Twos\Downloads\314877432-Oht-Cond-Rating-Spreadsheet.xls"
```

This exports:
- `aaac.csv`, `aac.csv`, `acar.csv`, etc.
- `manifest.csv` with family/file/record counts

Runtime helpers:
- `list_conductor_families()`
- `load_conductor_family("AAAC")`
- `format_conductor_name(row)` for UI labels like `795 26/7 Drake`
- `load_family_materials()` from `conductor_library/data/conductor_family_materials.csv`

## Local run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run frontend/app.py
```

In the UI, click `Run End-to-End`. You should see:
- A computed OHC metric from `thermal_engine`
- A JSON payload that includes values sourced from `conductor_library`

## Push to GitHub

```powershell
git init
git add .
git commit -m "Initial OHC Calculator E2E scaffold"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

## Deploy to Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Click `New app`.
3. Select your repo and branch (`main`).
4. Set main file path to `frontend/app.py`.
5. Deploy.

This repo includes `requirements.txt` with `-e .`, so Streamlit Cloud installs your local packages (`thermal_engine`, `conductor_library`) automatically.
