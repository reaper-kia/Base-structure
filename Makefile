.PHONY: up up-events down down-v build restart logs ps shell db-shell test lint format tree migration migrate downgrade cert ml-test

migration:
	docker compose exec app alembic revision --autogenerate -m "$(name)"

migrate:
	docker compose exec app alembic upgrade head

downgrade:
	docker compose exec app alembic downgrade -1

up:
	docker compose up --build -d

# С Kafka и воркерами (медленнее на старте)
up-events:
	docker compose --profile events up --build -d

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
