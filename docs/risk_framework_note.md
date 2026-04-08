# DRI and Financial Risk Modeling — Structural Parallels

This note documents how the Displacement Risk Index maps onto frameworks familiar from financial risk modeling.

## DRI as a credit-scoring analog

Consumer credit models and the DRI are solving structurally similar problems: both attempt to quantify the probability that a unit (household vs. borrower) will experience a negative outcome (displacement vs. default) from observable signals measured before the outcome occurs.

| Financial credit concept | DRI equivalent |
|--------------------------|----------------|
| Debt-to-income ratio | Rent burden (housing cost as share of income) |
| Probability of default (PD) | Displacement Risk Index score |
| Collateral cushion | Vacancy rate (ability to find alternatives) |
| Loan-to-value ratio | Rent-to-income ratio (structural affordability) |
| Risk-tiered pricing | Four-tier DRI classification |

## PSI and SR 11-7 alignment

The PSI-based drift monitoring in `src/monitor.py` directly implements the model validation approach described in the Federal Reserve's SR 11-7 guidance on model risk management. The same thresholds (PSI < 0.10 stable, 0.10–0.25 monitor, > 0.25 retrain) are used in bank internal model validation for retail credit scorecards.

The practical implication: a data scientist moving from this project to a financial services model validation role would encounter the same conceptual framework, just applied to income verification models or fraud detection systems rather than housing displacement.

### Out-of-Time (OOT) Temporal Validation
Initially built on a single cross-section of data, the pipeline now supports true **Out-of-Time (OOT) validation** by stacking 2022, 2023, and 2024 ACS data. The PSI drift monitor evaluates temporal distribution shifts (e.g., 2023 vs 2024) rather than synthetic within-sample splits. This mirrors the strict OOT testing requirements banks use to ensure models remain robust across changing macroeconomic conditions.

## Additive scorecard structure

The DRI is a linear weighted scorecard — the same architecture used in FICO score construction and most regulatory-compliant retail credit models. Linear scorecards are preferred in regulated environments not because they are the most accurate model type (they often aren't), but because they are interpretable, auditable, and defensible to regulators. A GBM or neural network with higher predictive accuracy would be harder to explain to a fair lending examiner or a city council member.

The GBM in `src/model.py` is run *alongside* the scorecard as a validation tool, not as a replacement — which is precisely how many financial institutions use advanced ML models: they build them to check and calibrate their interpretable production models, not to replace them.