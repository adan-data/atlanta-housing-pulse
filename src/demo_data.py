"""
src/demo_data.py
Generates realistic synthetic Atlanta metro data for the live demo.
Auto-called by dashboard/app.py when housing_pulse.db is absent.

County parameters are calibrated to 2022 ACS public summary statistics.
Clayton County is structurally different by design — higher rent burden,
lower incomes — mirroring its real-world housing market conditions.
Gwinnett has the tightest vacancy, consistent with rapid suburban growth.
"""
import sqlite3, numpy as np, pandas as pd, os, sys

COUNTY_PARAMS = {
    "Fulton":  dict(n=140,income_mu=68000,income_sd=28000,rent_mu=1480,rent_sd=380,burden_mu=0.28,burden_sd=0.10,vac_mu=0.072,vac_sd=0.025),
    "DeKalb":  dict(n=110,income_mu=58000,income_sd=24000,rent_mu=1290,rent_sd=310,burden_mu=0.31,burden_sd=0.11,vac_mu=0.068,vac_sd=0.022),
    "Gwinnett":dict(n=115,income_mu=72000,income_sd=22000,rent_mu=1390,rent_sd=290,burden_mu=0.24,burden_sd=0.09,vac_mu=0.058,vac_sd=0.018),
    "Cobb":    dict(n=100,income_mu=76000,income_sd=26000,rent_mu=1420,rent_sd=320,burden_mu=0.22,burden_sd=0.08,vac_mu=0.055,vac_sd=0.017),
    "Clayton": dict(n=55, income_mu=42000,income_sd=14000,rent_mu=1150,rent_sd=220,burden_mu=0.38,burden_sd=0.12,vac_mu=0.090,vac_sd=0.030),
}
FIPS = {"Fulton":"121","DeKalb":"089","Gwinnett":"135","Cobb":"067","Clayton":"063"}


def generate_census_tracts(seed=42):
    rng = np.random.default_rng(seed); rows = []; t = 1
    for county, p in COUNTY_PARAMS.items():
        n = p["n"]; fips = FIPS[county]
        income  = np.clip(rng.normal(p["income_mu"],p["income_sd"],n),18000,160000)
        rent    = np.clip(rng.normal(p["rent_mu"],  p["rent_sd"],  n),500,3200)
        units   = rng.integers(80,620,n)
        vac     = np.clip(rng.normal(p["vac_mu"],   p["vac_sd"],   n),0.01,0.22)
        renter  = rng.integers(40,480,n)
        burden  = np.clip(rng.normal(p["burden_mu"],p["burden_sd"],n),0.03,0.72)
        pop     = rng.integers(300,5500,n)
        white   = (pop * np.clip(rng.normal(0.42,0.25,n),0.03,0.95)).astype(int)
        for i in range(n):
            rows.append({"geo_id":f"13{fips}{t:06d}","NAME":f"Census Tract {t:04d}, {county} County, Georgia",
                "county_name":county,"state":"13","county":fips,"tract":f"{t:06d}",
                "total_renter_hh":int(renter[i]),"severely_burdened_hh":int(renter[i]*burden[i]),
                "median_income":float(round(income[i])),"median_rent":float(round(rent[i])),
                "vacant_units":int(units[i]*vac[i]),"total_units":int(units[i]),
                "white_pop":int(white[i]),"total_pop":int(pop[i]),
                "rent_burden_pct":round(float(burden[i]),4),"vacancy_rate":round(float(vac[i]),4),
                "rent_to_income_ratio":round(float(rent[i]*12/income[i]),4),
                "white_share":round(float(white[i]/pop[i]),4),
                "data_year":2022,"pulled_at":"2026-01-15T00:00:00"})
            t += 1
    return pd.DataFrame(rows)


def generate_fred_series(seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2025-12-01",periods=36,freq="MS").strftime("%Y-%m-%d").tolist()
    return {
        "fred_cpi_housing_southeast":    pd.DataFrame({"date":dates,"cpi_housing_southeast":[round(280+i*0.9+rng.normal(0,0.4),2) for i in range(36)]}),
        "fred_unemployment_rate_atlanta": pd.DataFrame({"date":dates,"unemployment_rate_atlanta":[round(max(1.5,4.1+rng.normal(0,0.3)),2) for _ in range(36)]}),
        "fred_mortgage_rate_30yr":        pd.DataFrame({"date":dates,"mortgage_rate_30yr":[round(max(2.0,6.8+i*0.01+rng.normal(0,0.15)),3) for i in range(36)]}),
    }


def generate_rent_forecast(seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start="2026-01-01",periods=18,freq="MS").strftime("%Y-%m-%d").tolist()
    rows = []
    for i,d in enumerate(dates):
        pt = 1480+i*16+rng.normal(0,12)
        rows.append({"date":d,"forecast":round(pt),"lower_90":round(pt-(45+i*8)),"upper_90":round(pt+(45+i*8)),"generated_at":"2026-01-15T00:00:00"})
    return pd.DataFrame(rows)


def seed_demo_db(db_path="housing_pulse.db"):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from features import build_displacement_risk_index, flag_gentrification_pressure
    conn = sqlite3.connect(db_path)
    df_raw = generate_census_tracts()
    df_raw.to_sql("census_tracts", conn, if_exists="replace", index=False)
    df_feat = flag_gentrification_pressure(build_displacement_risk_index(df_raw))
    df_feat.to_sql("tracts_with_features", conn, if_exists="replace", index=False)
    for table, df in generate_fred_series().items():
        df.to_sql(table, conn, if_exists="replace", index=False)
    generate_rent_forecast().to_sql("rent_forecast", conn, if_exists="replace", index=False)
    pd.DataFrame([{"feature":f,"psi_score":round(0.02+i*0.009,4),"status":"STABLE","checked_at":"2026-01-15T00:00:00"}
                  for i,f in enumerate(["rent_burden_pct","rent_to_income_ratio","vacancy_rate","median_income","median_rent","displacement_risk_index"])]
    ).to_sql("drift_log", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Demo DB seeded — {len(df_feat)} tracts across {df_feat['county_name'].nunique()} counties.")

if __name__ == "__main__":
    seed_demo_db()
