FROM debian:bookworm-slim AS model-downloader

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl \
        --fail \
        --location \
        --retry 5 \
        --retry-all-errors \
        --output /tmp/vosk-model.zip \
        https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip \
    && unzip -q /tmp/vosk-model.zip -d /opt \
    && mv /opt/vosk-model-small-ru-0.22 /opt/vosk-model \
    && test -f /opt/vosk-model/am/final.mdl \
    && test -f /opt/vosk-model/conf/model.conf \
    && rm /tmp/vosk-model.zip


FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VOSK_MODEL_PATH=/opt/vosk-model

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --requirement requirements.txt

COPY --from=model-downloader /opt/vosk-model /opt/vosk-model
COPY app ./app

RUN groupadd --gid 10001 stt \
    && useradd \
        --uid 10001 \
        --gid stt \
        --create-home \
        --shell /usr/sbin/nologin \
        stt \
    && chown -R stt:stt /service

USER stt

EXPOSE 8200

HEALTHCHECK \
    --interval=10s \
    --timeout=5s \
    --start-period=15s \
    --retries=6 \
    CMD curl -fsS http://localhost:8200/health || exit 1

CMD ["python", "-m", "app.main"]