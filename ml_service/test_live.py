import requests
import json
import time

# Адрес нашего ML-сервиса (внутри Docker он обычно крутится на порту 8100)
# Если запускаем локально, стучимся на localhost:8100
URL = "http://localhost:8100/api/v1/process"

payload = {
    "draft": "Прошу уволить меня по собственному желанию. Иванов И.И.",
    "doc_type": "resignation",
    "doc_type_name": "Заявление на увольнение",
    "structure_hint": "Официально-деловой стиль, от первого лица",
    "requisite_keys": [
        "improved_text",
        "addressee",
        "author",
        "position",
        "subject",
        "doc_date",
    ],
    "request_id": "test-hackathon-001",
}

print("Отправляем запрос в ML-сервис (ждем ответа нейросети)...")
start = time.time()

try:
    response = requests.post(URL, json=payload)
    response.raise_for_status()  # Проверяем, что нет ошибки 500

    data = response.json()

    print(f"\n✅ Ответ получен за {round(time.time() - start, 1)} сек!\n")
    print("=== ИТОГОВЫЙ ТЕКСТ ===")
    print(data.get("improved_text"))
    print("\n=== ИЗВЛЕЧЕННЫЕ РЕКВИЗИТЫ ===")
    print(json.dumps(data.get("requisites"), indent=2, ensure_ascii=False))
    print("\n=== ВЕРДИКТ FACT GUARD ===")
    print(json.dumps(data.get("fact_guard"), indent=2, ensure_ascii=False))
    print(f"\nFallback использован: {data.get('is_fallback')}")

except Exception as e:
    print(f"❌ Ошибка при запросе: {e}")
    print("Возможно, сервис висит на другом порту или еще не успел загрузиться.")
