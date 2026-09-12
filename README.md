# Hackathon Template

Универсальный каркас веб-приложения: FastAPI + PostgreSQL + Redis + React,
с авторизацией, миграциями, кэшем, событийной шиной и деплоем «из коробки».

Шаблон общего назначения — предметной логики в нём нет намеренно.

---

# Doc3 — ИИ-помощник делопроизводителя

Сервис принимает черновик делового документа на естественном языке,
исправляет орфографию, пунктуацию и стиль, извлекает реквизиты,
проверяет сохранность фактов и формирует готовый DOCX по выбранному шаблону оформления.

Модель работает **локально** (Ollama + qwen2.5:7b-instruct), без внешних API.

---

## Быстрый старт

```bash
cp .env.example .env

make up              # app + db + redis + frontend + ollama + ml_service
make pull-model      # ⚠️ скачать веса модели (~5 ГБ, один раз)
make migrate         # применить миграции
make smoke           # end-to-end проверка: создать документ → дождаться → скачать DOCX

- Backend: http://localhost:8000 — Swagger на `/docs`
- Frontend: http://localhost:3000
- ML-сервис: http://localhost:8100/docs

Проверка живости: `/health`, `/health/db`, `/health/redis`.

С Kafka и воркерами (медленнее на старте, нужно не всегда):

```bash
make up-events
```

## Команды

| Команда | Что делает |
|---|---|
| `make up` / `make up-events` | Поднять стек без Kafka / с Kafka |
| `make down` / `make down-v` | Остановить / остановить и снести тома |
| `make logs` / `make ps` | Логи / статус контейнеров |
| `make test` / `make lint` / `make format` | Тесты, ruff check, ruff format |
| `make migration name=add_x` | Сгенерировать миграцию |
| `make migrate` / `make downgrade` | Применить / откатить миграцию |
| `make admin` | Создать администратора |
| `make ml-test` | Тесты ML-сервиса |
| `make shell` / `make db-shell` | Шелл в контейнере / psql |

---

## Структура

```
src/
  core/            конфиг, логирование, security
  modules/         бизнес-модули (сейчас: users, auth)
    <module>/
      api/         роутеры, схемы, зависимости
      application/ commands, queries, handlers, ports, read_models
      domain/      сущности, value objects, исключения
      infra/       ORM-модели, репозитории
  shared/
    application/   Mediator, протокол UnitOfWork
    domain/        Money и общие исключения
    events/        IntegrationEvent
    infra/
      database/    сессия, UoW, healthcheck
      redis/       клиент, json-кэш, rate limiter
      kafka/       producer, consumer, DLQ
    outbox/        транзакционный Outbox
  workers/         outbox_publisher, event_consumer
migrations/        Alembic
tests/             unit / api / e2e
frontend/          React + Vite + TS (FSD)
ml_service/        независимый ML-сервис (свои зависимости и контейнер)
infra/ansible/     деплой
```

## Что уже готово

**Авторизация.** JWT в HttpOnly-куке, регистрация по admin-коду, rate limiting
логина и регистрации через Redis, bcrypt.

**Слои.** CQRS: команды и запросы разделены, обработчики через Mediator,
репозитории за портами, транзакции через UnitOfWork.

**Инфраструктура.** Redis-кэш и rate limiter, Kafka producer/consumer с DLQ и
ретраями, транзакционный Outbox с воркером-публикатором.

**Фронтенд.** UI-кит (Button, Input, Select, Textarea, Loading, EmptyState,
ErrorMessage, ErrorBoundary, StatusBadge), api-клиент с разбором ошибок,
провайдеры темы, языка и тостов, ProtectedRoute, дизайн-токены в `global.css`.

**ML-сервис.** Отдельный контейнер с зафиксированным контрактом, работает и без
обученной модели. Подробности — `ml_service/README.md` и `ml_service/TASK.md`.

---

## Как добавить модуль

1. Создай `src/modules/<name>/` по структуре из `users`.
2. ORM-модель — в `infra/models.py`, **обязательно импортируй её в
   `migrations/env.py`**, иначе autogenerate её не увидит.
3. Репозиторий добавь в оба файла UnitOfWork: протокол
   (`shared/application/unit_of_work.py`) и реализацию
   (`shared/infra/database/unit_of_work.py`). Правятся вместе.
4. Роутер подключи в `src/main.py`.
5. Новый URL-префикс пропиши в `frontend/nginx.local.conf` и `vite.config.ts`,
   иначе запрос уйдёт в SPA вместо API.
6. `make migration name=add_<name>` и `make migrate`.

Тест `tests/unit/infra/test_uow.py` проверяет состав UoW — допиши туда assert,
чтобы расхождение протокола и реализации ловилось сразу.

## Секреты

`.env` и `infra/ansible/inventory/group_vars/*/secrets.yml` в репозиторий не
попадают. Шаблоны — `.env.example` и `secrets.yml.example`. TLS-ключи для
локальной разработки генерируются через `make cert`.
