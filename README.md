# Atlanta Housing Pulse – Displacement Risk & Rent Forecasting

**Audience:**  
- Non‑technical stakeholders (policy, leadership, recruiters)  
- Technical reviewers (data scientists, ML engineers, analytics leads)  

This project is an end‑to‑end analytics and forecasting pipeline for the **5‑county Atlanta metro** (Fulton, DeKalb, Gwinnett, Cobb, Clayton). It quantifies **displacement risk at the census‑tract level**, highlights **gentrification pressure**, and produces an **18‑month rent forecast** anchored in ACS and FRED data.[file:1][file:68]

---

## 1. Business Problem & Value

Housing affordability pressure is highly localized and often detected too late. This project addresses three core questions:

1. **Where is displacement risk highest today?**  
   A Displacement Risk Index (DRI) scores every tract from 0–1 and assigns **Low / Moderate / High / Critical** risk tiers.[file:2][file:71]
2. **Where is gentrification pressure emerging?**  
   A flag identifies tracts where **high rent, low income, and high rent burden co‑occur**, surfacing early‑stage pressure before displacement becomes visible.[file:2][file:71]
3. **What will rents look like over the next 18 months?**  
   A **Prophet** time‑series model rescaled to ACS dollar rents projects metro‑wide rent trends with uncertainty bands, supporting budgeting and policy planning.[file:3][file:70]

**Business value:**

- Prioritize **emergency rental assistance** and **NOAH preservation** where risk is most acute.[file:68]
- Align **zoning, subsidy, and CLT strategies** with tracts facing the largest forecasted rent increases.[file:68]
- Provide a **repeatable, transparent analytical workflow** that can be scheduled and audited.

---

## 2. Repository Structure

```text
.
├── data_pipeline.py          # Ingests ACS & FRED data and builds housing_pulse.db[1]
├── features.py               # Builds DRI, risk tiers, gentrification flags[2]
├── model.py                  # GBM classifier + Prophet rent forecast[3]
├── monitor.py                # PSI-based drift monitoring on DRI inputs[4]
├── check_db.py               # Lightweight sanity check for the SQLite DB[5]
├── run_notebooks.py          # Batch executor for all notebooks (consultant workflow)
├── notebooks/
│   ├── 01_Executive_Summary.ipynb     # Stakeholder-facing executive story[6]
│   ├── 02_EDA.ipynb                   # Full exploratory data analysis[7]
│   ├── 03_Feature_Engineering.ipynb   # DRI construction & feature audit[8]
│   ├── 04_Model_Evaluation.ipynb      # GBM + drift monitoring deep dive[9]
│   └── 05_Forecast_Analysis.ipynb     # Prophet forecast & scenario analysis[10]
└── requirements.txt          # Python dependencies (see below)
```

---

## 3. Data Pipeline (Technical Overview)

### 3.1 Ingestion – `data_pipeline.py`

**Sources:**  
- **ACS 5‑year** variables: rent, income, vacancy, population (B25070, B19013, B25058, B25002, B03002).[file:1]  
- **FRED** macro series: labor force, unemployment, regional housing CPI, 30‑year mortgage rates.[file:1]

**Key steps:**

1. **Census pull per year (2022–2024)**  
   - Calls the ACS API for all tracts in the 5 target counties using the `CENSUS_API_KEY` from `.env`.[file:1]  
   - Normalizes column names and enforces non‑negative numeric values.
2. **Feature‑ready base table**  
   - Derives:
     - `rent_burden_pct` (severely burdened renter HH / all renter HH)  
     - `vacancy_rate` (vacant units / total units)  
     - `rent_to_income_ratio` \(\approx \frac{12 \times \text{median\_rent}}{\text{median\_income}}\)  
     - `white_share` (non‑Hispanic white pop / total pop).[file:1]
   - Writes stacked years into `census_tracts` in `housing_pulse.db`.[file:1]
3. **FRED pull**  
   - Hits the FRED API using `FRED_API_KEY`, standardizes to `date` + single metric, and saves one table per series (e.g. `fred_cpi_housing_southeast`).[file:1]

### 3.2 Feature Engineering – `features.py`

This step turns raw ACS values into **interpretable risk signals**.[file:2]

- **Low vacancy & low income scores**  
  - `low_vacancy_score = 1 - vacancy_rate` (capped between 0 and 1).  
  - `low_income_score` scales median income between the 5th and 95th percentiles, then inverts to highlight low‑income tracts.[file:2]
