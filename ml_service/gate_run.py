import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

llm_schema = {
    "type": "object",
    "properties": {
        "improved_text": {"type": ["string", "null"]},
        "addressee": {"type": ["string", "null"]},
        "author": {"type": ["string", "null"]},
        "position": {"type": ["string", "null"]},
        "subject": {"type": ["string", "null"]},
        "doc_date": {"type": ["string", "null"]},
    },
    "required": [
        "improved_text",
        "addressee",
        "author",
        "position",
        "subject",
        "doc_date",
    ],
}

drafts = [
    "прошу отпуск с 15 мая",
    "нужен ремонт принтера, 5000 руб",
    "я работаю тут с 2020",
    "доложите директору Иванову",
    "передай Сидорову про встречу",
    "выдайте новый ноут",
    "прошу уволить по собственному",
    "закупите бумагу 10 пачек",
    "отчет за квартал готов",
    "премия Петрову 10000",
    "надо починить кран",
    "согласовать договор №123",
    "прошу перевести в другой отдел",
    "справка дана для предъявления по месту",
    "направляю акт выполненных работ",
    "заявка на канцтовары",
    "объяснительная по опозданию",
    "служебка на пропуск для авто",
    "прошу оплатить счет от Ромашки",
    "информация о проекте",
]


def run_gate():
    print("🚀 Запускаем Гейт-тест: 20 прогонов (ML-01)...")
    valid_json_count = 0

    for i, draft in enumerate(drafts, 1):
        print(f"Тест {i}/20...", end=" ", flush=True)

        payload = {
            "model": "qwen2.5:7b-instruct",
            "prompt": f"Перепиши в деловом стиле и извлеки реквизиты. Черновик: {draft}",
            "format": llm_schema,
            "stream": False,
            "options": {"temperature": 0.2},
        }

        start_time = time.time()
        try:
            response = requests.post(OLLAMA_URL, json=payload).json()
            parsed_data = json.loads(response.get("response", ""))
            valid_json_count += 1
            print(f"✅ JSON валиден ({round(time.time() - start_time, 1)} сек)")
        except json.JSONDecodeError:
            print("❌ Ошибка: сломанный синтаксис JSON")
        except Exception as e:
            print(f"❌ Ошибка сети: {e}")

    success_rate = (valid_json_count / len(drafts)) * 100
    print("\n" + "=" * 30)
    print(f"ИТОГИ ГЕЙТА: {valid_json_count}/20 ({success_rate}%)")
    print("=" * 30)

    if success_rate >= 90:
        print("Вердикт тимлида: Идем по плану, repair на всякий случай")
    elif success_rate >= 70:
        print("Вердикт тимлида: Repair обязателен, план не меняем")
    else:
        print("Вердикт тимлида: НЕМЕДЛЕННО ПИШИ В ЧАТ, ПЕРЕХОДИМ НА ПЛАН Б")


if __name__ == "__main__":
    run_gate()
