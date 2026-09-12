FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system bot \
    && useradd --system --gid bot --home-dir /app bot \
    && chown bot:bot /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bot:bot app/ ./app/
COPY --chown=bot:bot test_manual.py ./test_manual.py

USER bot

STOPSIGNAL SIGTERM

CMD ["python", "-m", "app.main"]
