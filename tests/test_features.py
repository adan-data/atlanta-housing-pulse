import pytest
import pandas as pd
import numpy as np
from src.features import build_displacement_risk_index, flag_gentrification_pressure

@pytest.fixture
def sample_df():
    rng = np.random.default_rng(0)
    n = 100
    return pd.DataFrame({
        "total_renter_hh":     rng.integers(50,  400,  n).astype(float),
        "severely_burdened_hh":rng.integers(5,   100,  n).astype(float),
        "median_income":       rng.integers(20000, 90000, n).astype(float),
        "median_rent":         rng.integers(600,  2200,  n).astype(float),
        "vacant_units":        rng.integers(0,    50,   n).astype(float),
        "total_units":         rng.integers(100,  500,  n).astype(float),
        "rent_burden_pct":     rng.uniform(0.05, 0.60, n).round(4),
        "vacancy_rate":        rng.uniform(0.01, 0.20, n).round(4),
        "rent_to_income_ratio":rng.uniform(0.10, 0.80, n).round(4),
    })

def test_dri_unit_interval(sample_df):
    df = build_displacement_risk_index(sample_df)
    assert df["displacement_risk_index"].between(0, 1).all()

def test_all_tiers_present(sample_df):
    df = build_displacement_risk_index(sample_df)
    tiers = set(df["risk_tier"].dropna().astype(str).unique())
    assert tiers == {"Low", "Moderate", "High", "Critical"}

def test_dri_positive_correlation(sample_df):
    df = build_displacement_risk_index(sample_df)
    corr = df["displacement_risk_index"].corr(df["rent_burden_pct"])
    assert corr > 0, f"Expected positive correlation, got {corr:.4f}"

def test_gentrification_flag_binary(sample_df):
    df = build_displacement_risk_index(sample_df)
    df = flag_gentrification_pressure(df)
    assert df["gentrif_pressure_flag"].isin([0, 1]).all()

def test_gentrification_flag_nonzero(sample_df):
    df = build_displacement_risk_index(sample_df)
    df = flag_gentrification_pressure(df)
    assert df["gentrif_pressure_flag"].sum() > 0
