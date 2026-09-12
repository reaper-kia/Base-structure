from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

MAX_API_BASE_URL = "https://platform-api2.max.ru"
DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
MAX_MESSAGE_LENGTH = 4_000
MAX_DRAFT_LENGTH = 20_000


class ConfigurationError(RuntimeError):
    """Raised when an environment variable is absent or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    max_bot_token: str = field(repr=False)
    api_base_url: str
    max_api_base_url: str = MAX_API_BASE_URL
    max_long_poll_timeout_seconds: int = 30
    api_request_timeout_seconds: float = 15.0
    document_poll_interval_seconds: float = 1.5
    document_processing_timeout_seconds: float = 120.0
    http_max_attempts: int = 4
    http_retry_backoff_seconds: float = 0.5
    attachment_ready_attempts: int = 6
    max_concurrent_jobs: int = 8
    skip_pending_updates: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> Settings:
        values = os.environ if environ is None else environ

        token = _required(values, "MAX_BOT_TOKEN")
        api_base_url = _url(values, "API_BASE_URL")
        log_level = values.get("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError(
                "LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL"
            )

        return cls(
            max_bot_token=token,
            api_base_url=api_base_url,
            max_long_poll_timeout_seconds=_integer(
                values,
                "MAX_LONG_POLL_TIMEOUT_SECONDS",
                default=30,
                minimum=1,
                maximum=90,
            ),
            api_request_timeout_seconds=_number(
                values,
                "API_REQUEST_TIMEOUT_SECONDS",
                default=15.0,
                minimum=1.0,
                maximum=120.0,
            ),
            document_poll_interval_seconds=_number(
                values,
                "DOCUMENT_POLL_INTERVAL_SECONDS",
                default=1.5,
                minimum=0.1,
                maximum=10.0,
            ),
            document_processing_timeout_seconds=_number(
                values,
                "DOCUMENT_PROCESSING_TIMEOUT_SECONDS",
                default=120.0,
                minimum=1.0,
                maximum=3_600.0,
            ),
            http_max_attempts=_integer(
                values,
                "HTTP_MAX_ATTEMPTS",
                default=4,
                minimum=1,
                maximum=10,
            ),
            http_retry_backoff_seconds=_number(
                values,
                "HTTP_RETRY_BACKOFF_SECONDS",
                default=0.5,
                minimum=0.05,
                maximum=10.0,
            ),
            attachment_ready_attempts=_integer(
                values,
                "MAX_ATTACHMENT_READY_ATTEMPTS",
                default=6,
                minimum=1,
                maximum=10,
            ),
            max_concurrent_jobs=_integer(
                values,
                "MAX_CONCURRENT_JOBS",
                default=8,
                minimum=1,
                maximum=64,
            ),
            skip_pending_updates=_boolean(
                values,
                "MAX_SKIP_PENDING_UPDATES",
                default=True,
            ),
            log_level=log_level,
        )


def _required(environ: Mapping[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is required and cannot be blank")
    return value


def _url(environ: Mapping[str, str], name: str) -> str:
    value = _required(environ, name).rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigurationError(f"{name} must be an absolute HTTP(S) URL")
    if parsed.query or parsed.fragment:
        raise ConfigurationError(f"{name} must not contain query or fragment")
    return value


def _number(
    environ: Mapping[str, str],
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    raw = environ.get(name)
    try:
        value = default if raw is None else float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


def _integer(
    environ: Mapping[str, str],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = environ.get(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _boolean(
    environ: Mapping[str, str],
    name: str,
    *,
    default: bool,
) -> bool:
    raw = environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be a boolean")
