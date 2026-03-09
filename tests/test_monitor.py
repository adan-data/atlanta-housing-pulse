import numpy as np
import pytest
from src.monitor import calculate_psi

PSI_STABLE   = 0.10
PSI_MONITOR  = 0.10
PSI_RETRAIN  = 0.35

rng = np.random.default_rng(42)

def test_identical_stable():
    data = rng.normal(0, 1, 500)
    psi = calculate_psi(data, data)
    assert psi < PSI_STABLE, f"Identical arrays should be STABLE, got {psi:.4f}"

def test_large_shift_retrain():
    baseline = rng.normal(0, 1, 500)
    current  = rng.normal(5, 1, 500)
    psi = calculate_psi(baseline, current)
    assert psi > PSI_RETRAIN, f"Large shift should trigger RETRAIN, got {psi:.4f}"

def test_moderate_drift_monitor():
    baseline = rng.normal(0, 1, 500)
    current  = rng.normal(0.25, 1.05, 500)
    psi = calculate_psi(baseline, current)
    assert PSI_MONITOR <= psi <= PSI_RETRAIN, f"Expected MONITOR zone, got {psi:.4f}"

def test_nan_tolerance():
    baseline = np.array([1.0, 2.0, np.nan, 3.0, 4.0] * 100)
    current  = np.array([1.1, 2.1, np.nan, 3.1, 4.1] * 100)
    psi = calculate_psi(baseline, current)
    assert isinstance(psi, float)
    assert psi >= 0

def test_returns_float():
    a = rng.normal(0, 1, 200)
    b = rng.normal(0, 1, 200)
    assert isinstance(calculate_psi(a, b), float)

