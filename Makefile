# CreatorPulse AI — comandos de desarrollo
#
# Uso rápido con Docker:
#   cp .env.example .env && make up
#
# Uso nativo (requiere PostgreSQL con pgvector y Redis en marcha):
#   make install && make migrate && make dev

SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND := backend
FRONTEND := frontend
VENV := $(BACKEND)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help
help: ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Docker -----------------------------------------------------------------

.PHONY: up
up: ## Levanta todo el sistema con Docker Compose
	docker compose up --build

.PHONY: up-d
up-d: ## Levanta el sistema en segundo plano
	docker compose up --build -d

.PHONY: down
down: ## Para el sistema
	docker compose down

.PHONY: clean-volumes
clean-volumes: ## Para el sistema y BORRA los datos persistidos
	docker compose down -v

.PHONY: logs
logs: ## Muestra los registros de todos los servicios
	docker compose logs -f

.PHONY: compose-check
compose-check: ## Valida docker-compose.yml
	docker compose config --quiet && echo "docker-compose.yml válido"

# --- Instalación local ------------------------------------------------------

.PHONY: install
install: install-backend install-frontend ## Instala todas las dependencias

.PHONY: install-backend
install-backend: ## Crea el entorno virtual e instala el backend
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e '$(BACKEND)[dev]'

.PHONY: install-ml
install-ml: ## Instala los modelos neuronales opcionales (sentence-transformers)
	$(PIP) install -e '$(BACKEND)[ml]'

.PHONY: install-frontend
install-frontend: ## Instala las dependencias del frontend
	cd $(FRONTEND) && npm install

# --- Base de datos ----------------------------------------------------------

.PHONY: migrate
migrate: ## Aplica las migraciones de base de datos
	cd $(BACKEND) && .venv/bin/alembic upgrade head

.PHONY: migration
migration: ## Crea una migración nueva: make migration m="descripción"
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"

.PHONY: downgrade
downgrade: ## Revierte la última migración
	cd $(BACKEND) && .venv/bin/alembic downgrade -1

.PHONY: fixtures
fixtures: ## Regenera los datos de demostración
	python3 scripts/generate_fixtures.py

.PHONY: seed-demo
seed-demo: ## Carga los canales de demostración en la base de datos
	cd $(BACKEND) && .venv/bin/python -m app.cli cargar-demo

.PHONY: status
status: ## Estado de los servicios y recuento de datos
	cd $(BACKEND) && .venv/bin/python -m app.cli estado

.PHONY: purge
purge: ## Aplica la política de retención (usa --simular primero)
	cd $(BACKEND) && .venv/bin/python -m app.cli purgar --simular

# --- Desarrollo -------------------------------------------------------------

.PHONY: api
api: ## Arranca la API en modo recarga automática
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Arranca el worker de análisis
	cd $(BACKEND) && .venv/bin/python -m app.workers.main

.PHONY: web
web: ## Arranca el frontend en modo desarrollo
	cd $(FRONTEND) && npm run dev

# --- Calidad ----------------------------------------------------------------

.PHONY: lint
lint: lint-backend lint-frontend ## Ejecuta todos los linters

.PHONY: lint-backend
lint-backend: ## Linter y formato del backend
	cd $(BACKEND) && .venv/bin/ruff check .
	cd $(BACKEND) && .venv/bin/ruff format --check .

.PHONY: format
format: ## Aplica el formato automático al backend
	cd $(BACKEND) && .venv/bin/ruff check --fix .
	cd $(BACKEND) && .venv/bin/ruff format .

.PHONY: lint-frontend
lint-frontend: ## Linter del frontend
	cd $(FRONTEND) && npm run lint

.PHONY: typecheck
typecheck: ## Comprobación de tipos de backend y frontend
	cd $(BACKEND) && .venv/bin/mypy app
	cd $(FRONTEND) && npm run typecheck

# --- Pruebas ----------------------------------------------------------------

.PHONY: test
test: test-backend test-frontend ## Ejecuta todas las pruebas

.PHONY: test-backend
test-backend: ## Pruebas del backend (unitarias e integración)
	cd $(BACKEND) && .venv/bin/pytest

.PHONY: test-unit
test-unit: ## Sólo las pruebas unitarias del backend
	cd $(BACKEND) && .venv/bin/pytest tests/unit

.PHONY: test-frontend
test-frontend: ## Pruebas de componentes del frontend
	cd $(FRONTEND) && npm test

.PHONY: e2e
e2e: ## Prueba de extremo a extremo (requiere API, worker y frontend en marcha)
	cd $(FRONTEND) && npm run e2e

.PHONY: check
check: lint typecheck test ## Linters + tipos + pruebas
	@echo "Todas las comprobaciones han pasado."
