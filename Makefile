.PHONY: init install dev test test-unit test-integration test-cov lint format type-check clean run migrate setup-hooks

# Initialisation
init:
	@git init
	@echo
	@echo "=========================================================================================="
	@echo "Please create a github repo called 'agent-email-summarizer' with a main branch"
	@echo "(For example, by having github create a README for you.)"
	@echo "Then, set up environment variables as per the README."
	@echo "=========================================================================================="
	@echo
	@echo "Please confirm you have created the repository and the settings as per the README (Y/n):"
	@read line; if [ $$line = "n" ]; then echo Aborting. Please commit the initial code manually; exit 1 ; fi
	@git remote add origin git@github.com:Arata-AI/agent-email-summarizer.git
	@git fetch
	@git checkout main
	@mv -f README._md README.md
	@git checkout -b initial
	@git add -A
	@git commit -m "Initial commit"
	@git push origin initial
	@echo "=========================================================================================="
	@echo "Initial commit pushed to 'initial' branch. Please create a PR to merge to main."
	@echo
	@. ./setup_pulumi.sh


# Install production dependencies
install: setup-hooks
	uv sync --all-packages

# Setup git hooks
setup-hooks:
	@if [ ! -d .githooks ]; then \
		echo "Error: .githooks directory not found"; \
		exit 1; \
	fi
	@git config core.hooksPath .githooks || true
	@echo "✓ Git hooks configured (hooks will run from .githooks/)"

# Run all tests
test:
	uv sync --all-packages --group dev
	uv run pytest

# Run unit tests only
test-unit:
	uv sync --all-packages --group dev
	uv run pytest -m unit

# Run integration tests only
test-integration:
	uv sync --all-packages --group dev
	uv run pytest -m integration

# Run unit tests with coverage
test-cov:
	uv sync --all-packages --group dev
	uv run pytest -m unit --cov=. --cov-report=html --cov-report=term

# Lint code
lint:
	uv sync --all-packages --group dev
	uv run ruff check --fix .

# Format code
format:
	uv sync --all-packages --group dev
	uv run black .
	uv run ruff check --fix .

# App targets
app-install:
	cd app && pnpm install

app-dev:
	cd app && pnpm dev

app-build:
	cd app && pnpm build

