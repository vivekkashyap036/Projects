# Early-warning agent report (SYNTHETIC DATA)

> Synthetic data. These numbers show the method works; they are not real-world performance.

2000 loans (held-out test vendors), 195 defaults. Weekly runs every 7 days from origination until the first missed EMI or the end of the 12-month window. Thresholds were tuned on the training vendors only.

## Vendor level

* Recall (defaulters flagged before their first missed EMI): **67.2%**
* Precision (flagged vendors who went on to miss a payment): **23.4%** (base default rate 9.8%, so a random flag would be right 9.8% of the time)
* Good payers flagged at least once: 23.8%

## Lead time before the first missed EMI (true positives)

* Median **22.0 days** (IQR 9.0-45.0)
* At least 14 days ahead: 67%; at least 30 days ahead: 41%

## Alert level

* 1563 weekly alerts; 22.3% were followed by a missed EMI within 90 days
* high severity: 1049 alerts, 22.4% followed by a missed EMI within 90 days
* medium severity: 514 alerts, 22.0% followed by a missed EMI within 90 days

## Diagnostics (uses hidden synthetic traits)

* Recall when distress shows in UPI: 81.6%; when it does not: 22.9%
* Share of false alarms that were good payers with a temporary dip: 21.9%
