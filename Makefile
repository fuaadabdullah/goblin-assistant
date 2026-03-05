# GoblinOS Assistant Makefile

.PHONY: help dev-setup dev-setup-apply dev-setup-full dev-setup-ci

help:
	@echo "Available targets:"
	@echo "  dev-setup        - Check dev environment setup (safe)"
	@echo "  dev-setup-apply  - Apply dev environment setup (install deps)"
	@echo "  dev-setup-full   - Apply setup and boot local LLM"

# Dev environment setup
dev-setup:
	./scripts/dev-setup.sh --check

dev-setup-apply:
	./scripts/dev-setup.sh --apply

dev-setup-full:
	./scripts/dev-setup.sh --apply --boot-llm

dev-setup-ci:
	./scripts/dev-setup.sh --check --ci

# Convenience targets to manage a local ChromaDB server used by RAG tests
.PHONY: chroma-up chroma-down

chroma-up:
	@echo "Starting Chroma server (delegating to api/fastapi Makefile)..."
	@$(MAKE) -C api/fastapi start-chroma

chroma-down:
	@echo "Stopping Chroma server (delegating to api/fastapi Makefile)..."
	@$(MAKE) -C api/fastapi stop-chroma

.PHONY: provision-local
provision-local:
	@echo "Provisioning a local model using tools/provision_local_model.sh"
	@if [ -z "$(MODEL)" ]; then echo "Please set MODEL=<huggingface-model-id> or pass ARGS='--model <id>'"; exit 1; fi
	@bash tools/provision_local_model.sh --model $(MODEL) $(ARGS)

.PHONY: e2e-mock
e2e-mock:
	@echo "Running e2e tests with mock provider (delegating to api/fastapi Makefile)..."
	@$(MAKE) -C api/fastapi test-e2e-mock
