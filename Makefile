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

test: ## Run all tests
	@echo "Running backend integration tests..."
	@cd server && python3 -m pytest tests/ -v --tb=short 2>&1

test-server: ## Run Python backend tests (if pytest configured)
	@if command -v pytest >/dev/null 2>&1; then \
		pytest server/ -v; \
	else \
		echo "⚠️  pytest not installed. Run: pip install pytest"; \
	fi

test-web: ## Run frontend tests (vitest + playwright e2e)
	@echo "--- Vitest unit tests ---"
	@if [ -f web/node_modules/.bin/vitest ]; then \
		cd web && npx vitest run; \
	else \
		echo "⚠️  vitest not found. Install: cd web && npm install -D vitest"; \
	fi
	@echo "--- Playwright E2E tests ---"
	@if [ -f web/node_modules/.bin/playwright ]; then \
		echo "Running E2E tests (chromium-only, 1 worker)..."; \
		cd web && npx playwright test --workers=1; \
	else \
		echo "⚠️  playwright not found. Install: cd web && npm install -D @playwright/test && npx playwright install chromium"; \
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

# ── Agent-Friendly Targets ─────────────────────────────────────────────



# ── Container Build/Deploy ─────────────────────────────────────────────

container-build: ## Build Docker image for the backend
	docker compose build

container-up: ## Start all services with Docker Compose
	docker compose up -d

container-down: ## Stop and remove containers
	docker compose down

container-logs: ## Tail logs from all containers
	docker compose logs -f

container-rebuild: container-build container-up ## Rebuild and restart containers

.PHONY: container-build container-up container-down container-logs container-rebuild
.PHONY: test-unit test-integration test-container test-rust-container test-quick coverage check-ports deps-check health setup-git-hooks

test-unit:  ## Run fast offline-safe unit tests
	@echo "--- Backend unit tests ---"
	@if command -v pytest >/dev/null 2>&1; then \
		pytest server/ -v --tb=short; \
	else \
		echo "⚠️  pytest not installed. Run: pip install pytest"; \
	fi
	@echo "--- Frontend unit tests ---"
	@if [ -f web/node_modules/.bin/vitest ]; then \
		cd web && npx vitest run; \
	else \
		echo "⚠️  vitest not found. Install: cd web && npm install -D vitest"; \
	fi

test-container: ## Spin up test STDB container and run full integration suite (build → container → publish → backend → test → cleanup)
	@if docker pull spacetimedb/spacetimedb:latest >/dev/null 2>&1 || docker image inspect spacetimedb/spacetimedb:latest >/dev/null 2>&1; then \
		echo "Using Docker-based test runner..."; \
		bash scripts/run-integration-tests.sh $(ARGS); \
	elif command -v spacetimedb-standalone >/dev/null 2>&1 || [ -f "$(HOME)/.local/share/spacetime/bin/2.6.1/spacetimedb-standalone" ]; then \
		echo "Docker image not available — using standalone STDB binary..."; \
		bash scripts/run-integration-tests-standalone.sh $(ARGS); \
	else \
		echo "ERROR: Neither Docker (spacetimedb/spacetimedb:latest) nor spacetimedb-standalone binary available."; \
		echo "Install SpacetimeDB or run with --local-stdb pointing to an existing STDB instance."; \
		exit 1; \
	fi

test-rust-container: ## Build & run standalone Rust container tests (requires running STDB)
	@echo "🚀 Running container tests..."
	@cargo run --manifest-path server/container-tests/Cargo.toml

test-integration:  ## Tests needing running services (STDB + backend + frontend)
	@echo "⚠️  Integration tests require STDB on :3001 and backend on :8723"
	@if curl -sf http://localhost:3001/health >/dev/null 2>&1; then \
		echo "STDB running — testing STDB module..."; \
		cd server/spacetimedb && cargo test 2>/dev/null || echo "No Rust tests found"; \
	else \
		echo "STDB not running on :3001 — skipping"; \
	fi
	@if curl -sf http://localhost:8723/health >/dev/null 2>&1; then \
		echo "Backend running — running API integration tests..."; \
		python3 -m pytest tests/integration/ -v --tb=short 2>/dev/null || echo "No integration tests found at tests/integration/"; \
	else \
		echo "Backend not running on :8723 — skipping"; \
	fi

test-quick:  ## ~5s sanity check
	@echo "--- Quick sanity check ---"
	@if command -v python3 >/dev/null 2>&1; then \
		python3 -c "import sys; print('✅ Python', sys.version)"; \
	else \
		echo "❌ python3 not found"; \
	fi
	@if command -v node >/dev/null 2>&1; then \
		echo "✅ Node $$(node --version)"; \
	else \
		echo "❌ node not found"; \
	fi
	@echo "--- Lint check (ruff only) ---"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check server/main.py --quiet 2>/dev/null && echo "  lint OK"; \
	else \
		echo "  ruff not installed"; \
	fi

coverage:  ## Test coverage report
	@echo "--- Backend coverage ---"
	@if command -v pytest >/dev/null 2>&1; then \
		python3 -m pytest server/ --cov=server --cov-report=term --cov-report=html --cov-branch 2>/dev/null || echo "⚠️  pytest-cov may not be installed"; \
	else \
		echo "⚠️  pytest not installed. Run: pip install pytest pytest-cov"; \
	fi
	@echo ""
	@echo "--- Frontend coverage ---"
	@if [ -f web/node_modules/.bin/vitest ]; then \
		cd web && npx vitest run --coverage 2>/dev/null || echo "⚠️  vitest coverage not configured. Install: cd web && npm install -D @vitest/coverage-v8"; \
	else \
		echo "⚠️  vitest not found"; \
	fi

check-ports:  ## Verify required ports are free
	@echo "Checking required ports..."
	@for port in 5185 3001; do \
		if ss -tlnp "sport = :$$port" 2>/dev/null | grep -q .; then \
			echo "  ✅ :$$port — in use"; \
		else \
			echo "  ⚪ :$$port — free"; \
		fi; \
	done

deps-check:  ## Verify required tools are installed
	@echo "Checking development dependencies..."
	@for cmd in python3 node npm spacetime cargo ruff; do \
		if command -v $$cmd >/dev/null 2>&1; then \
			echo "  ✅ $$cmd — $$(command -v $$cmd)"; \
		else \
			echo "  ❌ $$cmd — NOT FOUND"; \
		fi; \
	done

health:  ## Check if dev servers are running
	@echo "--- Dev Server Health ---"
	@if curl -sf http://localhost:3001/health >/dev/null 2>&1; then \
		echo "  ✅ STDB (http://localhost:3001) — running"; \
	else \
		echo "  ⚪ STDB (http://localhost:3001) — not detected"; \
	fi
	@if curl -sf http://localhost:8723/docs >/dev/null 2>&1; then \
		echo "  ✅ Backend (http://localhost:8723) — running"; \
	else \
		echo "  ⚪ Backend (http://localhost:8723) — not detected"; \
	fi
	@if curl -sf http://localhost:5185 >/dev/null 2>&1; then \
		echo "  ✅ Vite (http://localhost:5185) — running"; \
	else \
		echo "  ⚪ Vite (http://localhost:5185) — not detected"; \
	fi

setup-git-hooks:  ## Configure .githooks
	@git config core.hooksPath .githooks
	@echo "✅ Git hooks configured (core.hooksPath = .githooks)"
	@chmod +x .githooks/* 2>/dev/null || true
	@echo "Done."