- **Normalized burden & rent‑to‑income**  
  - `rent_burden_norm = rent_burden_pct` (0–1).  
  - `rti_norm` scales `rent_to_income_ratio` by the 95th percentile to avoid extreme leverage.[file:2]
- **Displacement Risk Index (DRI)**  
  \[
  \text{DRI} = 0.35 \cdot \text{rent\_burden\_norm} +
               0.25 \cdot \text{rti\_norm} +
               0.20 \cdot \text{low\_vacancy\_score} +
               0.20 \cdot \text{low\_income\_score}
  \][file:2][file:71]

- **Risk tiers**  
  - Cutpoints: [0, 0.3, 0.5, 0.7, 1.0] mapped to **Low / Moderate / High / Critical**.[file:2][file:71]
- **Gentrification pressure flag**  
  - True if:
    - `median_rent` > 60th percentile  
    - `median_income` < 40th percentile  
    - `rent_burden_pct` > 0.25  
  - Saved as `gentrif_pressure_flag`.[file:2][file:71]

Outputs are written to `tracts_with_features` in `housing_pulse.db` for use by downstream notebooks and models.[file:2]

---

## 4. Modeling & Monitoring

### 4.1 GBM Risk Classifier – `model.py` & `04_Model_Evaluation.ipynb`

**Goal:** Validate that the DRI tiers align with the underlying feature space and understand which features drive the classifier.[file:3][file:69]

- **Features**  
  - `rent_burden_pct`, `rent_to_income_ratio`, `vacancy_rate`, `median_income`, `median_rent`, `low_vacancy_score`, `low_income_score`, `gentrif_pressure_flag`.[file:3][file:69]
- **Model**  
  - `GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=4, subsample=0.8, min_samples_leaf=5)`.[file:3][file:69]
- **Evaluation** (Model Evaluation notebook)
  - Train/test split with stratification, 5‑fold stratified CV, accuracy, precision/recall/F1 per tier, confusion matrices, learning curve, and feature importance vs DRI weight comparison.[file:69]
- **Drift monitoring**  
  - `monitor.py` computes **Population Stability Index (PSI)** on core features between the last two years (or halves of data if only one year exists), classifying each as STABLE / MONITOR / RETRAIN.[file:4][file:69]

### 4.2 Prophet Rent Forecast – `model.py` & `05_Forecast_Analysis.ipynb`

**Problem:** FRED’s rent CPI is in index points, not dollars.[file:3][file:70]

- **Rescaling strategy**  
  - Use FRED CPI series (or an unemployment fallback) as a shape proxy.  
  - Compute the latest ACS median rent (2024 or fallback to 2022).  
  - Rescale CPI so the last value equals ACS median rent:
    \[
    y_\text{scaled} = \frac{\text{cpi\_value}}{\text{cpi\_latest}} \times \text{acs\_anchor}
    \][file:3][file:70]
- **Prophet configuration**  
  - `growth="linear"`, `changepoint_prior_scale=0.05`, `seasonality_mode="multiplicative"`, `interval_width=0.80`, yearly seasonality enabled, weekly/daily disabled.[file:3][file:70]
- **Outputs**  
  - 18‑month forecast with `forecast`, `lower_90`, `upper_90`, stored in `rent_forecast` and visualized with:
    - Main forecast plot
    - Components (trend, seasonality, residuals)
    - Scenario analysis (e.g., optimistic/base/pessimistic) vs income‑based affordability thresholds.[file:70]

---

## 5. Notebook Guide (Who Should Read What)

### 01_Executive_Summary.ipynb – Story for Stakeholders

- **Audience:** Non‑technical stakeholders, recruiters, leadership.  
- **Content:**  
  - KPI snapshot (tract counts, High/Critical share, median rent/income, burden).  
  - Donut chart of risk tiers and stacked bar by county.  
  - Rent affordability panel (rent by county; rent‑to‑income vs burden).  
  - 18‑month rent forecast with natural‑language interpretation.  
  - Strategic recommendations and FAQ in plain English.[file:68]

**Use this as the first link in your portfolio.**

---

### 02_EDA.ipynb – Deep Exploratory Analysis

- **Audience:** Data scientists, senior analysts, reviewers.  
- **Content:**  
  - Data quality and missingness audit.  
  - Univariate distributions (skew, mean, median) for key variables.  
  - Year‑over‑year trends in rent, income, burden by county.  
  - Correlation matrix and scatter plots vs DRI.  
  - Boxplots by county and FRED macro overlays.[file:72]

Shows you can reason about data quality, distributions, and confounders—not just “push models.”

---

