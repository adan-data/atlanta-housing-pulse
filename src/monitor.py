"""
src/monitor.py
==============
Purpose: Detect data drift across DRI input features using Population
Stability Index (PSI), and log results to the database for dashboard display.
"""
import pandas as pd, numpy as np, sqlite3, logging, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DB_PATH = "housing_pulse.db"
PSI_MONITOR = 0.10
PSI_RETRAIN = 0.25
FEATURES = [
    "rent_burden_pct",
    "rent_to_income_ratio",
    "vacancy_rate",
    "median_income",
    "median_rent",
    "displacement_risk_index",
    "gentrif_pressure_flag"
]

def calculate_psi(baseline, current, buckets=10):
    baseline = pd.Series(baseline).dropna().values
    current = pd.Series(current).dropna().values

    if len(baseline) == 0 or len(current) == 0:
        return 0.0

    bp = np.percentile(baseline, np.linspace(0, 100, buckets + 1))
    bp = np.unique(bp)
    if len(bp) < 3:
        return 0.0

    bp[0] = -np.inf
    bp[-1] = np.inf

    b_counts = np.histogram(baseline, bins=bp)[0]
    c_counts = np.histogram(current, bins=bp)[0]

    b_pct = b_counts / len(baseline)
    c_pct = c_counts / len(current)

    b_pct = np.where(b_pct == 0, 1e-4, b_pct)
    c_pct = np.where(c_pct == 0, 1e-4, c_pct)

    psi = float(np.sum((c_pct - b_pct) * np.log(c_pct / b_pct)))
    return round(psi, 5)

def run_drift_check(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM tracts_with_features", conn)
    conn.close()

    years = sorted(df["data_year"].unique()) if "data_year" in df.columns else []

    if len(years) >= 2:
        base = df[df["data_year"] == years[-2]]
        curr = df[df["data_year"] == years[-1]]
        split_method = f"year {years[-2]} vs {years[-1]}"
    else:
        mid = len(df) // 2
        base = df.iloc[:mid]
        curr = df.iloc[mid:]
        split_method = "index split (single year — temporal drift check unavailable)"

    logging.info("Drift check method: %s", split_method)

    results = []
    for f in FEATURES:
        if f not in df.columns:
            continue
        psi = calculate_psi(base[f], curr[f])
        status = ("STABLE" if psi < PSI_MONITOR else
                  "MONITOR" if psi < PSI_RETRAIN else
                  "RETRAIN")
        results.append({
            "feature": f,
            "psi_score": psi,
            "status": status,
            "method": split_method,
            "checked_at": datetime.now().isoformat(),
        })
        logging.info("%-35s PSI=%.4f %s", f, psi, status)

    out = pd.DataFrame(results)
    
    # Overwrite the table on every run to clear out old dummy logs
    conn = sqlite3.connect(db_path)
    out.to_sql("drift_log", conn, if_exists="replace", index=False)
    conn.close()
    
    logging.info("Drift log saved to %s", db_path)
    return out

if __name__ == "__main__":
    results = run_drift_check()
    print(results.to_string(index=False))