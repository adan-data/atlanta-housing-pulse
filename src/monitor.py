"""
src/monitor.py
==============
Purpose: Detect data drift across DRI input features using Population
Stability Index (PSI), and log results to the database for dashboard display.

WHY PSI?
---------
PSI is the industry standard for model input monitoring in regulated
environments (SR 11-7, OCC model risk guidance). It was chosen over
simpler tests like mean-shift or KS test for three reasons:

1. Distributional sensitivity: PSI detects changes in the shape of a
   distribution, not just the mean. A feature can have the same mean
   but a very different spread or skew — PSI catches this, a t-test
   does not.

2. Interpretability: PSI produces a single scalar that maps directly
   to an action (stable / monitor / retrain). No p-value interpretation
   needed — thresholds are operationally defined.

3. Industry standard: The same thresholds are used in bank internal
   model validation for retail credit scorecards. Using them here makes
   the methodology immediately recognizable to anyone with financial
   services or model risk management background.

PSI THRESHOLDS
---------------
PSI < 0.10  STABLE  — distribution unchanged, no action required
0.10-0.25   MONITOR — meaningful shift, investigate before next release
PSI > 0.25  RETRAIN — significant distributional change, model outputs
                       are unreliable, retraining required

These thresholds follow SR 11-7 model validation standards used by banks
for retail credit model monitoring.

PSI FORMULA
------------
PSI = sum((actual_pct - expected_pct) * ln(actual_pct / expected_pct))

where distributions are binned into deciles. Small cells are floored at
1e-4 to avoid log(0) errors.

HOW BASELINE IS CONSTRUCTED
-----------------------------
In production with multiple ACS years, the baseline would be the prior
year's distribution. With a single year of data (the current case),
the dataset is split in half by index — the first half serves as baseline,
the second as current. This detects within-dataset heterogeneity rather
than temporal drift, and is clearly labeled as such in the log output.
This approach is replaced automatically when multi-year data is available.
"""
import pandas as pd, numpy as np, sqlite3, logging, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_PATH     = "housing_pulse.db"
PSI_MONITOR = 0.10
PSI_RETRAIN = 0.25
FEATURES    = [
    "rent_burden_pct",
    "rent_to_income_ratio",
    "vacancy_rate",
    "median_income",
    "median_rent",
    "displacement_risk_index",
]


def calculate_psi(baseline, current, buckets=10):
    """
    Compute PSI between two distributions using equal-width decile bins.

    Why deciles (10 buckets)?
    10 buckets is the standard in credit risk PSI calculations. Fewer buckets
    miss distributional nuance; more buckets produce unstable estimates when
    sample sizes are small (as with census tract data).

    Floor of 1e-4 prevents log(0) without materially affecting the PSI value
    — any bin with true zero frequency is vanishingly rare in practice.
    """
    baseline = pd.Series(baseline).dropna().values
    current  = pd.Series(current).dropna().values

    if len(baseline) == 0 or len(current) == 0:
        return 0.0

    bp = np.percentile(baseline, np.linspace(0, 100, buckets + 1))
    bp = np.unique(bp)
    if len(bp) < 3:
        return 0.0

    bp[0]  = -np.inf
    bp[-1] =  np.inf

    b_counts = np.histogram(baseline, bins=bp)[0]
    c_counts = np.histogram(current,  bins=bp)[0]

    b_pct = b_counts / len(baseline)
    c_pct = c_counts / len(current)

    b_pct = np.where(b_pct == 0, 1e-4, b_pct)
    c_pct = np.where(c_pct == 0, 1e-4, c_pct)

    psi = float(np.sum((c_pct - b_pct) * np.log(c_pct / b_pct)))
    return round(psi, 5)


def run_drift_check(db_path=DB_PATH):
    """
    Load feature data, construct baseline/current splits, compute PSI,
    classify status, and write results to drift_log table.
    """
    conn = sqlite3.connect(db_path)
    df   = pd.read_sql("SELECT * FROM tracts_with_features", conn)
    conn.close()

    years = sorted(df["data_year"].unique()) if "data_year" in df.columns else []

    if len(years) >= 2:
        base         = df[df["data_year"] == years[-2]]
        curr         = df[df["data_year"] == years[-1]]
        split_method = f"year {years[-2]} vs {years[-1]}"
    else:
        mid          = len(df) // 2
        base         = df.iloc[:mid]
        curr         = df.iloc[mid:]
        split_method = "index split (single year — temporal drift check unavailable)"

    logging.info("Drift check method: %s", split_method)

    results = []
    for f in FEATURES:
        if f not in df.columns:
            continue
        psi    = calculate_psi(base[f], curr[f])
        status = ("STABLE"  if psi < PSI_MONITOR else
                  "MONITOR" if psi < PSI_RETRAIN else
                  "RETRAIN")
        results.append({
            "feature":    f,
            "psi_score":  psi,
            "status":     status,
            "method":     split_method,
            "checked_at": datetime.now().isoformat(),
        })
        logging.info("%-35s PSI=%.4f %s", f, psi, status)

    out  = pd.DataFrame(results)
    conn = sqlite3.connect(db_path)
    out.to_sql("drift_log", conn, if_exists="append", index=False)
    conn.close()
    logging.info("Drift log saved to %s", db_path)
    return out


if __name__ == "__main__":
    results = run_drift_check()
    print(results.to_string(index=False))
