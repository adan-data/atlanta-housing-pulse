# Atlanta Housing Pulse

**[Live Demo →](https://atlanta-housing-pulse.streamlit.app)**

Tract-level housing displacement risk system for the Atlanta metro — Census + FRED data pipeline, engineered risk index, and Prophet rent forecasting across 500+ census tracts in Fulton, DeKalb, Gwinnett, Cobb, and Clayton counties.


![alt text](image.png)





---

## What this system does

The Displacement Risk Index (DRI) identifies which census tracts are under structural housing pressure *before* crisis-stage outcomes show up in eviction filings or displacement surveys. It combines four Census-derived measures into a single score and classifies tracts into four tiers — Low, Moderate, High, and Critical — to support resource allocation decisions by city planners, nonprofit housing agencies, and CDFIs.

The system runs an end‑to‑end pipeline: pull → clean → engineer → score → forecast → monitor → surface.

---

## Key findings (2022 ACS)

> **DRI scores range from 0 to 1. Higher = greater displacement risk.**

| County   | Avg DRI | Critical Tracts | Avg Rent Burden |
|----------|---------|-----------------|-----------------|
| Clayton  | 0.630   | 31              | 29.7%           |
| Gwinnett | 0.584   | 65              | 25.3%           |
| DeKalb   | 0.568   | 56              | 27.6%           |
| Fulton   | 0.546   | 59              | 23.8%           |
| Cobb     | 0.520   | 6               | 20.3%           |


Clayton County has the highest average DRI (0.630) and highest rent burden (29.7%) —
lower median incomes and more gentrification-pressure flags per capita than any other county.

Cobb County is the clear outlier on the low end — only 6 critical tracts versus
31–65 in every other county, and the lowest avg rent burden at 20.3%.

---

## Architecture

```text
census_api / FRED_api
        │
        ▼
src/data_pipeline.py   ← pulls & cleans Census ACS + FRED series
        │
        ▼
src/features.py        ← builds DRI, risk tiers, gentrification flags
        │
        ▼
src/model.py           ← Prophet forecast (plus room for GBM validation)
        │
        ▼
src/monitor.py         ← PSI drift detection on all DRI features
        │
        ▼
dashboard/app.py       ← Streamlit: Community Overview + Technical Analysis
```

---

## DRI methodology

```text
DRI = 0.35 × rent_burden_norm
    + 0.25 × rent_to_income_norm
    + 0.20 × low_vacancy_score
    + 0.20 × low_income_score
```

| Component                          | Weight | Rationale                                                                 |
|------------------------------------|--------|---------------------------------------------------------------------------|
| Rent burden (≥50% income to rent) | 0.35   | Realized distress — households already at the breaking point             |
| Rent‑to‑income ratio              | 0.25   | Forward affordability signal — rising pressure before it becomes crisis  |
| Low vacancy score (1 − vacancy)   | 0.20   | Tight market = fewer alternatives when pressure hits; landlord leverage  |
| Low income score (inverted pct)   | 0.20   | Capacity to absorb increases — lower income = shorter runway             |

Tiers: **Low** (0.00–0.30) · **Moderate** (0.30–0.50) · **High** (0.50–0.70) · **Critical** (0.70–1.00)

Normalization uses local percentile ranges, not national benchmarks, because this is a local prioritization tool. The full weight rationale and quick sensitivity checks live in `notebooks/02_feature_engineering.ipynb`.

---

## Rent forecast

Prophet-based rent forecast with multiplicative seasonality (rent growth compounds, so seasonal bumps scale proportionally). The current version focuses on the core use cases:

- **3‑month forecasts:** Treated as actionable  
- **6‑month forecasts:** Useful for planning  
- **12–18 months:** Directional only — intervals widen and structural assumptions matter more  

---

## Data drift monitoring

Population Stability Index (PSI) runs on the key DRI features at each data refresh:

| PSI    | Status   | Action                                |
|--------|----------|---------------------------------------|
| < 0.10 | STABLE   | No action                             |
| 0.10–0.25 | MONITOR | Look into the shift before next run |
| > 0.25 | RETRAIN | Re‑evaluate model / features           |

This is the same style of PSI thresholding used in model risk monitoring in regulated finance, adapted here for housing inputs. See `src/monitor.py`.

---

## Quick start

```bash
git clone https://github.com/adan-data/atlanta-housing-pulse
cd atlanta-housing-pulse
py -m pip install -r requirements.txt

cp .env.example .env          # add your Census + FRED API keys
# then run the pipeline
py src/data_pipeline.py       # pull data into SQLite
py src/features.py            # build DRI + features
py src/model.py               # run forecasting
py src/monitor.py             # check drift

py -m streamlit run dashboard/app.py
```

---

## Run tests

```bash
py -m pytest tests/ -v
```

15 tests across pipeline cleaning, DRI construction, gentrification flagging, and PSI calculation.

---

## Known limitations

1. **ACS data lags 2–3 years.** The DRI reflects structural conditions as of the latest ACS 5‑year release. The forecast helps but can’t see tract‑level changes that haven’t hit the data yet.
2. **Tract‑level averages.** Individuals in “Low” tracts can still be in severe distress. This is a prioritization tool, not a census of at‑risk households.
3. **Weights are defensible but not unique.** A different stakeholder might reasonably weight vacancy or income differently. The current weights are documented and meant to be debated, not treated as ground truth.
4. **Gentrification flag is an early‑warning pattern**, not a verdict. It flags the structural conditions that tend to precede displacement, not a confirmed gentrification event.

---

## Project structure

```text
atlanta-housing-pulse/
├── src/
│   ├── data_pipeline.py        # Census + FRED ingestion and cleaning
│   ├── features.py             # DRI construction + flags
│   ├── model.py                # Forecasting
│   └── monitor.py              # PSI drift detection
├── dashboard/
│   └── app.py                  # Streamlit application
├── notebooks/
│   ├── 00_executive_summary.ipynb
│   ├── 01_eda.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_evaluation.ipynb
│   └── 04_forecast_analysis.ipynb
├── tests/
│   ├── test_pipeline.py
│   ├── test_features.py
│   └── test_monitor.py
├── reports/
│   └── monthly_brief_template.py
├── requirements.txt
└── .env.example
```

---

## Data sources

| Source                        | Series                                   | Coverage              |
|-------------------------------|------------------------------------------|-----------------------|
| U.S. Census Bureau ACS 5‑Year | Rent burden, income, vacancy, renters   | 2022, tract level     |
| Federal Reserve (FRED)        | Labor force, unemployment, housing CPI, mortgage rates | Recent monthly history |
| HUD Fair Market Rents         | Metro‑level rent benchmarks             | Latest available year |
