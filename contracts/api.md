# REST-контракт бэкенда

**Владельцы:** TL (реализует), FE и бот (потребляют). Правки — через TL.

Базовый префикс — `/api`. Формат — JSON, UTF-8. Аутентификации нет:
задание прямо разрешает однопользовательский режим (п. 2.2), и лишний
экран входа только мешал бы эксперту пройти сценарии.

Состояние документа живёт на сервере. Клиент создаёт документ, опрашивает
его статус и в конце просит файл — ни текст, ни реквизиты на клиенте не
пересобираются.

---

## 1. Справочники

### `GET /api/doc-types`

Четыре обязательных типа в фиксированном порядке. Источник —
`src/modules/documents/config/doc_types/*.yaml`.

```json
[
  {
    "id": "memo",
    "name": "Служебная записка",
    "description": "Внутренний документ с просьбой или предложением",
    "requisites": [
      {"key": "addressee", "label": "Адресат", "required": true},
      {"key": "author", "label": "Автор", "required": true},
      {"key": "position", "label": "Должность автора", "required": true},
      {"key": "doc_date", "label": "Дата документа", "required": true},
      {"key": "reg_number", "label": "Номер документа", "required": true},
      {"key": "subject", "label": "Заголовок", "required": true},
      {"key": "signature", "label": "Подпись", "required": true},
      {"key": "executor", "label": "Исполнитель и телефон", "required": false}
    ]
  }
]
```

Канонические ключи реквизитов — общие для всех типов, набор и
обязательность задаёт тип:

| Ключ | Что это | Автозаполнение |
|---|---|---|
| `addressee` | адресат: должность, ФИО, организация | нет |
| `author` | автор, составитель или отправитель | нет |
| `position` | должность автора отдельной строкой | нет |
| `doc_date` | дата документа, `ДД.ММ.ГГГГ` | да, текущая дата |
| `reg_number` | регистрационный номер | нет |
| `subject` | заголовок или тема | нет |
| `signature` | И.О. Фамилия в блоке подписи | нет |
| `salutation` | обращение («Уважаемый …!») | нет |
| `executor` | исполнитель и телефон | нет |

Состав по типам:

| Тип | Обязательные | Необязательные |
|---|---|---|
| `memo` | addressee, author, position, doc_date, reg_number, subject, signature | executor |
| `report` | addressee, author, position, doc_date, reg_number, subject, signature | executor |
| `reference` | subject, doc_date, author, signature | addressee |
| `letter` | addressee, author, position, doc_date, reg_number, subject, signature | salutation, executor |

Таблица сверяется автоматически: `python scripts/check_doc_types_table.py`
падает, если в YAML появился ключ, которого нет в этом файле.

### `GET /api/templates`

```json
{
  "templates": [
    {
      "id": "classic",
      "name": "Классический корпоративный",
      "description": "Times New Roman 14 pt; поля 30/15/20/20 мм …",
      "available": true
    }
  ]
}
```

`description` собирается из `rules.yaml` программно — это не рукописный
текст, а перечисление фактических параметров шаблона.

`available: false` означает, что папка шаблона повреждена: карточка
показывается неактивной, а не исчезает молча.

### `POST /api/templates/upload`

`multipart/form-data`, поле `file` — DOCX. Расширение сверх обязательного
минимума (п. 1.6 задания).

- `201` — `{"id", "name", "rules", "warnings"}`
- `413` — файл больше 10 МБ
- `422` — файл не DOCX
- `503` — каталог пользовательских шаблонов недоступен для записи

`warnings` перечисляет всё, что не удалось вычитать из файла и заменено
значением по умолчанию. Расположение реквизитов из DOCX не выводится —
берётся раскладка классического шаблона, её можно поправить в `rules.yaml`.

---

## 2. Жизненный цикл документа

### `POST /api/documents`

```json
{"draft": "текст черновика", "doc_type": "memo", "template_id": "classic"}
```

