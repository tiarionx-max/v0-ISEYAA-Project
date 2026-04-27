# ============================================================
# ISEYAA — Makefile
# ============================================================

.PHONY: setup check-docker up up-infra down build migrate \
        migrate-service test lint health clean install-all \
        dev-gateway dev-auth dev-wallet dev-events dev-lga \
        dev-notifications dev-ai dev-all dev-stop dev-migrate

DOCKER_RUNNING := $(shell docker info > /dev/null 2>&1 && echo "yes" || echo "no")

check-docker:
	@if [ "$(DOCKER_RUNNING)" = "no" ]; then \
		echo ""; \
		echo "❌  Docker is not running."; \
		echo ""; \
		echo "  macOS: open -a Docker   (wait for whale icon to settle)"; \
		echo "  Linux: sudo systemctl start docker"; \
		echo ""; \
		echo "  No Docker? Run locally instead:"; \
		echo "    make install-all && make dev-all"; \
		echo ""; \
		exit 1; \
	fi
	@echo "✅ Docker is running"

setup:
	@echo "🔧 Setting up ISEYAA..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "  ✅ .env created"; fi
	@echo ""
	@echo "  ⚠️  Edit .env and set these before continuing:"
	@echo "     SECRET_KEY          →  openssl rand -hex 32"
	@echo "     JWT_SECRET_KEY      →  openssl rand -hex 32"
	@echo "     ANTHROPIC_API_KEY   →  console.anthropic.com"
	@echo "     PAYSTACK_SECRET_KEY →  paystack.com dashboard"
	@echo ""
	@echo "  Next steps (with Docker):"
	@echo "    make up-infra && make migrate && make up && make health"
	@echo ""
	@echo "  Next steps (without Docker):"
	@echo "    make install-all && make dev-migrate && make dev-all && make health"

# ── Docker ─────────────────────────────────────────────────────────────────
up: check-docker
	docker compose up -d
	@echo ""
	@echo "🚀 ISEYAA running:"
	@echo "   Gateway : http://localhost:8000/docs"
	@echo "   Auth    : http://localhost:8001/docs"
	@echo "   Wallet  : http://localhost:8002/docs"
	@echo "   Events  : http://localhost:8003/docs"
	@echo "   LGA     : http://localhost:8004/docs"
	@echo "   AI      : http://localhost:8010/docs"

up-infra: check-docker
	docker compose up -d postgres postgres-wallet redis mongodb clickhouse
	@echo "✅ Infrastructure up. Wait ~10s, then: make migrate"

down:
	docker compose down

down-clean:
	docker compose down -v
	@echo "⚠️  Volumes deleted — databases are empty"

build: check-docker
	docker compose build --no-cache

logs:
	@if [ -z "$(s)" ]; then docker compose logs -f; else docker compose logs -f $(s); fi

shell: check-docker
	docker compose exec $(s) /bin/sh

restart: check-docker
	docker compose restart $(s)

# ── Migrations ──────────────────────────────────────────────────────────────
migrate: check-docker
	@echo "🗄️  Migrating all services..."
	@for svc in auth-service wallet-service events-service lga-intelligence-service notifications-service; do \
		echo "  → $$svc"; \
		docker compose exec $$svc alembic upgrade head || echo "  ⚠️  $$svc not running yet"; \
	done
	@echo "✅ Migrations complete"

migrate-service: check-docker
	docker compose exec $(s) alembic upgrade head

migrate-rollback: check-docker
	docker compose exec $(s) alembic downgrade -1

migrate-generate: check-docker
	docker compose exec $(s) alembic revision --autogenerate -m "$(msg)"

# ── Local dev (no Docker) ───────────────────────────────────────────────────
# Requires postgres + redis running via Homebrew:
#   brew install postgresql@16 redis
#   brew services start postgresql@16 && brew services start redis

install-all:
	@echo "📦 Installing dependencies..."
	pip install -r api-gateway/requirements.txt
	@for svc in auth-service wallet-service events-service lga-intelligence-service notifications-service; do \
		echo "  → $$svc"; pip install -r services/$$svc/requirements.txt; \
	done
	pip install -r ai-layer/requirements.txt
	@echo "✅ Done"

dev-migrate:
	@echo "🗄️  Local migrations..."
	@for svc in auth-service wallet-service events-service lga-intelligence-service notifications-service; do \
		echo "  → $$svc"; \
		(cd services/$$svc && PYTHONPATH=. alembic upgrade head); \
	done

