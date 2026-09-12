#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
DRAFT="Прошу предоставить мне ежегодный оплачиваемый отпуск с 10 июня 2025 года на 14 календарных дней."

echo "🔥 Smoke test against $API_URL"

# 1. Create document
RESPONSE=$(curl -s -X POST "$API_URL/api/documents" \
  -H "Content-Type: application/json" \
  -d "{\"draft\": \"$DRAFT\", \"doc_type\": \"memo\", \"template_id\": \"classic\"}")

DOC_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "📝 Created document: $DOC_ID"

# 2. Poll until terminal status (max 3 minutes)
echo "⏳ Polling..."
for i in {1..180}; do
  sleep 1
  STATE=$(curl -s "$API_URL/api/documents/$DOC_ID")
  STATUS=$(echo "$STATE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
  
  if [[ "$STATUS" != "processing" ]]; then
    echo "✅ Terminal status: $STATUS (after $i seconds)"
    break
  fi
done

# 3. Verify Real LLM was used
IS_FALLBACK=$(echo "$STATE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_fallback', False))")
if [[ "$IS_FALLBACK" == "True" ]]; then
  echo "❌ FAIL: is_fallback=true. Real LLM was not used or Guard blocked it!"
  exit 1
fi

# 4. Render
HTTP_CODE=$(curl -s -o "smoke_$DOC_ID.docx" -w "%{http_code}" -X POST "$API_URL/api/documents/$DOC_ID/render")
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "❌ Render failed with HTTP $HTTP_CODE"
  exit 1
fi

echo "✅ Smoke test passed! File: smoke_$DOC_ID.docx"