- `202` — документ создан, обработка запущена в фоне. Тело — тот же объект,
  что и у `GET /api/documents/{id}`, со `status: "processing"`.
- `422` — пустой черновик, неизвестный тип или неизвестный шаблон.

Черновик не изменяется никогда: сценарий 6 требует, чтобы после ошибки ИИ
исходный текст остался на месте.

### `GET /api/documents/{id}`

```json
{
  "id": "3f2b9c10-…",
  "status": "processed",
  "stage": null,
  "doc_type": "memo",
  "template_id": "classic",
  "draft": "кароче надо бы купить три компа…",
  "improved_text": "Прошу выделить средства на закупку трёх компьютеров…",
  "changes": [{"type": "style", "from": "кароче", "to": ""}],
  "requisites": [
    {
      "key": "addressee",
      "label": "Адресат",
      "value": "Генеральному директору ООО «Ромашка» Иванову И.И.",
      "status": "found_in_draft",
      "required": true
    }
  ],
  "fact_guard": {
    "verdict": "clean",
    "preserved": ["180 000 рублей"],
    "lost": [],
    "added": [],
    "inverted": [],
    "source_count": 3,
    "preserved_count": 3
  },
  "is_fallback": false,
  "reason_code": null,
  "error": null
}
```

`status`:

| Значение | Что произошло | Что показывает интерфейс |
|---|---|---|
| `processing` | пайплайн идёт, заполнено `stage` | прогресс с текущей стадией |
| `processed` | ИИ отработал штатно | результат |
| `degraded` | ИИ недоступен, сработала резервная обработка | результат плюс плашка с причиной |
| `failed` | обработать не удалось, заполнено `error` | экран ошибки с целым черновиком |

`stage` — `llm`, `fact_guard` или `validation`; `null` в терминальных статусах.

`status` реквизита:

| Значение | Смысл |
|---|---|
| `found_in_draft` | значение было в черновике |
| `user_provided` | пользователь вписал руками |
| `auto_filled` | система подставила достоверное (дата формирования) |
| `missing` | значения нет — в документе будет `[Метка]` |
| `left_blank` | пользователь осознанно оставил пустым |

`reason_code` заполняется только при `degraded` и объясняет, почему
результат резервный: `model_unavailable`, `schema_invalid`,
`facts_unverified`, `empty_text` (contracts/llm_contract.md §2).

`error` при `failed`: `{"code", "message", "recoverable"}`, где `code` —
`llm_unavailable`, `timeout` или `internal`. `message` — готовый текст для
пользователя, придумывать свой на клиенте не нужно.

- `404` — документа нет.

### `PATCH /api/documents/{id}/requisites`

```json
{"values": {"addressee": "Генеральному директору ООО «Ромашка» Иванову И.И."}}
```

Заполняет недостающие реквизиты (сценарий 3). Пустая строка или `null` —
осознанный отказ заполнять: реквизит получает статус `left_blank` и
попадёт в документ явной пометкой.

Решение пользователя сильнее модели: повторная обработка не перезаписывает
ключи со статусом `user_provided` и `left_blank`.

- `200` — обновлённый документ.
- `404` — документа нет.
- `409` — документ ещё обрабатывается.

### `PATCH /api/documents/{id}/text`

```json
{"improved_text": "Прошу выделить средства на закупку трёх компьютеров…"}
```

Ручная правка улучшенного текста перед скачиванием (сценарий 7, он же
дополнительный). Модель повторно не вызывается: меняется только то, что
уйдёт в файл.

Fact Guard по правке не проходит осознанно: он защищает от выдумок модели,
а не запрещает человеку дописать в свой документ то, что он знает.
Правка попадает в журнал обработки стадией `user_edit`.

- `200` — обновлённый документ.
- `404` — документа нет.
- `409` — документ ещё обрабатывается или текст ещё не сформирован.
- `422` — пустой текст.

