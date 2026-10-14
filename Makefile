ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
SHELL := /bin/bash

include .devcontainer/.env
export

APP_NAME := jobs
DOCKER_IMAGE_TAG := $(APP_NAME):dev

.PHONY: help
help: ## This help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build
build: ## Build app package
	rm -rf dist
	uv build --wheel

.PHONY: bootstrap
bootstrap: ## Perform a bootstrap
	# deleting as there may be a conflict when running inside a devcontainer vs local host
	rm -rf .venv
	command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
	$(MAKE) generate-clients
	# install app and all deps (uv creates .venv in-project)
	uv sync
	# install pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

.PHONY: lint
lint: ## Run linters
	uv run pre-commit run --all-files

.PHONY: test
test: ## Run unit tests
	uv run pytest tests/

.PHONY: clean
clean: ## Remove all generated artifacts (except .venv and .env)
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -rf {} +
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf dist
	rm -rf jobs/services/clients/jukeboxsvc

.PHONY: docker-run
docker-run: ## Run dev docker image
	docker run --rm -it \
		--name yag-$(APP_NAME) \
		--env-file $(ROOT_DIR)/.devcontainer/.env \
		--env-file $(ROOT_DIR)/.devcontainer/secret.env \
		$(DOCKER_IMAGE_TAG)

.PHONY: docker-build
docker-build: ## Build docker image
	docker build \
		-t $(DOCKER_IMAGE_TAG) \
		--progress plain \
		.

.PHONY: gha-build
gha-build: ## GitHub action: install all deps, lint, test and build app
	$(MAKE) generate-clients
	uv sync --locked
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) build

.PHONY: update-clients
update-clients:
	curl -sSf $(JUKEBOXSVC_URL)/openapi.json | python3 -m json.tool > jobs/services/clients/jukeboxsvc.json
	$(MAKE) generate-clients

.PHONY: generate-clients
generate-clients:
	uv run --only-group codegen openapi-python-client generate --overwrite \
		--path jobs/services/clients/jukeboxsvc.json \
		--output-path jobs/services/clients/jukeboxsvc
	# so it isn't treated as a separate project
	rm -f jobs/services/clients/jukeboxsvc/pyproject.toml
