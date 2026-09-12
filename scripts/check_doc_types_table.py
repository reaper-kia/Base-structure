import sys
from pathlib import Path

import yaml

DOCS_DIR = Path("src/modules/documents/config/doc_types")
API_MD = Path("contracts/api.md")


def load_doc_types() -> dict[str, dict]:
    """Читает все YAML-конфиги типов документов."""
    types = {}
    for p in sorted(DOCS_DIR.glob("*.yaml")):
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        types[p.stem] = data
    return types


def generate_table(types: dict[str, dict]) -> str:
    """Генерирует Markdown-таблицу типов и реквизитов."""
    lines = [
        "| Тип | Обязательные | Необязательные | Всего |",
        "|---|---|---|---|",
    ]
    for doc_id, data in types.items():
        reqs = data.get("requisites", [])
        req = [r["key"] for r in reqs if r.get("required")]
        opt = [r["key"] for r in reqs if not r.get("required")]
        lines.append(
            f"| {doc_id} | {', '.join(req)} | {', '.join(opt) or '—'} | {len(reqs)} |"
        )
    return "\n".join(lines)


def check_contract(types: dict[str, dict], api_content: str) -> list[str]:
    """Проверяет, что все ключи из YAML упомянуты в api.md."""
    missing = []
    for doc_id, data in types.items():
        for r in data.get("requisites", []):
            # Ищем ключ в разделе канонических ключей или в примерах
            if f"`{r['key']}`" not in api_content and r["key"] not in api_content:
                missing.append(f"{doc_id}:{r['key']}")
    return missing


if __name__ == "__main__":
    if not DOCS_DIR.exists():
        print(f"Ошибка: директория {DOCS_DIR} не найдена")
        sys.exit(1)

    types = load_doc_types()
    table = generate_table(types)

    print("Сгенерированная таблица из YAML (для вставки в README/api.md):")
    print(table)
    print("-" * 40)

    if not API_MD.exists():
        print(f"Предупреждение: {API_MD} не найден, пропуск сверки")
        sys.exit(0)

    api_content = API_MD.read_text(encoding="utf-8")
    missing_keys = check_contract(types, api_content)

    if missing_keys:
        print(f"Ошибка: следующие ключи отсутствуют в {API_MD}:")
        for k in missing_keys:
            print(f"  - {k}")
        print("Обновите раздел 1.4 (Канон ключей) в contracts/api.md")
        sys.exit(1)
    else:
        print(f"Успех: все ключи из YAML найдены в {API_MD}")
        sys.exit(0)
