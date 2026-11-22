# Phase reports

**All results are on synthetic data and are not real-world accuracy.** Each phase ends with its limitations and open questions.
Re-generate everything with `make all && make test`.

---

## Phase 1: Synthetic data

**What was built:** `vendorscore.data.synth`, which generates 8,000 vendors across 6 types, with 180 observation days plus 365 performance days of daily `(day, n_txn, inflow)`, and loan terms (amount, tenure, rate, EMI). Each vendor has hidden traits: true income, cash share, market-day boost, seasonality, trend, volatility, dry spells (illness, rain, closure), profit margin and resilience. Outcomes are drawn from the **true** repayment capacity and traits plus noise. Defaulters go through a distress period before their first missed EMI, and 25% of those periods are invisible in UPI. 15% of good payers have a temporary dip. The schema is in [`DATA_SCHEMA.md`](DATA_SCHEMA.md).

**Result:** default rate 9.78%, with type rates from 7.7% (kirana) to 11.3% (tea stall). Median UPI income is 4.6 times the EMI.

**Tests:** schema, hidden traits never in model tables, consistency (`n_txn = 0` means `inflow = 0`), default rate in range, missed-payment dates, EMI formula, determinism.

**Limitations and open questions**
* Every distribution (income, cash share, dry spells, the outcome equation) is my assumption. Real data will differ, and the conclusions may change.
* Loan sizing is simulated as a field officer's noisy view of true income. Real sizing rules would change the EMI-to-income relationship.
* Open question: what default definition does the lender use (90+ DPD, write-off, first missed EMI)?

## Phase 2: Features and score

**What was built:** five features: log(UPI income / EMI), weekly variability (open weeks only), longest dry spell, share of active days (days not inside a closure of 2+ days), and recent trend (last 30 days vs the 60 days before). The main model is an L2 logistic regression, with C chosen by 5-fold CV and each coefficient bounded to its expected sign. The score is 300-900, with 600 at 20:1 odds and +40 points doubling the odds. Bands come from config: approve ≥ 575, review 535-574, decline < 535. Reason codes are bilingual and quote only displayed numbers. The model is stored as readable JSON, not a pickle.

**What changed during the phase:** my first feature definitions gave two wrong-sign coefficients (dry spell and active days), because dry spells were counted inside weekly variability and single zero-UPI days mostly reflect few transactions, not closures. I redefined both features. All five signs are now correct **without the bound being active**; the bound stays as a guardrail.

**Coefficients (standardised):** income/EMI −0.50, active days −0.21, recent trend −0.07, weekly variability +0.05, dry spell +0.02.

**Tests:** sign test, monotonicity in income vs EMI and in dry-spell length, PDO doubling, score range, band edges, reason codes, training and scoring determinism.

**Limitations and open questions**
* Income relative to EMI does almost all the work. Weekly variability and dry spell carry little extra signal here, partly because the generator puts most of the risk in hidden traits.
* The model is trained on 180-day windows. Applicants with only 90 days have noisier features, and the score does not yet widen its uncertainty for them.
* The band thresholds (575 / 535) were picked from the synthetic score distribution, giving 37% approve, 44% review and 19% decline. A lender must set them from its own risk appetite and review capacity: 44% to review may be too many for its staff.

## Phase 3: Evaluation

Hold-out test set: 2,000 vendors, 9.8% default. Full report: [`reports/evaluation.md`](../reports/evaluation.md).

| | AUC | KS | Brier |
|---|---|---|---|
| Logistic regression | 0.692 | 0.297 | 0.0855 |
| Gradient boosting (comparison) | 0.682 | 0.285 | 0.0862 |
| Baseline rule (0/1) | 0.615 | - | - |
| Baseline ratio as a ranking | 0.683 | - | - |

* **At the same approval rate (71.5%)**, the model's default rate is 6.78% against the rule's 6.92%, a 2% relative reduction.
* **At the same default rate (6.92%)**, the model approves 73.9% against the rule's 71.5%: +23 per 1,000 applicants.
* **AUC gain** over the 0/1 rule is +0.077 (95% CI +0.050 to +0.104). Over ranking by the ratio alone it is **+0.009 (CI −0.010 to +0.028), not significant.** Gradient boosting minus logistic regression is −0.010 (CI −0.038 to +0.018).
* Calibration is reasonable in the middle deciles. The top decile is slightly over-predicted, and the lowest decile is over-predicted (3.6% predicted vs 0.5% observed).
* Bands rank risk: approve 3.8%, review 10.6%, decline 19.2% default.
* **Weak segments:** flower sellers, fruit carts, kirana shops and the ≥ Rs 60k band have too few defaults to judge (fewer than 30). No segment's AUC is more than 0.05 below overall.
* **Bias finding (most important):** sellers who take more than 60% of sales in cash default at 8.8%, the same as low-cash sellers (8.6%). But the model puts 37.5% of them in decline against 4.0% of low-cash sellers, because UPI misses their cash income. This is exactly the slide-14 risk ("bias against cash-heavy sellers").

