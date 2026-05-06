SYSTEM_PYTHON ?= python3
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
BIN ?= $(VENV)/bin
CONSTRAINTS ?= constraints-dev.txt
DEV_STAMP := $(VENV)/.synrail-dev-installed

.PHONY: install-dev install-local smoke test compile lint coverage audit demo verify docker-build clean-dev

$(PYTHON):
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip

$(DEV_STAMP): pyproject.toml constraints-dev.txt $(PYTHON)
	$(PYTHON) -m pip install -e ".[dev]" -c $(CONSTRAINTS)
	touch $(DEV_STAMP)

install-dev: $(DEV_STAMP)

install-local:
	$(SYSTEM_PYTHON) tools/reference/synrail_install_v0.py --venv $(VENV) --project-root "$$(pwd)"

smoke: $(DEV_STAMP)
	$(PYTHON) -m unittest tests.test_install_smoke

test: $(DEV_STAMP)
	$(PYTHON) -m unittest discover -s tests

compile: $(PYTHON)
	$(PYTHON) -m py_compile alpha.py tools/reference/*.py

lint: $(DEV_STAMP)
	$(BIN)/ruff check .

coverage: $(DEV_STAMP)
	$(BIN)/pytest --cov=tools/reference --cov=alpha --cov-report=term-missing --cov-report=xml

audit: $(DEV_STAMP)
	$(BIN)/pip-audit

demo:
	./examples/false-green-demo/run_demo.sh

verify: compile test lint coverage audit

docker-build:
	docker build -t synrail-demo .

clean-dev:
	rm -rf $(VENV)
