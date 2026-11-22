# Shadow-mode report

> Shadow mode: read-only comparison. No real lending decision was changed.
> Model built on SYNTHETIC data; treat results as a method check, not evidence of accuracy.

Loans: 2000 (2000 scored, 0 with too little history). Lender approved 1300, declined 700; outcomes known for 1300.

## Among loans the lender approved

Lender's default rate on approvals: **7.23%**

| | would decline | their default rate | rest's default rate | defaults avoided | good loans lost | AUC |
|---|---|---|---|---|---|---|
| Model (decline band) | 153 | 16.34% | 6.02% | 25 | 128 | 0.6969 |
| Baseline rule | 225 | 14.22% | 5.77% | 32 | 193 | 0.6798 |

Default rate by model band (lender approvals only):

* approve: n=620, default rate 0.0323
* review: n=527, default rate 0.093
* decline: n=153, default rate 0.1634

## Loans the lender declined

700 declined. The model would have put 120 in approve and 347 in review; the baseline rule would have approved 356.

_Outcomes are unknown for loans the lender declined, so these cannot be scored as right or wrong. They are candidates for a controlled test, not proof of missed good borrowers._