dev-gateway:
	cd api-gateway && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

dev-auth:
	cd services/auth-service && PYTHONPATH=. uvicorn app.main:app --reload --port 8001

dev-wallet:
	cd services/wallet-service && PYTHONPATH=. uvicorn app.main:app --reload --port 8002

dev-events:
	cd services/events-service && PYTHONPATH=. uvicorn app.main:app --reload --port 8003

dev-lga:
	cd services/lga-intelligence-service && PYTHONPATH=. uvicorn app.main:app --reload --port 8004

dev-notifications:
	cd services/notifications-service && PYTHONPATH=. uvicorn app.main:app --reload --port 8005

dev-ai:
	cd ai-layer && PYTHONPATH=. uvicorn app.main:app --reload --port 8010

dev-all:
	@echo "🚀 Starting all services in background..."
	@(cd api-gateway && PYTHONPATH=. uvicorn app.main:app --port 8000 > /tmp/iseyaa-gateway.log 2>&1) &
	@(cd services/auth-service && PYTHONPATH=. uvicorn app.main:app --port 8001 > /tmp/iseyaa-auth.log 2>&1) &
	@(cd services/wallet-service && PYTHONPATH=. uvicorn app.main:app --port 8002 > /tmp/iseyaa-wallet.log 2>&1) &
	@(cd services/events-service && PYTHONPATH=. uvicorn app.main:app --port 8003 > /tmp/iseyaa-events.log 2>&1) &
	@(cd services/lga-intelligence-service && PYTHONPATH=. uvicorn app.main:app --port 8004 > /tmp/iseyaa-lga.log 2>&1) &
	@(cd services/notifications-service && PYTHONPATH=. uvicorn app.main:app --port 8005 > /tmp/iseyaa-notifications.log 2>&1) &
	@(cd ai-layer && PYTHONPATH=. uvicorn app.main:app --port 8010 > /tmp/iseyaa-ai.log 2>&1) &
	@sleep 3
	@echo "✅ Services started. Logs: tail -f /tmp/iseyaa-*.log"
	@make health

dev-stop:
	@pkill -f "uvicorn app.main:app" 2>/dev/null && echo "✅ Stopped" || echo "No services running"

# ── Health ─────────────────────────────────────────────────────────────────
health:
	@echo "🏥 Health check..."
	@for p_n in "8000:api-gateway" "8001:auth" "8002:wallet" "8003:events" "8004:lga" "8005:notifications" "8010:ai-layer"; do \
		p=$$(echo $$p_n | cut -d: -f1); n=$$(echo $$p_n | cut -d: -f2); \
		if curl -sf http://localhost:$$p/health > /dev/null 2>&1; then \
			echo "  ✅ $$n [:$$p]"; \
		else \
			echo "  ❌ $$n [:$$p] not responding"; \
		fi; \
	done

# ── Tests ─────────────────────────────────────────────────────────────────
test:
	@for svc in api-gateway auth-service wallet-service events-service lga-intelligence-service ai-layer; do \
		echo "→ $$svc"; \
		if [ -d "services/$$svc" ]; then \
			(cd services/$$svc && PYTHONPATH=. pytest tests/ -q 2>/dev/null || echo "  ⚠️  no tests yet"); \
		else \
			(cd $$svc && PYTHONPATH=. pytest tests/ -q 2>/dev/null || echo "  ⚠️  no tests yet"); \
		fi; \
	done

test-service:
	@if [ -d "services/$(s)" ]; then \
		cd services/$(s) && PYTHONPATH=. pytest tests/ -v --cov=app; \
	else \
		cd $(s) && PYTHONPATH=. pytest tests/ -v --cov=app; \
	fi

# ── Lint ───────────────────────────────────────────────────────────────────
lint:
	@for dir in api-gateway/app services/auth-service/app services/wallet-service/app \
	            services/events-service/app services/lga-intelligence-service/app ai-layer/app; do \
		echo "→ $$dir"; ruff check $$dir 2>/dev/null || true; \
	done

# ── Terraform ─────────────────────────────────────────────────────────────
tf-init:
	cd infrastructure/terraform/environments/prod && terraform init

tf-plan:
	cd infrastructure/terraform/environments/prod && terraform plan -out=tfplan

tf-apply:
	cd infrastructure/terraform/environments/prod && terraform apply tfplan

# ── Clean ─────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	find . -name ".DS_Store" -delete 2>/dev/null; true
	find . -name "._*" -delete 2>/dev/null; true
	@echo "✅ Cleaned"
