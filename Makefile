.PHONY: help install install-web dev web-dev api-dev api-docker-up api-docker-down build build-packages lint lint-web lint-api lint-policy type-check type-check-packages test test-unit test-web test-web-coverage test-api test-api-coverage test-api-context-coverage test-e2e test-e2e-budget test-integration test-contract test-performance generate-providers-json check-providers-json check-api-boundaries check-api-cycles check-api-cycles-report check-capability-boundaries check-route-lifecycle check-operational-policy check-docs-canonical-refs check-docs-inventory check-docs-links generate-docs-coverage type-check-api-mypy type-check-api-pyright format format-check test-critical sdk-generate sdk-check generate-route-manifest check-api-calls contract-checks secret-scan check-unused-deps check-dead-code phase-gates
PNPM_TMP := TMPDIR="$(PWD)/.tmp"
PYTHON ?= python3.11

help:
	@echo "Workspace commands"
	@echo "  make install              - install JS & Python deps for full native dev"
	@echo "  make install-web          - install JS deps for Docker-first backend workflow"
	@echo "  make dev                  - run web + api in parallel (requires two terminals)"
	@echo "  make web-dev              - start Next.js web app"
	@echo "  make api-dev              - start FastAPI backend"
	@echo "  make api-docker-up        - start Redis + FastAPI backend via Docker Compose"
	@echo "  make api-docker-down      - stop Redis + FastAPI backend Docker services"
	@echo "  make lint                 - run web + api lint"
	@echo "  make lint-web             - run web lint"
	@echo "  make lint-api             - run api Ruff lint"
	@echo "  make type-check           - run web typecheck"
	@echo "  make test-unit            - run all unit tests (web + api)"
	@echo "  make test-web             - run web test suite (subset of test-unit)"
	@echo "  make test-web-coverage    - run web test suite with coverage gates"
	@echo "  make test-api             - run api pytest suite (subset of test-unit)"
	@echo "  make test-api-coverage    - run api pytest suite with coverage gates"
	@echo "  make test-integration     - run integration + contract buckets from tests/manifests"
	@echo "  make test-contract        - run contract bucket only"
	@echo "  make test-performance     - run performance bucket from tests/manifests"
	@echo "  make test-critical        - run critical-path journey gates"
	@echo "  make phase-gates          - run rollout phase-gate checks"
	@echo "  make check-dead-code      - find unused Python functions and TS exports"
	@echo "  make secret-scan          - scan config/env/docs for embedded secrets"
	@echo "  make format               - auto-format web + api"
	@echo "  make format-check         - run blocking format checks"
	@echo "  make test-api-context-coverage - run context assembly service coverage gate (>=90%)"
	@echo "  make check-api-boundaries - enforce API module import boundaries"
	@echo "  make check-api-cycles     - enforce no API circular dependencies"
	@echo "  make check-api-cycles-report - report API circular dependencies (non-blocking, writes artifacts/api-cycles.json + .dot)"
	@echo "  make check-capability-boundaries - enforce capability ownership rules"
	@echo "  make check-route-lifecycle - validate route lifecycle metadata policy"
	@echo "  make check-operational-policy - validate Docker, deploy target, and dependency-update policy"
	@echo "  make check-docs-canonical-refs - fail on stale docs canonical-location references"
	@echo "  make check-docs-inventory - validate docs inventory coverage and compatibility stubs"
	@echo "  make check-docs-links - validate local markdown links in docs"
	@echo "  make generate-docs-coverage - write the checked-in docs coverage report"
	@echo "  make type-check-api-mypy  - run strict mypy for API"
	@echo "  make type-check-api-pyright - run strict pyright for API"
	@echo "  make test-e2e             - run Playwright suite"
	@echo "  make test-e2e-budget      - enforce critical E2E journey cap"
	@echo "  make sdk-generate         - export OpenAPI, route manifest, and SDK types"
	@echo "  make sdk-check            - fail if generated SDK and route artifacts are stale"
	@echo "  make generate-route-manifest - export the checked-in FastAPI route manifest"
	@echo "  make check-api-calls      - validate frontend API path usage against client rules"
	@echo "  make contract-checks      - run SDK drift and frontend API path validation"
	@echo "  make generate-providers-json — validate providers.toml & regenerate providers.json"
	@echo "  make check-providers-json  - fail if providers.json is stale"

install:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm install
	cd apps/api && $(PYTHON) -m pip install -r requirements.txt -r requirements-vector.txt

install-web:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm install

check-api-boundaries:
	$(PYTHON) scripts/architecture/check_api_architecture.py boundaries

check-api-cycles:
	$(PYTHON) scripts/architecture/check_api_architecture.py cycles

check-api-cycles-report:
	mkdir -p artifacts
	$(PYTHON) scripts/architecture/check_api_architecture.py cycles --report-only --output artifacts/api-cycles.json

check-capability-boundaries:
	$(PYTHON) scripts/architecture/check_capability_boundaries.py

check-route-lifecycle:
	$(PYTHON) scripts/architecture/check_route_lifecycle.py

check-operational-policy:
	$(PYTHON) scripts/architecture/check_operational_policy.py

check-docs-canonical-refs:
	$(PYTHON) scripts/architecture/check_docs_canonical_refs.py

check-docs-inventory:
	$(PYTHON) scripts/architecture/check_docs_inventory.py

check-docs-links:
	$(PYTHON) scripts/architecture/check_docs_links.py

generate-docs-coverage:
	$(PYTHON) scripts/architecture/generate_docs_coverage.py

type-check-api-mypy:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m mypy \
		--ignore-missing-imports \
		--disallow-any-generics \
		--follow-imports=skip \
		src/api/services/error_summarizer.py \
		src/api/ops_routes/sentry_webhook.py \
		src/api/providers/rovo_dev_provider.py \
		src/api/routes/support_router.py

type-check-api-pyright:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pyright --project pyrightconfig.json \
		src/api/services/error_summarizer.py \
		src/api/ops_routes/sentry_webhook.py \
		src/api/providers/rovo_dev_provider.py \
		src/api/routes/support_router.py

generate-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) tooling/generators/generate-providers-json.py

check-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) tooling/generators/generate-providers-json.py --check

web-dev:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web dev

api-dev:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m uvicorn api.main:app --reload --port 8001

api-docker-up:
	docker compose up -d redis goblin-assistant-backend

api-docker-down:
	docker compose stop goblin-assistant-backend redis

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
	$(PYTHON) scripts/architecture/check_operational_policy.py
	$(PYTHON) scripts/policy_guard.py --strict
	$(PYTHON) scripts/architecture/check_docs_canonical_refs.py
	$(PYTHON) scripts/architecture/check_docs_inventory.py
	$(PYTHON) scripts/architecture/check_docs_links.py

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

test-web-coverage:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test:coverage

test-api:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-api-coverage:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v \
		--cov=api \
		--cov-report=term-missing \
		--cov-fail-under=68

test-critical:
	bash tooling/quality/run-critical-coverage.sh

test-api-context-coverage:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v \
		src/api/tests/test_context_assembly*.py \
		src/api/tests/context_assembly_coverage \
		--cov=api.services.context_assembly_service \
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

test-engine:
	@echo "==> Engine smoke test — exercises all six pillars"
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v \
		../../tests/contract/test_engine_routing_contract.py \
		../../tests/contract/test_engine_memory_contract.py \
		../../tests/contract/test_engine_sandbox_contract.py \
		../../tests/contract/test_engine_auth_contract.py \
		../../tests/contract/test_engine_observability_contract.py \
		--tb=short -q
	@echo "==> Engine smoke test complete"

test-performance:
	$(PYTHON) tooling/quality/run-test-bucket.py performance

phase-gates:
	$(PYTHON) scripts/phase_gates.py all

sdk-generate:
	bash tooling/generators/generate-sdk-client.sh

sdk-check:
	bash tooling/generators/check-sdk-generated.sh

generate-route-manifest:
	python3.11 tooling/generators/export-route-manifest.py

check-api-calls:
	python3.11 tooling/quality/check-api-paths.py

contract-checks: sdk-check check-api-calls

secret-scan:
	$(PYTHON) scripts/security/scan_secrets.py

check-dead-code:
	cd apps/api && $(PYTHON) -m vulture src/api vulture_whitelist.py --min-confidence 80
	$(PNPM_TMP) pnpm --filter @goblin/web dead-code

check-unused-deps:
	@echo "==> Python unused/transitive deps"
	cd apps/api && pip install --quiet pipdeptree && pipdeptree --warn fail
	@echo "==> Node.js unused deps"
	$(PNPM_TMP) pnpm --filter @goblin/web exec npx depcheck