**Limitations and open questions**
* The honest headline: the gain comes mostly from *ranking* by income/EMI instead of using a hard 3× cut-off. The extra features add little on this data.
* The cash-share bias needs a design answer before any pilot: a declared cash-sales field verified in a field visit, bank deposits via Account Aggregator, or a segment-specific review policy.
* With 196 test defaults, segment AUCs have wide intervals.

## Phase 4: Scoring API

**What was built:** FastAPI app (Python 3.11) with `POST /score`, `GET /health` and `GET /model-info`. Requests without consent get 403 with nothing scored. Fewer than 90 days gets 422. EMI is computed from `annual_rate` if missing. The append-only JSONL audit log is hash-chained, stores the HMAC-SHA256 of the vendor ID and the model version, and never stores raw income records. A tamper check is included.

**Tests:** contract, consent rejection, the 89/90-day boundary, input validation, EMI from rate, audit hashing and chain, tamper detection, determinism, console endpoints.

**Limitations and open questions**
* There is no authentication or rate limiting yet. These are needed before any deployment.
* `AUDIT_SALT` must come from a secrets manager. The audit log is a local file and would need WORM storage in production.
* Open question: how is consent captured and evidenced (Account Aggregator consent artefact)? Today it is a boolean the caller asserts.

## Phase 5: Explanation agent

**What was built:** a provider-agnostic `LLMProvider` interface. The Claude implementation uses the official Anthropic SDK (`claude-opus-5-5` at low effort, with server-side fallback if the model declines). `build_llm_input` whitelists the score, band and reason sentences only. The output must be JSON `{en, hi}`. The validator rejects numbers not in the input (including Devanagari digits), approval or promise language, advice on changing the score, outside facts (bureau, collateral, interest rate and similar), a missing score, and non-Devanagari Hindi. The fallback is a deterministic bilingual template that passes the same validator.

**Tests:** no personal data in the LLM input, the template passes for all bands, six kinds of ungrounded output are rejected, Hindi digits are checked, bad, failed or non-JSON LLM output falls back, good output is used, determinism.

**Limitations and open questions**
* **No API key was available in this build environment, so the live LLM path was exercised only through test doubles.** The template path is what ran end to end.
* The validator is pattern-based. It catches numbers and listed phrases, but not every possible paraphrased claim. A sample of LLM outputs should be reviewed by a person before going live.
* The Hindi was written by me and should be reviewed by a native speaker, and ideally tested with vendors for clarity.

## Phase 6: Early-warning agent

**What was built:** a weekly job that compares each active loan's last 4 weeks of UPI with the vendor's own 12-week median. It flags a sustained dip (3 of 4 weeks below 50%, and a 4-week mean below 60%) and long dry spells (21+ days with no UPI income in the last 4 weeks). Each flag gets a severity, a reason with numbers, and a suggested human action. `auto_contact` is always False. Thresholds were tuned on **training vendors** with a small grid, and are reported on held-out vendors.

**Results (2,000 held-out loans, 195 defaults):** recall 67.2%, vendor-level precision 23.4% (base rate 9.8%), 23.8% of good payers flagged at least once in 12 months. Median lead time is **22 days** before the first missed EMI (IQR 9-45); 67% of catches come at least 14 days ahead. Recall is 82% when distress is visible in UPI and 23% when it is not.

**What changed during the phase:** my first thresholds (7-day dry spell, 60% dip) flagged 59% of good payers, too noisy to use. I tuned them down on training vendors only.

**Limitations and open questions**
* Severity does not separate precision (high 22.4% vs medium 22.0%), so it is not yet a useful priority signal.
* One alert in four leads to a missed payment within 90 days. Staff time per alert decides whether that is worth it, and only the lender knows that cost.
* A real test needs a control group: flagged accounts with and without the follow-up, comparing slippage from 1-30 to 31-60 days late.

## Phase 7: Shadow-mode report

**What was built:** a reader for a CSV of past loans (`vendor_id, emi, lender_decision, default_12m`) plus UPI records. It scores each loan and compares the model and the baseline rule with the lender's decisions. Outcomes are used only for lender approvals. The report states the reject-inference caveat and never modifies its input. The synthetic sample uses a simulated lender (a field officer's noisy view of true income) that approves 65%.

**Results (sample):** the lender's approvals default at 7.23%. Applying the model's decline band would have removed 153 of them, which defaulted at 16.3% (the rest at 6.0%): 25 defaults avoided and 128 good loans lost. The baseline rule would have removed 225, which defaulted at 14.2%: 32 avoided and 193 good loans lost. On lender approvals, AUC is 0.697 for the model and 0.680 for the rule. Of the 700 lender declines, the model would have put 120 in approve; their outcomes are unknown.

**Limitations and open questions**
* The "lender" here is simulated. Real lender decisions will use information the model cannot see, which can make the comparison look better or worse.
* Choosing between avoided defaults and good loans lost needs the lender's unit economics (the deck's illustrative example has a margin of about Rs 400 per Rs 20,000 loan).
* Open questions for a lender partner: can they share anonymised past loans with UPI or bank-statement data? What default definition do they use? How much review capacity do they have?
