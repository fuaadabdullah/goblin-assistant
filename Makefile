.PHONY: help install dev web-dev api-dev build lint type-check test test-web test-api test-e2e generate-providers-json
PNPM_TMP := TMPDIR="$(PWD)/.tmp"
PYTHON ?= python3.11

help:
	@echo "Workspace commands"
	@echo "  make install              - install JS & Python deps"
	@echo "  make dev                  - run web + api in parallel (requires two terminals)"
	@echo "  make web-dev              - start Next.js web app"
	@echo "  make api-dev              - start FastAPI backend"
	@echo "  make lint                 - run web lint"
	@echo "  make type-check           - run web typecheck"
	@echo "  make test-web             - run web test suite"
	@echo "  make test-api             - run api pytest suite"
	@echo "  make test-e2e             - run Playwright suite"
	@echo "  make generate-providers-json — validate providers.toml & regenerate providers.json"

install:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm install
	cd apps/api && $(PYTHON) -m pip install -r requirements.txt -r requirements-vector.txt

generate-providers-json:
	PYTHONPATH=packages/shared/src $(PYTHON) scripts/generate-providers-json.py

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

lint:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web lint

type-check:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web type-check

test:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-web:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test

test-api:
	cd apps/api && PYTHONPATH=src $(PYTHON) -m pytest -o "addopts=" -v

test-e2e:
	mkdir -p .tmp
	$(PNPM_TMP) pnpm --filter @goblin/web test:e2e
