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

check: lint types test guard ## everything CI runs, minus Docker and mutation

docker: ## build the image and run the guards on this repository from the container
	docker compose build check && TARGET=. docker compose run --rm check

clean: ## remove build and cache directories
	rm -rf build dist .mypy_cache .pytest_cache .ruff_cache src/*.egg-info

.PHONY: help install lint types test guard mutate check docker clean
