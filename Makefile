PYTHON ?= python3
SKILLS_DIR ?= $(HOME)/.claude/skills/regintel

.PHONY: validate test check scan-self install

validate:
	$(PYTHON) tools/validate_repo.py

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check: validate test

install:
	mkdir -p $(SKILLS_DIR)
	cp skills/regintel/SKILL.md $(SKILLS_DIR)/SKILL.md

scan-self:
	$(PYTHON) scripts/repo_signal_scan.py --path . --scope full > /tmp/regintel-scan.json
	$(PYTHON) scripts/applicability_score.py --signals /tmp/regintel-scan.json --format markdown
