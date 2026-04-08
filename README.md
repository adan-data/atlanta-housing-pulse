# Atlanta Housing Pulse – Displacement Risk & Rent Forecasting

Atlanta Housing Pulse is an end-to-end housing analytics project for the 5-county Atlanta core: **Fulton, DeKalb, Gwinnett, Cobb, and Clayton**. It combines ACS and FRED data to measure **displacement risk at the census-tract level**, flag **gentrification pressure**, evaluate a **risk classification model**, monitor **data drift**, and produce an **18-month rent forecast**.

This project is designed for both:
- **Non-technical stakeholders** — policy teams, nonprofits, city leadership, recruiters.
- **Technical reviewers** — data scientists, ML engineers, analytics leads.

---

## Why this project matters

Housing pressure is local, uneven, and often detected too late. This project helps answer three practical questions:

1. **Where is displacement risk highest right now?**
2. **Which tracts show early gentrification pressure?**
3. **How might rents change over the next 18 months?**

The result is a workflow that supports both **decision-making** and **technical review**:
- tract-level risk scoring,
- county-level comparison,
- model validation,
- drift monitoring,
- forward-looking rent forecasting,
- and stakeholder-ready notebooks and dashboarding.

---

## What’s included

### Core pipeline
- **`data_pipeline.py`** — pulls ACS and FRED data and builds `housing_pulse.db`
- **`features.py`** — creates the Displacement Risk Index (DRI), risk tiers, and gentrification flags
- **`model.py`** — trains a Gradient Boosting classifier and generates a Prophet-based rent forecast
- **`monitor.py`** — calculates Population Stability Index (PSI) for drift monitoring

### Notebooks
- **`notebooks/01_Executive_Summary.ipynb`** — non-technical business summary
- **`notebooks/02_EDA.ipynb`** — exploratory data analysis
- **`notebooks/03_Feature_Engineering.ipynb`** — DRI construction and rationale
- **`notebooks/04_Model_Evaluation.ipynb`** — classifier validation and drift review
- **`notebooks/05_Forecast_Analysis.ipynb`** — rent forecast and scenarios

### Dashboard
- **`dashboard/app.py`** — Streamlit dashboard powered by `housing_pulse.db`

### Tests
- **`tests/test_pipeline.py`**
- **`tests/test_features.py`**
- **`tests/test_monitor.py`**

---

## Repository structure

```text
atlanta-housing-pulse/
├── housing_pulse.db
├── requirements.txt
├── README.md
├── run_notebooks.py
├── dashboard/
│   └── app.py
├── notebooks/
│   ├── 01_Executive_Summary.ipynb
│   ├── 02_EDA.ipynb
│   ├── 03_Feature_Engineering.ipynb
│   ├── 04_Model_Evaluation.ipynb
│   ├── 05_Forecast_Analysis.ipynb
│   └── 01_exec_affordability.jpg
├── src/
│   ├── __init__.py
│   ├── data_pipeline.py
│   ├── features.py
│   ├── model.py
│   ├── monitor.py
│   └── demo_data.py
└── tests/
    ├── test_pipeline.py
    ├── test_features.py
    └── test_monitor.py
```

---

## Data sources

| Source | Purpose |
|---|---|
| **U.S. Census Bureau ACS 5-Year** | tract-level rent, income, vacancy, renter burden, and demographic inputs |
| **FRED** | macroeconomic context including unemployment, labor force, housing CPI, and mortgage rates |
| **HUD benchmarks** | external context for rent interpretation and policy framing |

---

## Methodology

### 1. Data ingestion
The pipeline collects ACS tract-level data for the 5 target counties across multiple years and stores the cleaned results in SQLite. It also pulls supporting macroeconomic time series from FRED.

### 2. Feature engineering
The project derives tract-level indicators such as:
- `rent_burden_pct`
- `vacancy_rate`
- `rent_to_income_ratio`
- `low_vacancy_score`
- `low_income_score`

### 3. Displacement Risk Index (DRI)
The DRI is a weighted score from 0 to 1:

- **35%** rent burden
- **25%** rent-to-income ratio
- **20%** low vacancy
- **20%** low income

```text
DRI = 0.35 * rent_burden_norm
    + 0.25 * rti_norm
    + 0.20 * low_vacancy_score
    + 0.20 * low_income_score
```

Risk tiers are assigned as:

- **Low**: 0.00–0.30
- **Moderate**: 0.30–0.50
- **High**: 0.50–0.70
- **Critical**: 0.70–1.00

### 4. Gentrification pressure flag
A tract is flagged when:
- median rent is above the 60th percentile,
- median income is below the 40th percentile,
- and rent burden is above 25%.

This is intended as an early-warning indicator of displacement pressure.

### 5. Model evaluation
A **Gradient Boosting Classifier** is trained to predict risk tiers from the engineered features. The model is evaluated with:
- stratified train/test split,
- 5-fold cross-validation,
- precision / recall / F1,
- confusion matrices,
- feature importances,
- learning curves.

