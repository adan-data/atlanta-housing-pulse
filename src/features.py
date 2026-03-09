import pandas as pd
import numpy as np
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)


def load_data(db_path="housing_pulse.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM census_tracts", conn)
    conn.close()
    return df


def build_displacement_risk_index(df):
    weights = {
        "rent_burden_pct":     0.35,
        "rent_to_income_ratio":0.25,
        "low_vacancy_score":   0.20,
        "low_income_score":    0.20
    }
    df = df.copy()
    df["low_vacancy_score"] = 1 - df["vacancy_rate"].clip(0, 1)
    income_max = df["median_income"].quantile(0.95)
    income_min = df["median_income"].quantile(0.05)
    df["low_income_score"] = 1 - (
        (df["median_income"] - income_min) / (income_max - income_min)
    ).clip(0, 1)
    df["rent_burden_norm"] = df["rent_burden_pct"].clip(0, 1)
    rti_max = df["rent_to_income_ratio"].quantile(0.95)
    df["rti_norm"] = (df["rent_to_income_ratio"] / rti_max).clip(0, 1)
    df["displacement_risk_index"] = (
        df["rent_burden_norm"]  * weights["rent_burden_pct"] +
        df["rti_norm"]          * weights["rent_to_income_ratio"] +
        df["low_vacancy_score"] * weights["low_vacancy_score"] +
        df["low_income_score"]  * weights["low_income_score"]
    ).round(4)
    df["risk_tier"] = pd.cut(
        df["displacement_risk_index"],
        bins=[0, 0.3, 0.5, 0.7, 1.0],
        labels=["Low", "Moderate", "High", "Critical"],
        include_lowest=True
    )
    return df


def flag_gentrification_pressure(df):
    df = df.copy()
    df["gentrif_pressure_flag"] = (
        (df["median_rent"]    > df["median_rent"].quantile(0.60)) &
        (df["median_income"]  < df["median_income"].quantile(0.40)) &
        (df["rent_burden_pct"]> 0.25)
    ).astype(int)
    return df


if __name__ == "__main__":
    df   = load_data()
    df   = build_displacement_risk_index(df)
    df   = flag_gentrification_pressure(df)
    conn = sqlite3.connect("housing_pulse.db")
    df.to_sql("tracts_with_features", conn, if_exists="replace", index=False)
    conn.close()