### `POST /api/documents/{id}/reprocess`

Повторяет обработку того же черновика, минуя кэш. Нужен после
восстановления ИИ (сценарий 6).

- `202` — обработка запущена.
- `409` — документ уже обрабатывается.

### `POST /api/documents/{id}/render`

Возвращает готовый `.docx` (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

- `200` — файл.
- `404` — документа нет.
- `409` — документ в статусе `processing` или `failed`.

Заголовки ответа:

| Заголовок | Когда | Значение |
|---|---|---|
| `Content-Disposition` | всегда | `attachment; filename="sluzhebnaya-zapiska-13-09-2026.docx"` |
| `X-Template-Fallback` | шаблон был повреждён | `true` |
| `X-Template-Fallback-Reason` | вместе с предыдущим | причина, **процент-закодированная** |

**Важно для фронта:** значение `X-Template-Fallback-Reason` закодировано
`encodeURIComponent`-совместимо и требует `decodeURIComponent()` перед
показом. Заголовки HTTP ограничены latin-1 (RFC 7230), и сырая кириллица
в значении роняет весь ответ на уровне ASGI-сервера ещё до отправки.

Пример: `X-Template-Fallback-Reason: %D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD…`
разворачивается в «Шаблон «modern» повреждён, применён «classic»».

---

## 3. Проверяемость и демонстрация

### `GET /api/trace/{id}`

Журнал обработки по попыткам: что ушло в ИИ, что вернулось, что решил
Fact Guard, что решил валидатор, был ли ответ взят из кэша, сколько заняла
каждая стадия и какая версия модели отвечала.

Это доказательство для критерия 4.4 «техническая проверяемость»: эксперт
видит внутреннюю логику, не залезая в логи контейнера.

```json
[
  {
    "attempt_id": "…",
    "input": {"sha256": "…", "length": 212},
    "doc_type": "memo",
    "prompt_version": "1.0.0",
    "model_version": "qwen2.5:7b-instruct",
    "outcome": "processed",
    "total_duration_ms": 18432.5,
    "stages": [
      {"stage": "llm_request", "payload": {"…": "…"}, "duration_ms": null},
      {"stage": "llm_result", "payload": {"…": "…"}, "duration_ms": 18201.4},
      {"stage": "fact_guard", "payload": {"verdict": "clean"}, "duration_ms": null},
      {"stage": "validation", "payload": {"missing": ["reg_number"]}, "duration_ms": null},
      {"stage": "render", "payload": {"template_id": "classic"}, "duration_ms": null}
    ]
  }
]
```

Журнал держится в памяти процесса: он нужен для проверки и демонстрации,
переживать перезапуск не обязан.

### `GET /api/dev/state`

```json
{
  "ai_force_failure": false,
  "ml_service_url": "http://ml_service:8100",
  "ml_reachable": true,
  "model_version": "qwen2.5:7b-instruct",
  "templates_loaded": ["classic", "modern"]
}
```

Проверяется перед демонстрацией: видно, поднята ли модель и какие шаблоны
подхватились.

### `POST /api/dev/break-ai`

```json
{"enabled": true}
```

Включает имитацию отказа ИИ для текущей сессии (cookie) — так сценарий 6
показывается без остановки контейнера. Настоящую недоступность модели
проверяют иначе: `docker compose stop ml_service`.

---

## 4. Служебные эндпоинты

| Метод | Путь | Ответ |
|---|---|---|
| `GET` | `/health` | `{"status": "success"}` |
| `GET` | `/health/db` | `{"database": "ok"}` |
| `GET` | `/health/redis` | `{"redis": "ok"}` |

---

## 5. Ошибки

Любая ошибка возвращает `{"detail": "текст на русском"}`. Необработанное
исключение превращается в `500` с текстом «Внутренняя ошибка сервиса» —
стектрейс наружу не уходит (сценарий 6).
