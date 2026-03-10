PYTHON ?= python3

.PHONY: validate scan-self

validate:
	$(PYTHON) tools/validate_repo.py

scan-self:
	$(PYTHON) scripts/repo_signal_scan.py --path . --scope full > /tmp/regintel-scan.json
	$(PYTHON) scripts/applicability_score.py --signals /tmp/regintel-scan.json --format markdown