### 6. Drift monitoring
Population Stability Index (PSI) is used to detect shifts in key features over time. Each feature is classified as:
- **STABLE**
- **MONITOR**
- **RETRAIN**

### 7. Forecasting
A **Prophet** model is used to generate an 18-month rent forecast. FRED series are rescaled to ACS rent levels so the final forecast is expressed in dollars rather than index points.

---

## Notebook guide

### 01. Executive Summary
Best for:
- recruiters,
- non-technical stakeholders,
- portfolio review.

Includes:
- KPI summary,
- risk tier charts,
- county-level highlights,
- affordability story,
- forecast summary,
- plain-English recommendations.

### 02. EDA
Best for:
- analysts,
- technical reviewers,
- interview walkthroughs.

Includes:
- data quality checks,
- univariate distributions,
- county comparisons,
- trends over time,
- correlation analysis.

### 03. Feature Engineering
Best for:
- explaining the DRI,
- showing reasoning behind the scoring framework,
- demonstrating analytical transparency.

Includes:
- variable definitions,
- normalization logic,
- weighting rationale,
- risk tier construction,
- gentrification flag review.

### 04. Model Evaluation
Best for:
- ML engineers,
- data science interviews,
- technical portfolio review.

Includes:
- model training,
- cross-validation,
- classification performance,
- confusion matrices,
- feature importance analysis,
- PSI drift monitoring.

### 05. Forecast Analysis
Best for:
- stakeholders interested in planning and budgeting,
- technical reviewers who want forecasting detail.

Includes:
- rent series preparation,
- rescaling logic,
- Prophet forecast,
- confidence intervals,
- scenario analysis.

---

## Streamlit dashboard

The Streamlit dashboard reads directly from **`housing_pulse.db`** and presents two views:

### Community Overview
For planners, nonprofits, and non-technical users:
- critical tract count,
- high-risk tract count,
- average rent burden,
- gentrification flags,
- tract-level income vs. rent chart,
- county-level risk distribution,
- top 10 highest-risk tracts,
- rent forecast.

### Technical Analysis
For reviewers and data practitioners:
- DRI distribution,
- feature correlation heatmap,
- DRI methodology table,
- PSI drift chart,
- county summary table.

Run it with:

```bash
streamlit run dashboard/app.py
```

---

## Key results

This project highlights the real affordability pressure across the Atlanta core counties and shows where risk is concentrated.

### Median rent by county

![Median rent by county](./notebooks/01_exec_affordability.jpg)

The chart shows that Gwinnett has the highest median rent at $1,714, followed by Cobb at $1,652, Fulton at $1,645, DeKalb at $1,435, and Clayton at $1,198.

### Affordability stress

![Affordability stress — RTI vs. severe burden](./notebooks/01_exec_affordability.jpg)

The scatter plot shows that many tracts fall near or above the 30% affordability threshold, with higher displacement risk generally appearing where rent-to-income pressure and severe burden rise together.

These visuals support the core story of the project: affordability pressure is uneven, county-specific, and tied to tract-level vulnerability.

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/adan-data/atlanta-housing-pulse.git
cd atlanta-housing-pulse
```

### 2. Create a virtual environment

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Create a `.env` file

```text
CENSUS_API_KEY=your_census_api_key
FRED_API_KEY=your_fred_api_key
MLFLOW_TRACKING_URI=optional
```

---

## Running the full pipeline

From the repo root:

```bash
python data_pipeline.py
python features.py
python model.py
python monitor.py
```

If your source files live under `src/`, use the matching paths.

---

## Running the notebooks

To execute all notebooks in sequence:

```bash
python run_notebooks.py
```

Or open them interactively:

```bash
jupyter lab
```

---

## Running tests

```bash
pytest
```

The tests validate:
- census cleaning behavior,
- DRI construction and tiering,
- gentrification flag logic,
- PSI drift thresholds.

---

## Tech stack

- **Python**
- **pandas / numpy**
- **scikit-learn**
- **Prophet**
- **SQLite**
- **matplotlib / seaborn / plotly**
- **Streamlit**
- **pytest**
- **Jupyter**

---

## Portfolio value

This project demonstrates:
- end-to-end analytical workflow design,
- feature engineering for an applied policy problem,
- interpretable scoring methodology,
- classification model evaluation,
- forecast modeling,
- drift monitoring,
- executive communication through notebooks and dashboarding.

If you are reviewing this project as a recruiter or hiring manager, the best starting points are:

1. `notebooks/01_Executive_Summary.ipynb`
2. `dashboard/app.py`
3. `notebooks/04_Model_Evaluation.ipynb`

---

## Notes

- The dashboard is configured to use **`housing_pulse.db`** directly.
- The notebooks and charts are intended to be portfolio-ready and presentation-friendly.
- If deploying publicly, avoid committing secrets; use `.env` locally and deployment secrets in the hosting platform.

---

## Future improvements

- Add tract-level mapping with GeoJSON
- Add model retraining automation
- Add county-specific forecast drilldowns
- Add CI for notebook execution and tests
- Add cloud deployment health checks

