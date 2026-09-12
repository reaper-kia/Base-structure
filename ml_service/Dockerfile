FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
# Тесты и гейт качества едут в образ: эксперт должен уметь проверить
# внутреннюю логику одной командой, не собирая окружение руками
# (критерий 4.4 «техническая проверяемость»).
COPY tests ./tests
COPY scripts ./scripts
COPY pytest.ini ./pytest.ini

EXPOSE 8100

CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8100"]
