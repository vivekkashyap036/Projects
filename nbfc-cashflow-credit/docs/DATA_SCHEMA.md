# Data schema

**All data produced by `vendorscore.data.synth` is synthetic.** This schema is the contract that real
lender data must meet to replace it. Only the first two tables are model inputs.

## 1. `vendors` (one row per loan)

| column | type | meaning | needed for |
|---|---|---|---|
| `vendor_id` | string | Lender's internal ID. Hashed before audit logging; never sent to the LLM. | join key |
| `vendor_type` | string | e.g. `vegetable_seller`, `tea_stall`, `kirana_shop`. Free text is fine; used for segment reporting only, **not** as a model feature. | evaluation |
| `loan_amount` | int, rupees | Principal disbursed | reporting |
| `tenure_months` | int | Loan tenure | reporting |
| `annual_rate` | float | e.g. 0.26 | reporting |
| `emi` | int, rupees | Monthly instalment. **Model feature input.** | features |
| `origination_day` | int | Day index when the loan started. Observation window = the 180 days before it. | features |
| `default_12m` | 0/1 | Default within 12 months (or within tenure if shorter). In real data: first 90+ DPD event, or the lender's own definition. | training label |
| `first_missed_day` | int, nullable | Due day of the first missed EMI. Needed only to evaluate the early-warning agent. | EWS evaluation |

## 2. `daily_upi` (one row per vendor per day)

| column | type | meaning |
|---|---|---|
| `vendor_id` | string | join key |
| `day` | int | Day index on the same clock as `origination_day`. Real data: convert dates to an integer day count. |
| `n_txn` | int | Number of UPI receipts that day |
| `inflow` | float, rupees | Total UPI receipts that day (credits only; exclude self-transfers and refunds) |

Rules:
* **A day with no row means zero inflow.** The feature code fills gaps with zeros between the first and last day supplied.
* Scoring needs **at least 90 days** (config `features.min_days`). Only the latest 180 days are used.
* Real data sources: UPI app or PSP settlement exports, or bank statements via the Account Aggregator framework, **with the vendor's consent**.

## 3. `hidden_traits` (synthetic only, never a model input)

This table exists so we can check *why* the model is right or wrong, for example whether it is biased against cash-heavy sellers.
Real lender data will not have it.

| column | meaning |
|---|---|
| `true_daily_income` | True average daily sales, cash + UPI |
| `cash_share` | Share of sales taken in cash (not visible in UPI) |
| `market_day`, `market_boost` | Weekday with a sales boost, and its size |
| `season_amp`, `trend_monthly`, `volatility` | Seasonality amplitude, monthly growth, daily noise |
| `dry_spell_rate_per_180d` | Expected number of illness / rain / closure spells per 180 days |
| `profit_margin`, `resilience` | Drivers of repayment capacity that UPI cannot show |
| `true_pd` | The probability of default the outcome was drawn from |
| `distress_onset_day`, `distress_visible_in_upi` | For defaulters: when trouble started, and whether it shows up in UPI (25% do not) |
| `temporary_dip_good_payer` | Good payers who had a temporary dip (false-alarm source for early warning) |

## 4. Shadow-mode input CSV (Phase 7)

| column | required | meaning |
|---|---|---|
| `vendor_id` | yes | joins to `daily_upi` |
| `emi` | yes | monthly instalment |
| `lender_decision` | yes | `approve` or `decline` (what the lender actually did) |
| `default_12m` | for approved loans | outcome; blank for declined loans (outcome unknown) |
| `vendor_type` | no | segment reporting |

The matching daily UPI records go in a second file (same columns as `daily_upi`), with each vendor's
window ending at their own origination.

## How the synthetic outcome is generated (for review)

`logit(PD) = b0 + 1.7*ln(EMI / true repayment capacity) + 3.0*(volatility - 0.375) + 0.35*(dry spell rate - 1.5) - 12*monthly trend - 0.55*resilience + N(0, 0.6)`

`b0` is solved so the average PD is 9.5%. True repayment capacity = true monthly sales x profit margin x share of active days.
The model never sees true sales, cash share, margin or resilience.
