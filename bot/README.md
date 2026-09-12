# MAX-бот для сервиса документов

Изолированный Python 3.12-сервис: получает черновик в MAX, предлагает тип
документа и доступный шаблон, вызывает существующий HTTP API, ждёт терминального
статуса и возвращает готовый DOCX. Код и файлы монолита бот не импортирует,
база данных ему не нужна.

Выбран полностью асинхронный `httpx`: long polling не блокируется во время
создания документа; варианты показываются нумерованным списком, чтобы сценарий
не зависел от callback-кнопок MAX.

## Архитектура

```text
app/main.py          orchestration, long polling, команды и фоновые задания
app/conversation.py  конечный автомат и состояние по chat_id в памяти
app/max_client.py    граница MAX API, лимит отправки, upload и ретраи
app/doc_api.py       типизированная граница API документов и polling
app/config.py        единственная точка чтения и проверки переменных окружения
```

Каждый документ обрабатывается отдельной `asyncio`-задачей. Цикл MAX продолжает
принимать апдейты, а число одновременных обработок ограничено. Ошибка одного
чата не завершает процесс. `/cancel` отменяет задание. После перезапуска
состояние диалогов теряется намеренно — это требование режима без БД.

## Получение токена MAX

По актуальной документации MAX токен создаётся и копируется на
[платформе MAX для бизнеса](https://business.max.ru/) в разделе «Чат-боты»:
откройте настройки нужного бота и скопируйте поле с токеном. Для профилей,
созданных через мини-приложение «MAX для бизнеса», токен доступен там же. Если
в вашем аккаунте ещё используется старый сценарий `@MasterBot`, полученный там
токен подходит как `MAX_BOT_TOKEN`.

Не передавайте токен в URL и не коммитьте `.env`: MAX принимает его как
`Authorization: <token>`.

## Переменные окружения

Обязательные:

| Переменная | Пример | Назначение |
| --- | --- | --- |
| `MAX_BOT_TOKEN` | `…` | токен бота |
| `API_BASE_URL` | `http://app:8000` | адрес существующего сервиса документов |

Опциональные:

| Переменная | По умолчанию | Назначение |
| --- | ---: | --- |
| `MAX_LONG_POLL_TIMEOUT_SECONDS` | `30` | серверный таймаут `/updates`, 1–90 с |
| `API_REQUEST_TIMEOUT_SECONDS` | `15` | таймаут отдельного HTTP-запроса |
| `DOCUMENT_POLL_INTERVAL_SECONDS` | `1.5` | интервал проверки статуса |
| `DOCUMENT_PROCESSING_TIMEOUT_SECONDS` | `120` | общий предел ожидания документа |
| `HTTP_MAX_ATTEMPTS` | `4` | максимум попыток сетевой операции |
| `HTTP_RETRY_BACKOFF_SECONDS` | `0.5` | начальная пауза экспоненциального backoff |
| `MAX_ATTACHMENT_READY_ATTEMPTS` | `6` | попытки при `attachment.not.ready` |
| `MAX_CONCURRENT_JOBS` | `8` | одновременно создаваемые документы |
| `MAX_SKIP_PENDING_UPDATES` | `true` | не повторять последний апдейт после рестарта |
| `LOG_LEVEL` | `INFO` | уровень журналирования |

## Подключение к текущему docker-compose

Добавьте `MAX_BOT_TOKEN=...` в корневой `.env` и вставьте этот сервис в секцию
`services` существующего `docker-compose.yml`:

```yaml
  bot:
    build:
      context: ./bot
    environment:
      MAX_BOT_TOKEN: ${MAX_BOT_TOKEN}
      API_BASE_URL: http://app:8000
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy
```

Порты и volume не нужны: бот сам обращается к MAX наружу и видит `app` через
общую compose-сеть.

Запуск из корня проекта:

```bash
docker compose up -d --build bot
docker compose logs -f bot
```

Long polling работает, только когда у бота нет активной webhook-подписки.
Официальная документация MAX считает long polling режимом разработки и
тестирования; здесь он используется осознанно для хакатон-стенда без публичного
HTTPS. Базовый адрес и параметры сверены с документацией
[`GET /updates`](https://dev.max.ru/docs-api/methods/GET/updates),
[`POST /messages`](https://dev.max.ru/docs-api/methods/POST/messages) и
[`POST /uploads`](https://dev.max.ru/docs-api/methods/POST/uploads).

## Проверка

Юнит-тесты не требуют MAX или запущенного монолита:

```bash
cd bot
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Полный технический прогон против запущенного API документов (токен MAX не
нужен):

```bash
cd bot
API_BASE_URL=http://localhost:8000 python test_manual.py
```

Скрипт получает справочники, проходит конечный автомат, создаёт документ,
дожидается результата, проверяет ZIP-сигнатуру DOCX и сохраняет
`manual-result.docx`. Тип, шаблон и выходной путь можно переопределить через
`MANUAL_DOC_TYPE`, `MANUAL_TEMPLATE_ID`, `MANUAL_OUTPUT_PATH`.

Для проверки в MAX откройте бота, нажмите Start или отправьте `/start`, затем
пришлите черновик, выберите номер типа и номер шаблона. При `processed` или
`degraded` бот пришлёт DOCX; недостающие обязательные реквизиты перечислит
отдельным сообщением, но файл всё равно отдаст.
