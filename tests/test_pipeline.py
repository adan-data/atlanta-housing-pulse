import pytest
import pandas as pd
import numpy as np
from src.data_pipeline import clean_census_data

@pytest.fixture
def raw():
    return pd.DataFrame({
        "B25070_001E": ["100", "80", "60", "120"],
        "B25070_010E": ["30",  "20", "-1",  "40"],
        "B19013_001E": ["45000", "32000", "61000", "28000"],
        "B25058_001E": ["1200",  "950",   "1500",  "800"],
        "B25002_003E": ["10",    "5",     "20",    "8"],
        "B25002_001E": ["200",   "150",   "300",   "180"],
        "B03002_003E": ["60",    "30",    "120",   "20"],
        "B03002_001E": ["200",   "150",   "300",   "180"],
        "NAME":        ["Tract A", "Tract B", "Tract C", "Tract D"],
        "state":       ["13", "13", "13", "13"],
        "county":      ["121", "121", "089", "089"],
        "tract":       ["000100", "000200", "000300", "000400"],
        "county_name": ["Fulton", "Fulton", "DeKalb", "DeKalb"],
    })

def test_row_count(raw):
    assert len(clean_census_data(raw, year=2023)) == 4

def test_suppression_coerced(raw):
    c = clean_census_data(raw, year=2023)
    assert c["severely_burdened_hh"].isna().sum() >= 1

def test_ratios_bounded(raw):
    c = clean_census_data(raw, year=2023).dropna(subset=["rent_burden_pct", "vacancy_rate"])
    assert c["rent_burden_pct"].between(0, 1).all()
    assert c["vacancy_rate"].between(0, 1).all()

def test_geo_id_length(raw):
    assert clean_census_data(raw, year=2023)["geo_id"].str.len().eq(11).all()

def test_data_year(raw):
    c = clean_census_data(raw, year=2023)
    assert (c["data_year"] == 2023).all()
