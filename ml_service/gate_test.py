import requests
import json
import time

# Адрес локальной Ollama, которую мы подняли в Docker
OLLAMA_URL = "http://localhost:11434/api/generate"
# Мы поднимаемся на одну папку вверх (..) и заходим в contracts
SCHEMA_PATH = "../contracts/llm_schema.json"

# Шаг 1: Загружаем схему, которую модель должна строго соблюдать
print("Загружаем JSON-схему...")
with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    llm_schema = json.load(f)

# 20 черновых текстов для проверки (от простых до тех, где не хватает данных)
drafts = [
    "прошу отпуск с 15 мая", "нужен ремонт принтера, 5000 руб", "я работаю тут с 2020",
    "доложите директору Иванову", "передай Сидорову про встречу", "выдайте новый ноут",
    "прошу уволить по собственному", "закупите бумагу 10 пачек", "отчет за квартал готов",
    "премия Петрову 10000", "надо починить кран", "согласовать договор №123",
    "прошу перевести в другой отдел", "справка дана для предъявления по месту",
    "направляю акт выполненных работ", "заявка на канцтовары", "объяснительная по опозданию",
    "служебка на пропуск для авто", "прошу оплатить счет от Ромашки", "информация о проекте"
]

def run_gate():
    print(f"🚀 Запускаем Гейт-тест: 20 прогонов (ML-01)...")
    valid_json_count = 0
    
    for i, draft in enumerate(drafts, 1):
        print(f"Тест {i}/20...", end=" ", flush=True)
        
        # Строим запрос по правилам из ТЗ (ML-01.2)
        payload = {
            "model": "qwen2.5:7b-instruct",
            "prompt": f"Перепиши в деловом стиле и извлеки реквизиты. Черновик: {draft}",
            "format": llm_schema,
            "stream": False,
            "options": {"temperature": 0.2} # Строго 0.2, чтобы ИИ не выдумывал факты
        }
        
        start_time = time.time()
        try:
            # Отправляем запрос
            response = requests.post(OLLAMA_URL, json=payload).json()
            
            # Самое главное: пробуем программно прочитать ответ
            # Если ИИ ошибся в синтаксисе JSON, эта строчка вызовет ошибку
            parsed_data = json.loads(response["response"])
            
            valid_json_count += 1
            print(f"✅ JSON валиден ({round(time.time() - start_time, 1)} сек)")
            
        except json.JSONDecodeError:
            print("❌ Ошибка: сломанный синтаксис JSON")
        except Exception as e:
            print(f"❌ Ошибка сети: {e}")

    # Считаем и выводим итог
    success_rate = (valid_json_count / len(drafts)) * 100
    print("\n" + "="*30)
    print(f"ИТОГИ ГЕЙТА: {valid_json_count}/20 валидных ответов ({success_rate}%)")
    print("="*30)
    
    if success_rate >= 90:
        print("Вердикт тимлида: Идем по плану, repair на всякий случай")
    elif success_rate >= 70:
        print("Вердикт тимлида: Repair обязателен, план не меняем")
    else:
        print("Вердикт тимлида: НЕМЕДЛЕННО ПИШИ В ЧАТ, ПЕРЕХОДИМ НА ПЛАН Б")

if __name__ == "__main__":
    run_gate()