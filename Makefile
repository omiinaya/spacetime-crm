# SpacetimeCRM — Makefile
# Targets for development, testing, linting, and deployment.

.PHONY: help build test lint fmt fix dev-up dev-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Build ─────────────────────────────────────────────────────────────

build: ## Build all artifacts (STDB wasm + frontend dist)
	cargo build --release --target wasm32-unknown-unknown --manifest-path server/spacetimedb/Cargo.toml
	cd web && npm ci && npm run build

build-stdb: ## Build only the STDB Rust module
	cargo build --release --target wasm32-unknown-unknown --manifest-path server/spacetimedb/Cargo.toml

build-web: ## Build only the frontend
	cd web && npm ci && npm run build

# ── Test ──────────────────────────────────────────────────────────────

test: ## Run all tests (currently none exist — placeholder)
	@echo "⚠️  No test suite configured yet. Add pytest and vitest targets."
	@echo "   Python:  pytest server/"
	@echo "   Frontend: vitest run (requires @vitest/runner dependency)"

test-server: ## Run Python backend tests (if pytest configured)
	@if command -v pytest >/dev/null 2>&1; then \
		pytest server/ -v; \
	else \
		echo "⚠️  pytest not installed. Run: pip install pytest"; \
	fi

test-web: ## Run frontend tests (if vitest configured)
	@if [ -f web/node_modules/.bin/vitest ]; then \
		cd web && npx vitest run; \
	else \
		echo "⚠️  vitest not found. Install: cd web && npm install -D vitest"; \
	fi

# ── Lint ──────────────────────────────────────────────────────────────

lint: lint-py lint-rs lint-web ## Run all linters

lint-py: ## Lint Python code (ruff)
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check server/ scripts/; \
	else \
		echo "⚠️  ruff not installed. Run: pip install ruff"; \
	fi

lint-rs: ## Lint Rust code (clippy)
	cargo clippy --manifest-path server/spacetimedb/Cargo.toml -- -D warnings

lint-web: ## Lint TypeScript/React code
	cd web && npx tsc --noEmit

# ── Format ────────────────────────────────────────────────────────────

fmt: fmt-py fmt-rs fmt-web ## Format all code

fmt-py: ## Format Python code (ruff)
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format server/ scripts/; \
	else \
		echo "⚠️  ruff not installed. Run: pip install ruff"; \
	fi

fmt-rs: ## Format Rust code (rustfmt)
	cargo fmt --manifest-path server/spacetimedb/Cargo.toml

fmt-web: ## Format frontend code (prettier or biome)
	@if [ -f web/node_modules/.bin/prettier ]; then \
		cd web && npx prettier --write src/; \
	elif command -v npx >/dev/null 2>&1 && npx --yes biome --version >/dev/null 2>&1; then \
		cd web && npx @biomejs/biome format --write src/; \
	else \
		echo "⚠️  No formatter found. Install: cd web && npm install -D prettier"; \
	fi

fix: ## Auto-fix lint issues (ruff + cargo fix)
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check --fix server/ scripts/; \
	else \
		echo "⚠️  ruff not installed. Run: pip install ruff"; \
	fi
	cargo fix --manifest-path server/spacetimedb/Cargo.toml --allow-dirty 2>/dev/null || true

# ── Dev Servers ───────────────────────────────────────────────────────

dev-up: ## Start full dev environment (STDB + backend + frontend)
	@echo "┌─────────────────────────────────────────┐"
	@echo "│ Starting SpacetimeCRM dev environment…│"
	@echo "└─────────────────────────────────────────┘"
	@echo ""
	@echo "Step 1: SpacetimeDB (port 3001)"
	@echo "  spacetime start -l 3001"
	@echo ""
	@echo "Step 2: FastAPI backend (port 8723)"
	@echo "  cd server && cp -n .env.example .env 2>/dev/null; python3 main.py"
	@echo ""
	@echo "Step 3: Vite frontend (port 5185)"
	@echo "  cd web && npm run dev"
	@echo ""
	@echo "Open: http://localhost:5185"
	@echo "API:  http://localhost:8723/docs"

dev-down: ## Stop dev services (process kill signals)
	@-pkill -f "spacetime start" 2>/dev/null || true
	@-pkill -f "uvicorn main:app" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	@echo "🛑 Dev services stopped"

# ── Docker ────────────────────────────────────────────────────────────

docker-up: ## Start Docker Compose stack
	docker compose up -d

docker-down: ## Stop Docker Compose stack
	docker compose down

docker-down-clean: ## Stop and remove volumes (wipes STDB data!)
	docker compose down -v

docker-logs: ## Tail logs from all Docker services
	docker compose logs -f

docker-rebuild: ## Rebuild and restart Docker services
	docker compose build --no-cache
	docker compose up -d

# ── Database / STDB ──────────────────────────────────────────────────

publish-stdb: ## Build & publish STDB module to local instance
	./scripts/publish-stdb.sh

seed: ## Seed demo data
	python3 scripts/seed-demo.py

backup: ## Backup all STDB data
	python3 scripts/backup.py

restore: ## Restore from backup (usage: make restore FILE=backups/xxx.gz)
	python3 scripts/restore.py $(FILE)

# ── Clean ─────────────────────────────────────────────────────────────

clean: clean-py clean-rs clean-web clean-docker ## Clean all build artifacts

clean-py: ## Clean Python artifacts
	rm -rf server/__pycache__ scripts/__pycache__ server/**/__pycache__
	rm -f *.pyc

clean-rs: ## Clean Rust/STDB build artifacts
	cargo clean --manifest-path server/spacetimedb/Cargo.toml

clean-web: ## Clean frontend artifacts
	rm -rf web/dist web/node_modules

clean-docker: ## Clean Docker artifacts
	@-docker compose down -v 2>/dev/null || true
	@-docker system prune -f 2>/dev/null || true

clean-all: clean ## Thorough clean including lockfiles
	rm -f web/package-lock.json
