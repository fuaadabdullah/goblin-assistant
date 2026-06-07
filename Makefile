.PHONY: help install dev web-dev api-dev build build-packages lint lint-web lint-api lint-policy type-check type-check-packages test test-unit test-web test-api test-api-context-coverage test-e2e test-e2e-budget test-integration test-contract test-performance generate-providers-json check-providers-json check-api-boundaries check-api-cycles check-capability-boundaries check-route-lifecycle type-check-api-mypy type-check-api-pyright format format-check test-critical sdk-generate sdk-check secret-scan check-unused-deps check-dead-code
PNPM_TMP := TMPDIR="$(PWD)/.tmp"
PYTHON ?= python3

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
	@echo "  make test-unit            - run all unit tests (web + api)"
	@echo "  make test-web             - run web test suite (subset of test-unit)"
	@echo "  make test-api             - run api pytest suite (subset of test-unit)"
	@echo "  make test-integration     - run integration + contract buckets from tests/manifests"
	@echo "  make test-contract        - run contract bucket only"
	@echo "  make test-performance     - run performance bucket from tests/manifests"
	@echo "  make test-critical        - run critical-path coverage gates"
	@echo "  make check-dead-code      - find unused Python functions and TS exports"
	@echo "  make secret-scan          - scan config/env/docs for embedded secrets"
	@echo "  make format               - auto-format web + api"
	@echo "  make format-check         - run blocking format checks"
	@echo "  make test-api-context-coverage - run context assembly service coverage gate (>=90%)"
	@echo "  make check-api-boundaries - enforce API module import boundaries"
	@echo "  make check-api-cycles     - enforce no API circular dependencies"
	@echo "  make check-capability-boundaries - enforce capability ownership rules"
	@echo "  make check-route-lifecycle - validate route lifecycle metadata policy"
	@echo "  make type-check-api-mypy  - run strict mypy for API"
	@echo "  make type-check-api-pyright - run strict pyright for API"
	@echo "  make test-e2e             - run Playwright suite"
	@echo "  make test-e2e-budget      - enforce critical E2E journey cap"
	@echo "  make sdk-generate         - export OpenAPI and generate SDK types"
	@echo "  make sdk-check            - fail if SDK generated artifacts are stale"
	@echo "  make generate-providers-json — validate providers.toml & regenerate providers.json"
	@echo "  make check-providers-json  - fail if providers.json is stale"

install:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm install
	cd apps/api && $(PYTHON) -m pip install -r requirements.txt -r requirements-vector.txt

check-api-boundaries:
	$(PYTHON) scripts/architecture/check_api_architecture.py boundaries

check-api-cycles:
	$(PYTHON) scripts/architecture/check_api_architecture.py cycles

check-capability-boundaries:
	$(PYTHON) scripts/architecture/check_capability_boundaries.py

check-route-lifecycle:
	$(PYTHON) scripts/architecture/check_route_lifecycle.py

type-check-api-mypy:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m mypy --config-file pyproject.toml src/api

type-check-api-pyright:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pyright --project pyrightconfig.json

generate-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) tooling/generators/generate-providers-json.py

check-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) tooling/generators/generate-providers-json.py --check

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
	$(PNPM_TMP) pnpm run packages:type-check

type-check-packages:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm run packages:type-check

build-packages:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm run packages:build

format:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web exec prettier --write .
	$(PNPM_TMP) pnpm --filter @goblin/web exec eslint . --fix
	cd apps/api && PYTHONPATH=src $(PYTHON) -m ruff format src/api

format-check:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web exec prettier --check .
	$(PNPM_TMP) pnpm --filter @goblin/web exec eslint .
	cd apps/api && PYTHONPATH=src $(PYTHON) -m ruff format --check src/api

test: test-unit

test-unit:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-web:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test

test-api:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-critical:
	bash tooling/quality/run-critical-coverage.sh

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
	bash tooling/quality/check-e2e-budget.sh

test-integration:
	$(PYTHON) tooling/quality/run-test-bucket.py integration
	$(PYTHON) tooling/quality/run-test-bucket.py contract

test-contract:
	$(PYTHON) tooling/quality/run-test-bucket.py contract

test-performance:
	$(PYTHON) tooling/quality/run-test-bucket.py performance

sdk-generate:
	bash tooling/generators/generate-sdk-client.sh

sdk-check:
	bash tooling/generators/check-sdk-generated.sh

secret-scan:
	$(PYTHON) scripts/security/scan_secrets.py

check-dead-code:
	cd apps/api && $(PYTHON) -m vulture src/api --min-confidence 80
	$(PNPM_TMP) pnpm --filter @goblin/web dead-code

check-unused-deps:
	@echo "==> Python unused/transitive deps"
	cd apps/api && pip install --quiet pipdeptree && pipdeptree --warn fail
	@echo "==> Node.js unused deps"
	$(PNPM_TMP) pnpm --filter @goblin/web exec npx depcheck
