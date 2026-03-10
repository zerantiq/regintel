PYTHON ?= python3

.PHONY: validate test check scan-self

validate:
	$(PYTHON) tools/validate_repo.py

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check: validate test

scan-self:
	$(PYTHON) scripts/repo_signal_scan.py --path . --scope full > /tmp/regintel-scan.json
	$(PYTHON) scripts/applicability_score.py --signals /tmp/regintel-scan.json --format markdown
