import requests
import pandas as pd
import sqlite3
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

CENSUS_API_KEY = "YOUR_CENSUS_API_KEY"
FRED_API_KEY   = "YOUR_FRED_API_KEY"

ATLANTA_COUNTIES = {
    "Fulton":   "121",
    "DeKalb":   "089",
    "Gwinnett": "135",
    "Cobb":     "067",
    "Clayton":  "063",
}

STATE_FIPS = "13"


def get_census_data(year=2022):
    variables = [
        "B25070_001E", "B25070_010E", "B19013_001E",
        "B25058_001E", "B25002_003E", "B25002_001E",
        "B03002_003E", "B03002_001E", "NAME",
    ]

    all_data = []
    for county_name, county_fips in ATLANTA_COUNTIES.items():
        url = (
            f"https://api.census.gov/data/{year}/acs/acs5"
            f"?get={','.join(variables)}"
            f"&for=tract:*"
            f"&in=state:{STATE_FIPS}+county:{county_fips}"
            f"&key={CENSUS_API_KEY}"
        )
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            df   = pd.DataFrame(data[1:], columns=data[0])
            df["county_name"] = county_name
            all_data.append(df)
            logging.info(f"Pulled {len(data)-1} tracts for {county_name} County")
            time.sleep(0.5)
        except Exception as e:
            logging.error(f"Failed on {county_name}: {e}")
    if not all_data:
        raise ValueError("No census data retrieved.")
    return pd.concat(all_data, ignore_index=True)


def clean_census_data(df, year=2022):
    df = df.copy()
    numeric_cols = [
        "B25070_001E", "B25070_010E", "B19013_001E",
        "B25058_001E", "B25002_003E", "B25002_001E",
        "B03002_003E", "B03002_001E",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df[numeric_cols] = df[numeric_cols].where(df[numeric_cols] >= 0, other=pd.NA)
    df = df.rename(columns={
        "B25070_001E": "total_renter_hh",
        "B25070_010E": "severely_burdened_hh",
        "B19013_001E": "median_income",
        "B25058_001E": "median_rent",
        "B25002_003E": "vacant_units",
        "B25002_001E": "total_units",
        "B03002_003E": "white_pop",
        "B03002_001E": "total_pop",
    })
    df["rent_burden_pct"]      = (df["severely_burdened_hh"] / df["total_renter_hh"]).round(4)
    df["vacancy_rate"]         = (df["vacant_units"] / df["total_units"]).round(4)
    df["rent_to_income_ratio"] = ((df["median_rent"] * 12) / df["median_income"]).round(4)
    df["white_share"]          = (df["white_pop"] / df["total_pop"]).round(4)
    df["geo_id"]               = STATE_FIPS + df["county"].astype(str) + df["tract"].astype(str)
    df["data_year"]            = year
    df["pulled_at"]            = datetime.now().isoformat()
    return df


def get_fred_data():
    series_map = {
        "ATLA113LBSA":  "labor_force_atlanta",
        "ATLA113URN":   "unemployment_rate_atlanta",
        "CUURA319SAH":  "cpi_housing_southeast",
        "MORTGAGE30US": "mortgage_rate_30yr",
    }

    fred_data = {}
    for series_id, label in series_map.items():
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&sort_order=desc&limit=24"
            f"&api_key={FRED_API_KEY}&file_type=json"
        )
        try:
            r   = requests.get(url, timeout=30)
            r.raise_for_status()
            obs = r.json()["observations"]
            df  = pd.DataFrame(obs)[["date", "value"]]
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df  = df.dropna()
            df.columns = ["date", label]
            fred_data[label] = df
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"FRED series {series_id} failed: {e}")
    return fred_data


def save_to_db(df, table_name, db_path="housing_pulse.db"):
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    logging.info(f"Saved {len(df)} rows to '{table_name}'")


if __name__ == "__main__":
    raw   = get_census_data(year=2022)
    clean = clean_census_data(raw, year=2022)
    save_to_db(clean, "census_tracts")
    fred  = get_fred_data()
    for label, df in fred.items():
        save_to_db(df, f"fred_{label}")
