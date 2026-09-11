# Контракты

Правки только через тимлида. Пока файл не зафиксирован — логику по нему не пишем.

- `api.md` — REST-контракт бэкенда (TL + FE)
- `llm_schema.json` — что возвращает ml_service (ML + TL)
- `template_format.md` — формат rules.yaml (B2 + TL)

## Кто владеет чем

| Папка | Владелец |
|---|---|
| `src/modules/documents` | TL |
| `src/modules/templates` | B2 |
| `ml_service` | ML |
| `frontend/src` | FE |
| `frontend/src/app/styles` | UI -> FE |

Общие файлы (правит только TL): `src/main.py`, `src/core/config.py`,
`src/shared/**`, `migrations/env.py`, `docker-compose.yml`.
