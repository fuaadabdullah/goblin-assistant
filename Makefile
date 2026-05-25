.PHONY: help install dev web-dev api-dev build lint lint-web lint-api lint-policy type-check test test-web test-api test-api-context-coverage test-e2e test-e2e-budget generate-providers-json check-api-boundaries check-api-cycles type-check-api-mypy type-check-api-pyright format format-check test-critical
PNPM_TMP := TMPDIR="$(PWD)/.tmp"
PYTHON ?= python3.11

help:
	@echo "Workspace commands"
	@echo "  make install              - install JS & Python deps"
	@echo "  make dev                  - run web + api in parallel (requires two terminals)"
	@echo "  make web-dev              - start Next.js web app"
	@echo "  make api-dev              - start FastAPI backend"
	@echo "  make lint                 - run web + api lint"
	@echo "  make lint-web             - run web lint"
	@echo "  make lint-api             - run api Ruff lint"
	@echo "  make type-check           - run web typecheck"
	@echo "  make test-web             - run web test suite"
	@echo "  make test-api             - run api pytest suite"
	@echo "  make test-critical        - run critical-path coverage gates"
	@echo "  make format               - auto-format web + api"
	@echo "  make format-check         - run blocking format checks"
	@echo "  make test-api-context-coverage - run context assembly service coverage gate (>=90%)"
	@echo "  make check-api-boundaries - enforce API module import boundaries"
	@echo "  make check-api-cycles     - enforce no API circular dependencies"
	@echo "  make type-check-api-mypy  - run strict mypy for API"
	@echo "  make type-check-api-pyright - run strict pyright for API"
	@echo "  make test-e2e             - run Playwright suite"
	@echo "  make test-e2e-budget      - enforce critical E2E journey cap"
	@echo "  make generate-providers-json — validate providers.toml & regenerate providers.json"

install:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm install
	cd apps/api && $(PYTHON) -m pip install -r requirements.txt -r requirements-vector.txt

check-api-boundaries:
	$(PYTHON) scripts/architecture/check_api_architecture.py boundaries

check-api-cycles:
	$(PYTHON) scripts/architecture/check_api_architecture.py cycles

type-check-api-mypy:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m mypy --config-file pyproject.toml src/api

type-check-api-pyright:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pyright --project pyrightconfig.json

generate-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) scripts/generate-providers-json.py
	cp config/providers.json apps/web/src/config/providers.json

web-dev:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web dev

api-dev:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m uvicorn api.main:app --reload --port 8001

dev:
	@echo "Run 'make web-dev' and 'make api-dev' in separate terminals"

build: generate-providers-json
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web build

lint: lint-web lint-api lint-policy

lint-web:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web lint

lint-api:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m ruff check --config pyproject.toml src/api

lint-policy:
	$(PYTHON) scripts/policy_guard.py --strict

type-check:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web type-check

format:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web exec prettier --write .
	$(PNPM_TMP) pnpm --filter @goblin/web exec eslint . --fix
	cd apps/api && PYTHONPATH=src $(PYTHON) -m ruff format src/api
	cd apps/api && PYTHONPATH=src $(PYTHON) -m black src/api

format-check:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web exec prettier --check .
	$(PNPM_TMP) pnpm --filter @goblin/web exec eslint .
	cd apps/api && PYTHONPATH=src $(PYTHON) -m ruff format --check src/api
	cd apps/api && PYTHONPATH=src $(PYTHON) -m black --check src/api

test:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-web:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test

test-api:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-critical:
	bash scripts/run-critical-coverage.sh

test-api-context-coverage:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v \
		src/api/tests/test_context_assembly*.py \
		--cov=src/api/services/context_assembly_service \
		--cov-report=term-missing \
		--cov-fail-under=90

test-e2e:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test:e2e

test-e2e-budget:
	bash scripts/check-e2e-budget.sh
