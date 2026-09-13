.PHONY: help up down down-v build restart logs ps shell db-shell test lint format \
        migration migrate downgrade cert ml-test ml-gate ml-lint bot-up bot-logs \
        docx-samples demo-drafts pull-model models smoke smoke-prod prod prod-down

OLLAMA_MODEL ?= qwen2.5:7b-instruct
RAG_EMBED_MODEL ?= bge-m3

help: ## Список команд
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------- локальный стек ----------

up: ## Поднять стек (первый запуск: сначала cp .env.example .env)
	docker compose up --build -d

down: ## Остановить стек
	docker compose down

down-v: ## Остановить стек и удалить тома (включая веса модели)
	docker compose down -v

build: ## Пересобрать образы
	docker compose build

restart: ## Перезапустить стек
	docker compose down
	docker compose up --build -d

logs: ## Логи всех сервисов
	docker compose logs -f

ps: ## Состояние контейнеров
	docker compose ps

shell: ## Shell внутри контейнера приложения
	docker compose exec app bash

db-shell: ## psql внутри контейнера базы
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# ---------- модель ----------

pull-model: ## Скачать генеративную и embedding-модель (~6 ГБ)
	docker compose exec ollama ollama pull $(OLLAMA_MODEL)
	docker compose exec ollama ollama pull $(RAG_EMBED_MODEL)

models: ## Проверить, что веса на месте (перед демо — обязательно)
	docker compose exec ollama ollama list

# ---------- миграции ----------

migration: ## Создать миграцию: make migration name="add something"
	docker compose exec app alembic revision --autogenerate -m "$(name)"

migrate: ## Применить миграции
	docker compose exec app alembic upgrade head

downgrade: ## Откатить последнюю миграцию
	docker compose exec app alembic downgrade -1

# ---------- проверки ----------

test: ## Тесты бэкенда
	docker compose exec app pytest

lint: ## Линт бэкенда
	docker compose exec app ruff check src/ tests/ scripts/ migrations/

format: ## Форматирование бэкенда
	docker compose exec app ruff format .

ml-test: ## Тесты ML-сервиса
	docker compose exec ml_service pytest

ml-lint: ## Линт ML-сервиса
	docker compose exec ml_service ruff check src/ tests/ scripts/

ml-gate: ## Гейт качества модели: доля валидных JSON на 21 черновике
	docker compose exec ml_service python scripts/gate.py

smoke: ## Сквозная проверка: создать документ -> дождаться -> скачать DOCX
	@API_URL=http://localhost:8000 bash scripts/smoke.sh

smoke-prod: ## То же против боевого стенда: make smoke-prod PROD_URL=https://...
	@if [ -z "$(PROD_URL)" ]; then \
		echo "Usage: make smoke-prod PROD_URL=https://your-stand.com"; \
		exit 1; \
	fi
	@API_URL=$(PROD_URL) bash scripts/smoke.sh

# ---------- демо-материалы ----------

docx-samples: ## 8 эталонных DOCX (4 типа x 2 шаблона) в artifacts/
	docker compose exec app python scripts/make_docx_samples.py

demo-drafts: ## Пересобрать демо-черновики фронта из стартового пакета
	python3 scripts/sync_demo_drafts.py

# ---------- бот ----------

bot-up: ## Поднять MAX-бота (нужен bot/.env с токеном)
	docker compose --profile bot up -d --build bot

bot-logs: ## Логи бота
	docker compose logs -f bot

# ---------- боевой стек ----------

prod: ## Поднять боевой стек (нужен .env.prod)
	docker compose -f compose.prod.yml up -d --build

prod-down: ## Остановить боевой стек
	docker compose -f compose.prod.yml down

cert: ## Самоподписанный сертификат для локального HTTPS
	openssl req -x509 -newkey rsa:2048 -sha256 -noenc \
		-keyout certs/localhost.key \
		-out certs/localhost.crt \
		-days 365 \
		-config certs/openssl.cnf
