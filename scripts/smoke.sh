#!/usr/bin/env bash
# Сквозная проверка обязательного сценария: черновик -> обработка -> DOCX.
#
#   make smoke                                  # локальный стек
#   make smoke-prod PROD_URL=https://stand.ru   # боевой стенд
#
# Скрипт проходит ровно тот путь, который в задании назван сценарием 1,
# и не требует ни браузера, ни ручных действий.
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
DOC_TYPE="${DOC_TYPE:-memo}"
TEMPLATE_ID="${TEMPLATE_ID:-classic}"
# Непустой REQUIRE_LLM превращает резервный режим в ошибку: полезно, чтобы
# перед защитой убедиться, что модель реально отвечает.
REQUIRE_LLM="${REQUIRE_LLM:-}"

DRAFT=$(cat <<'EOF'
Кому: Генеральному директору ООО «Ромашка» Иванову И.И.
От кого: начальник отдела аналитики Петров П.П.
Заголовок: О закупке офисной техники

кароче надо бы купить три компа, цена 180 000 рублей, поставка не позднее 25.03.2025
EOF
)

json_field() {
  python3 -c "import sys, json; print(json.load(sys.stdin).get('$1', ''))"
}

echo "Проверяю $API_URL"

PAYLOAD=$(DRAFT="$DRAFT" DOC_TYPE="$DOC_TYPE" TEMPLATE_ID="$TEMPLATE_ID" python3 -c '
import json, os
print(json.dumps({
    "draft": os.environ["DRAFT"],
    "doc_type": os.environ["DOC_TYPE"],
    "template_id": os.environ["TEMPLATE_ID"],
}))')

RESPONSE=$(curl -sSk -X POST "$API_URL/api/documents" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

DOC_ID=$(echo "$RESPONSE" | json_field id)

if [[ -z "$DOC_ID" ]]; then
  echo "Не удалось создать документ: $RESPONSE"
  exit 1
fi

echo "Документ создан: $DOC_ID"
echo "Жду завершения обработки..."

STATE=""
for i in $(seq 1 180); do
  sleep 1
  STATE=$(curl -sSk "$API_URL/api/documents/$DOC_ID")
  STATUS=$(echo "$STATE" | json_field status)

  if [[ "$STATUS" != "processing" ]]; then
    echo "Статус: $STATUS (через $i с)"
    break
  fi
done

if [[ "$STATUS" == "processing" ]]; then
  echo "Обработка не завершилась за 180 секунд"
  exit 1
fi

if [[ "$STATUS" == "failed" ]]; then
  echo "Обработка завершилась ошибкой:"
  echo "$STATE" | python3 -m json.tool
  exit 1
fi

IS_FALLBACK=$(echo "$STATE" | json_field is_fallback)
REASON=$(echo "$STATE" | json_field reason_code)
VERDICT=$(echo "$STATE" | python3 -c "import sys, json; print((json.load(sys.stdin).get('fact_guard') or {}).get('verdict', '-'))")

echo "Fact Guard: $VERDICT"

if [[ "$IS_FALLBACK" == "True" ]]; then
  if [[ -n "$REQUIRE_LLM" ]]; then
    echo "Резервный режим (причина: $REASON), а REQUIRE_LLM требует модель"
    exit 1
  fi
  echo "Резервный режим (причина: $REASON) — документ всё равно формируется"
fi

# Рендер обязан отработать в любом из штатных статусов.
HTTP_CODE=$(curl -sSk -o "smoke_$DOC_ID.docx" -w "%{http_code}" \
  -X POST "$API_URL/api/documents/$DOC_ID/render")

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Рендер вернул HTTP $HTTP_CODE"
  exit 1
fi

if ! python3 -c "
import sys, zipfile
with zipfile.ZipFile('smoke_$DOC_ID.docx') as z:
    assert 'word/document.xml' in z.namelist()
"; then
  echo "Скачанный файл не является корректным DOCX"
  exit 1
fi

echo "Готово: smoke_$DOC_ID.docx"
