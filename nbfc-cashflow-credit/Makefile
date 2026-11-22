PY ?= python
export PYTHONPATH := src

.PHONY: install data train evaluate ews shadow reports test serve all docker

install:
	$(PY) -m pip install -r requirements-dev.txt

data:            ## Phase 1: synthetic vendors, daily UPI, outcomes
	$(PY) -m vendorscore.data.synth
train:           ## Phase 2: features + scorecard -> artifacts/model.json
	$(PY) -m vendorscore.model
evaluate:        ## Phase 3: reports/evaluation.{json,md}
	$(PY) -m vendorscore.evaluate
ews:             ## Phase 6: reports/early_warning.{json,md}
	$(PY) -m vendorscore.agents.early_warning
shadow:          ## Phase 7: reports/shadow_report.{json,md}
	$(PY) -m vendorscore.agents.shadow
reports: evaluate ews shadow
all: data train reports

test:
	$(PY) -m pytest -q

serve:           ## Phase 4: API + lender console on http://localhost:8000
	$(PY) -m uvicorn vendorscore.api.app:app --host 0.0.0.0 --port 8000

docker:
	docker build -t vendorscore .
