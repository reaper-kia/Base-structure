.PHONY: up down down-v build restart logs ps shell db-shell test lint format tree migration migrate downgrade cert ml-test pull-model models smoke smoke-prod

OLLAMA_MODEL ?= qwen2.5:7b-instruct

# Скачать веса LLM. Делается ОДИН раз после первого `make up`:
# ~5 ГБ ложатся в том ollama_models и переживают пересоздание контейнеров.
pull-model:
	docker compose exec ollama ollama pull $(OLLAMA_MODEL)

# Проверить, что веса на месте (перед демо - обязательно).
models:
	docker compose exec ollama ollama list

migration:
	docker compose exec app alembic revision --autogenerate -m "$(name)"

migrate:
	docker compose exec app alembic upgrade head

downgrade:
	docker compose exec app alembic downgrade -1

up:
	docker compose up --build -d

down:
	docker compose down

down-v:
	docker compose down -v

build:
	docker compose build

restart:
	docker compose down
	docker compose up --build

logs:
	docker compose logs -f

ps:
	docker compose ps

shell:
	docker compose exec app bash

db-shell:
	docker compose exec db sh -c \
		'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

test:
	docker compose exec app pytest

lint:
	docker compose exec app ruff check .

format:
	docker compose exec app ruff format .

tree:
	tree -I "__pycache__|.git|.venv|venv|.pytest_cache|.mypy_cache|.ruff_cache"

cert:
	openssl req -x509 -newkey rsa:2048 -sha256 -noenc \
		-keyout certs/localhost.key \
		-out certs/localhost.crt \
		-days 365 \
		-config certs/openssl.cnf

# Тесты ML-сервиса (у него свои зависимости и свой pytest)
ml-test:
	cd ml_service && pytest

# End-to-end smoke-тест: создать документ → дождаться → скачать DOCX
smoke:
	@API_URL=http://localhost:8000 bash scripts/smoke.sh

smoke-prod:
	@if [ -z "$(PROD_URL)" ]; then \
		echo "Usage: make smoke-prod PROD_URL=https://your-stand.com"; \
		exit 1; \
	fi
	@API_URL=$(PROD_URL) bash scripts/smoke.sh