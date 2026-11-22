# Evaluation report (SYNTHETIC DATA)

> All numbers come from synthetic data. They show the pipeline works; they are **not** real-world accuracy.

Test set: 2000 vendors, default rate 9.8%.

## Headline metrics

| model | AUC | KS | Brier |
|---|---|---|---|
| Logistic regression (decision model) | 0.692 | 0.2968 | 0.0855 |
| Gradient boosting (comparison only) | 0.6822 | 0.2849 | 0.0862 |
| Baseline rule as 0/1 | 0.6151 | - | - |
| Baseline ratio as a ranking | 0.683 | - | - |

## Against the baseline rule

Rule: **approve if monthly UPI income >= 3.0 x EMI**. It approves 71.5% with 6.92% defaults among approved.

* **Same approval rate (71.5%)**: model default rate 6.78% vs baseline 6.92% (relative reduction 2%).
* **Same default rate (6.92%)**: model approves 73.9% vs baseline 71.5% (+23 per 1,000 applicants).

* AUC gain vs the 0/1 rule: **+0.0769** (95% bootstrap CI +0.0497 to +0.1044, 1000 resamples)
* AUC gain vs ranking by the ratio alone: **+0.0091** (95% bootstrap CI -0.0097 to +0.0276, 1000 resamples)
* AUC gain gradient boosting minus logistic regression: **-0.0099** (95% bootstrap CI -0.0384 to +0.0185, 1000 resamples)

## Bands

| band | share | default rate | score range |
|---|---|---|---|
| approve | 37.0% | 3.78% | 575-662 |
| review | 43.7% | 10.64% | 535-574 |
| decline | 19.3% | 19.17% | 312-534 |

## Calibration by decile

| decile | predicted PD | observed |
|---|---|---|
| 1 | 3.58% | 0.50% |
| 2 | 4.96% | 4.00% |
| 3 | 6.03% | 5.50% |
| 4 | 7.01% | 4.50% |
| 5 | 7.99% | 10.50% |
| 6 | 9.06% | 10.00% |
| 7 | 10.36% | 12.00% |
| 8 | 12.06% | 12.00% |
| 9 | 14.91% | 17.00% |
| 10 | 23.61% | 21.50% |

## Segments by vendor type

| segment | n | defaults | default rate | AUC | approve share | flags |
|---|---|---|---|---|---|---|
| flower_seller | 179 | 21 | 11.7% | 0.7092 | 24.0% | only 21 defaults: too few to judge |
| fruit_cart | 309 | 24 | 7.8% | 0.6712 | 34.6% | only 24 defaults: too few to judge |
| kirana_shop | 304 | 29 | 9.5% | 0.7086 | 52.3% | only 29 defaults: too few to judge |
| street_food | 337 | 37 | 11.0% | 0.6814 | 43.6% | - |
| tea_stall | 363 | 36 | 9.9% | 0.7148 | 29.2% | - |
| vegetable_seller | 508 | 48 | 9.4% | 0.6953 | 35.0% | - |

## Segments by income band

| segment | n | defaults | default rate | AUC | approve share | flags |
|---|---|---|---|---|---|---|
| < Rs 15k/month | 676 | 57 | 8.4% | 0.6939 | 17.2% | - |
| Rs 15-30k | 634 | 71 | 11.2% | 0.7444 | 36.9% | - |
| Rs 30-60k | 473 | 52 | 11.0% | 0.7276 | 51.2% | - |
| >= Rs 60k | 217 | 15 | 6.9% | 0.6442 | 68.2% | only 15 defaults: too few to judge |

## Bias check: cash-heavy sellers (synthetic-only, uses a hidden trait)

| cash share | n | actual default rate | approve share | decline share |
|---|---|---|---|---|
| cash < 40% | 454 | 8.6% | 63.4% | 4.0% |
| cash 40-60% | 815 | 11.3% | 42.8% | 11.5% |
| cash > 60% | 731 | 8.8% | 14.1% | 37.5% |
