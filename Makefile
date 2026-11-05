.DEFAULT_GOAL := help
PY ?= .venv/bin/python

help: ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## create .venv and install with dev tools
	python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'

lint: ## ruff (lint + format check)
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

types: ## mypy --strict
	.venv/bin/mypy

test: ## unit and process-level tests
	.venv/bin/pytest

guard: ## this repository's own documentation guards, and what a session costs
	.venv/bin/docsguard check && .venv/bin/docsguard budget

mutate: ## break every guard on purpose; each must turn its test red
	$(PY) scripts/sabotage.py

transcripts: ## re-record the tour on the landing page from the real command line
	$(PY) scripts/record_transcripts.py

transcripts-check: ## fail if the tour on the landing page no longer matches what the tool prints
	$(PY) scripts/record_transcripts.py --check

check: lint types test guard transcripts-check ## everything CI runs, minus Docker, the browser and mutation

docker: ## build the image and run the guards on this repository from the container
	docker compose build check && TARGET=. docker compose run --rm check

E2E_USER = --user $$(id -u):$$(id -g) -e HOME=/tmp

playground: ## build the lab and start it on http://localhost:8200 (loopback only)
	docker compose up --build --wait -d playground
	@echo; echo "  the lab:  http://localhost:$${DG_PORT:-8200}     stop it with: make down"

down: ## stop the lab
	docker compose down

smoke: ## checks that talk to the running lab (make playground first)
	scripts/smoke.sh http://localhost:$${DG_PORT:-8200}

e2e: ## browser tests (Playwright + axe) against the lab, in a container
	@mkdir -p docs/img  # Docker would create a missing bind-mount source as root
	docker compose up --build --wait -d playground
	docker compose --profile e2e run --rm $(E2E_USER) e2e

screenshots: ## re-take the README screenshots (docs/img) from the running lab
	@mkdir -p docs/img
	docker compose up --build --wait -d playground
	docker compose --profile e2e run --rm $(E2E_USER) -e SHOTS=1 e2e bash -lc "npm ci --no-audit --no-fund && npx playwright test shots"

clean: ## remove build and cache directories
	rm -rf build dist .mypy_cache .pytest_cache .ruff_cache src/*.egg-info

.PHONY: help install lint types test guard mutate transcripts transcripts-check check docker playground down smoke e2e screenshots clean