### 03_Feature_Engineering.ipynb – DRI & Flags Explained

- **Audience:** Technical reviewers and policy analysts.  
- **Content:**  
  - ACS variable mapping and descriptive stats.  
  - Detailed derivation of ratios and DRI components.  
  - Weighting rationale for each component (35/25/20/20).  
  - Risk tier boundary behavior and gentrification flag rates by county.  
  - Summary table of features with intended modeling roles.[file:71]

This notebook is your **“explain my index”** artifact and is critical for trust.

---

### 04_Model_Evaluation.ipynb – Classifier & Drift

- **Audience:** ML engineers, DS leads, technical interviewers.  
- **Content:**  
  - Class balance plots and rationale for tier labels.  
  - GBM training, CV summary, test metrics.  
  - Confusion matrices (counts + normalized).  
  - Feature importance vs manual DRI weights, with divergence table.  
  - PSI drift visualization and textual summary of which features drifted and what action is recommended (monitor vs retrain).[file:69]

This demonstrates **MLOps maturity** (validation + drift monitoring), not just model building.

---

### 05_Forecast_Analysis.ipynb – Forecast & Scenario Story

- **Audience:** Both technical and semi‑technical stakeholders who care about budgeting.  
- **Content:**  
  - FRED series selection and rescaling explanation.  
  - Prophet forecast plot, components, and change‑point visualization.  
  - Scenario analysis vs affordability thresholds for median income.  
  - Forecast table ready for export or dashboard integration.[file:70]

Shows your ability to **tie forecasts back to real economic decisions**.

---

## 6. Getting Started

### 6.1 Environment Setup

1. **Clone the repo**:

   ```bash
   git clone https://github.com/<your-username>/atlanta-housing-pulse.git
   cd atlanta-housing-pulse
   ```

2. **Create and activate a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up `.env`** with your API keys:

   ```text
   CENSUS_API_KEY=your_census_key_here
   FRED_API_KEY=your_fred_key_here
   # optional
   # MLFLOW_TRACKING_URI=http://your-mlflow-server
   ```

### 6.2 Running the Full Pipeline

1. **Build the database**:

   ```bash
   python data_pipeline.py    # pulls ACS & FRED, creates housing_pulse.db
   python features.py         # builds DRI & flags into tracts_with_features
   python model.py            # trains GBM, generates rent_forecast
   python monitor.py          # runs PSI drift check into drift_log
   ```

2. **Run all notebooks non‑interactively** (e.g., before sending to a recruiter):

   ```bash
   python run_notebooks.py
   ```

   This executes, in order:

   - `01_Executive_Summary.ipynb`
   - `02_EDA.ipynb`
   - `03_Feature_Engineering.ipynb`
   - `04_Model_Evaluation.ipynb`
   - `05_Forecast_Analysis.ipynb`[code_file:32]

3. **Open notebooks in Jupyter** for interactive exploration:

   ```bash
   jupyter lab
   # or
   jupyter notebook
   ```

---

## 7. Tech Stack

- **Language:** Python 3.11+ (notebook metadata currently 3.14.x)[file:68]  
- **Data & computation:** `pandas`, `numpy`, `sqlite3`, `scikit-learn`, `prophet`[file:1][file:3][file:69][file:70]  
- **Visualization:** `matplotlib`, `seaborn`[file:68][file:72]  
- **Orchestration & monitoring:** `python-dotenv`, `requests`, custom PSI drift in `monitor.py`[file:1][file:4]  
- **Notebooks & tooling:** Jupyter, nbclient/nbformat for scripted execution.[code_file:32]

---

## 8. How to Use This as a Portfolio Piece

- Link directly to:
  - `01_Executive_Summary.ipynb` for a polished story.[file:68]
  - `03_Feature_Engineering.ipynb` + `04_Model_Evaluation.ipynb` to showcase modeling and rigor.[file:71][file:69]
- In your resume/LinkedIn:
  - Emphasize **end‑to‑end ownership**: ingestion → feature engineering → modeling → monitoring → communication.
  - Call out **displacement risk**, **gentrification**, and **rent forecasting** as applied domains.


## Data sources

| Source                        | Series                                   | Coverage              |
|-------------------------------|------------------------------------------|-----------------------|
| U.S. Census Bureau ACS 5‑Year | Rent burden, income, vacancy, renters   | 2022-2024, tract level|
| Federal Reserve (FRED)        | Labor force, unemployment, housing CPI, mortgage rates | Recent monthly history |
| HUD Fair Market Rents         | Metro‑level rent benchmarks             | Latest available year |