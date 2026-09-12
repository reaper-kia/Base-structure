from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Mapping
from contextlib import suppress
from functools import partial

from app.config import ConfigurationError, MAX_DRAFT_LENGTH, Settings
from app.conversation import (
    Choice,
    ChoiceNotFound,
    ConversationState,
    ConversationStore,
    GenerationRequest,
    RequiredRequisite,
    format_choices,
)
from app.doc_api import (
    DocumentApiClient,
    DocumentApiError,
    DocumentSnapshot,
    DocumentType,
    Template,
)
from app.max_client import (
    InboundEvent,
    InboundKind,
    MaxApiError,
    MaxAuthenticationError,
    MaxClient,
    MaxRecipient,
    parse_inbound_update,
)

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "Здравствуйте! Я превращаю черновик в готовый DOCX.\n\n"
    "Пришлите текст документа одним сообщением. "
    "Команды: /help — подсказка, /cancel — начать заново."
)
HELP_TEXT = (
    "Как создать документ:\n"
    "1. Пришлите черновик текстом.\n"
    "2. Выберите номер типа документа.\n"
    "3. Выберите номер шаблона.\n"
    "4. Дождитесь готового DOCX (до двух минут).\n\n"
    "/start — новый диалог, /cancel — отменить текущий документ."
)


class BotApplication:
    def __init__(
        self,
        *,
        settings: Settings,
        max_client: MaxClient,
        document_client: DocumentApiClient,
        conversations: ConversationStore | None = None,
    ) -> None:
        self._settings = settings
        self._max = max_client
        self._documents = document_client
        self._conversations = conversations or ConversationStore()
        self._jobs: dict[int, tuple[str, asyncio.Task[None]]] = {}
        self._job_slots = asyncio.Semaphore(settings.max_concurrent_jobs)

    async def run(self) -> None:
        marker: int | None = None
        bootstrapped = not self._settings.skip_pending_updates
        failure_delay = 1.0
        logger.info("MAX bot long polling started")

        try:
            while True:
                try:
                    if not bootstrapped:
                        initial = await self._max.get_updates(
                            None,
                            timeout_seconds=0,
                        )
                        marker = initial.marker
                        bootstrapped = True
                        logger.info(
                            "Long polling marker initialized; skipped %s pending update(s)",
                            len(initial.updates),
                        )
                        continue

                    batch = await self._max.get_updates(marker)
                    if batch.marker is not None:
                        marker = batch.marker
                    for update in batch.updates:
                        await self._dispatch(update)
                    failure_delay = 1.0
                except asyncio.CancelledError:
                    raise
                except MaxAuthenticationError:
                    logger.exception(
                        "MAX rejected MAX_BOT_TOKEN; waiting before the next attempt"
                    )
                    await asyncio.sleep(30.0)
                except Exception:  # noqa: BLE001 - the polling loop must survive
                    logger.exception("Long polling iteration failed")
                    await asyncio.sleep(failure_delay)
                    failure_delay = min(failure_delay * 2.0, 30.0)
        finally:
            await self._cancel_all_jobs()
            logger.info("MAX bot stopped")

    async def _dispatch(self, update: Mapping[str, object]) -> None:
        event = parse_inbound_update(update)
        if event is None:
            return
        try:
            await self._handle_event(event)
        except asyncio.CancelledError:
            raise
        except MaxAuthenticationError:
            raise
        except DocumentApiError as exc:
            logger.warning(
                "Document API error for chat %s: %s",
                event.chat_id,
                exc,
            )
            await self._safe_send(event.recipient, exc.public_message)
        except MaxApiError:
            logger.exception("MAX API error while handling chat %s", event.chat_id)
        except Exception:  # noqa: BLE001 - isolate a poison update
            logger.exception("Unhandled update error for chat %s", event.chat_id)
            self._conversations.reset(event.chat_id)
            await self._safe_send(
                event.recipient,
                "Не удалось обработать сообщение. Пришлите черновик ещё раз.",
            )

    async def _handle_event(self, event: InboundEvent) -> None:
        if event.kind is InboundKind.BOT_STARTED:
            await self._cancel_chat_job(event.chat_id)
            self._conversations.reset(event.chat_id)
            await self._max.send_text(event.recipient, WELCOME_TEXT)
            return

        raw_text = event.text
        if raw_text is not None:
            command = _command(raw_text)
            if command == "/start":
                await self._cancel_chat_job(event.chat_id)
                self._conversations.reset(event.chat_id)
                await self._max.send_text(event.recipient, WELCOME_TEXT)
                return
            if command == "/help":
                await self._max.send_text(event.recipient, HELP_TEXT)
                return
            if command == "/cancel":
                await self._cancel_chat_job(event.chat_id)
                self._conversations.reset(event.chat_id)
                await self._max.send_text(
                    event.recipient,
                    "Текущий сценарий отменён. Пришлите новый черновик.",
                )
                return

        state = self._conversations.state(event.chat_id)
        if state is ConversationState.PROCESSING:
            await self._max.send_text(
                event.recipient,
                "Документ уже создаётся. Подождите или отправьте /cancel.",
            )
            return
        if raw_text is None or not raw_text.strip():
            await self._max.send_text(
                event.recipient,
                "Нужно текстовое сообщение. Пришлите черновик или номер варианта.",
            )
            return

        if state is ConversationState.WAITING_DRAFT:
            await self._accept_draft(event, raw_text)
        elif state is ConversationState.WAITING_DOC_TYPE:
            await self._accept_doc_type(event, raw_text)
        elif state is ConversationState.WAITING_TEMPLATE:
            await self._accept_template(event, raw_text)

    async def _accept_draft(self, event: InboundEvent, draft: str) -> None:
        if len(draft) > MAX_DRAFT_LENGTH:
            await self._max.send_text(
                event.recipient,
                f"Черновик длиннее {MAX_DRAFT_LENGTH} символов. Сократите его.",
            )
            return

        document_types = await self._documents.get_document_types()
        choices = tuple(_document_type_choice(item) for item in document_types)
        self._conversations.start(event.chat_id, draft, choices)
        await self._max.send_text(
            event.recipient,
            "Выберите тип документа — отправьте номер, название или id:\n\n"
            + format_choices(choices),
        )

    async def _accept_doc_type(self, event: InboundEvent, value: str) -> None:
        try:
            selected = self._conversations.resolve_doc_type(event.chat_id, value)
        except ChoiceNotFound:
            choices = self._conversations.doc_type_choices(event.chat_id)
            await self._max.send_text(
                event.recipient,
                "Не понял выбор. Отправьте номер, название или id:\n\n"
                + format_choices(choices),
            )
            return

        templates = await self._documents.get_templates()
        choices = tuple(_template_choice(item) for item in templates)
        self._conversations.select_doc_type(event.chat_id, selected, choices)
        await self._max.send_text(
            event.recipient,
            "Выберите шаблон оформления — отправьте номер, название или id:\n\n"
            + format_choices(choices),
        )

    async def _accept_template(self, event: InboundEvent, value: str) -> None:
        try:
            selected = self._conversations.resolve_template(event.chat_id, value)
        except ChoiceNotFound:
            choices = self._conversations.template_choices(event.chat_id)
            await self._max.send_text(
                event.recipient,
                "Не понял выбор. Отправьте номер, название или id:\n\n"
                + format_choices(choices),
            )
            return

        await self._max.send_text(
            event.recipient,
            "Создаю документ. Обычно это занимает до двух минут…",
        )
        request = self._conversations.begin_generation(event.chat_id, selected)
        task = asyncio.create_task(
            self._generate_document(
                chat_id=event.chat_id,
                recipient=event.recipient,
                request=request,
            ),
            name=f"document-{event.chat_id}-{request.generation_id[:8]}",
        )
        self._jobs[event.chat_id] = (request.generation_id, task)
        task.add_done_callback(partial(self._job_done, event.chat_id))

    async def _generate_document(
        self,
        *,
        chat_id: int,
        recipient: MaxRecipient,
        request: GenerationRequest,
    ) -> None:
        document_id: str | None = None
        try:
            async with self._job_slots:
                document_id = await self._documents.create_document(
                    draft=request.draft,
                    doc_type=request.doc_type_id,
                    template_id=request.template_id,
                )
                snapshot = await self._documents.poll_until_done(document_id)
                rendered = await self._documents.render_document(document_id)

                missing = _missing_required(snapshot, request)
                if missing:
                    await self._max.send_text(
                        recipient,
                        "В черновике не найдены обязательные реквизиты:\n"
                        + "\n".join(f"• {label}" for label in missing)
                        + "\n\nДокумент всё равно сформирован; пустые поля можно заполнить вручную.",
                    )

                caption = "Готово — отправляю документ."
                if snapshot.status == "degraded" or snapshot.is_fallback:
                    caption = (
                        "Готово. Документ собран в резервном режиме — "
                        "рекомендуется проверить текст."
                    )
                await self._max.send_file(
                    recipient,
                    content=rendered.content,
                    filename=rendered.filename,
                    text=caption,
                )
                logger.info(
                    "Document %s delivered to chat %s with status %s",
                    document_id,
                    chat_id,
                    snapshot.status,
                )
        except asyncio.CancelledError:
            logger.info(
                "Generation %s cancelled for chat %s", request.generation_id, chat_id
            )
            raise
        except DocumentApiError as exc:
            logger.warning(
                "Document generation failed for chat %s, document %s: %s",
                chat_id,
                document_id or "not-created",
                exc,
            )
            await self._safe_send(recipient, exc.public_message)
        except MaxApiError:
            logger.exception(
                "Could not deliver document %s to chat %s",
                document_id or "not-created",
                chat_id,
            )
            await self._safe_send(
                recipient,
                "Документ создан, но отправить файл не удалось. Попробуйте ещё раз.",
            )
        except Exception:  # noqa: BLE001 - isolate one generation task
            logger.exception("Unexpected generation error for chat %s", chat_id)
            await self._safe_send(
                recipient,
                "Произошла непредвиденная ошибка. Пришлите черновик ещё раз.",
            )
        finally:
            self._conversations.complete(chat_id, request.generation_id)

    async def _safe_send(self, recipient: MaxRecipient, text: str) -> None:
        try:
            await self._max.send_text(recipient, text)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - error notification is best effort
            logger.exception(
                "Could not send an error notification to %s", recipient.key
            )

    async def _cancel_chat_job(self, chat_id: int) -> None:
        entry = self._jobs.pop(chat_id, None)
        if entry is None:
            return
        _generation_id, task = entry
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _cancel_all_jobs(self) -> None:
        tasks = [task for _generation_id, task in self._jobs.values()]
        self._jobs.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _job_done(self, chat_id: int, completed: asyncio.Task[None]) -> None:
        current = self._jobs.get(chat_id)
        if current is not None and current[1] is completed:
            self._jobs.pop(chat_id, None)
        if completed.cancelled():
            return
        with suppress(Exception):
            completed.result()


def _document_type_choice(document_type: DocumentType) -> Choice:
    required = tuple(
        RequiredRequisite(key=item.key, label=item.label)
        for item in document_type.requisites
        if item.required
    )
    return Choice(
        id=document_type.id,
        label=document_type.name,
        required_requisites=required,
    )


def _template_choice(template: Template) -> Choice:
    return Choice(id=template.id, label=template.name)


def _missing_required(
    snapshot: DocumentSnapshot,
    request: GenerationRequest,
) -> tuple[str, ...]:
    statuses = {item.key: item.status for item in snapshot.requisites}
    return tuple(
        requisite.label
        for requisite in request.required_requisites
        if statuses.get(requisite.key) == "missing"
    )


def _command(text: str) -> str | None:
    first_token = text.strip().split(maxsplit=1)[0] if text.strip() else ""
    command = first_token.split("@", 1)[0].casefold()
    return command if command in {"/start", "/help", "/cancel"} else None


async def _serve(settings: Settings) -> None:
    async with (
        MaxClient(
            settings.max_bot_token,
            base_url=settings.max_api_base_url,
            long_poll_timeout_seconds=settings.max_long_poll_timeout_seconds,
            request_timeout_seconds=settings.api_request_timeout_seconds,
            max_attempts=settings.http_max_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
            attachment_ready_attempts=settings.attachment_ready_attempts,
        ) as max_client,
        DocumentApiClient(
            settings.api_base_url,
            request_timeout_seconds=settings.api_request_timeout_seconds,
            poll_interval_seconds=settings.document_poll_interval_seconds,
            processing_timeout_seconds=settings.document_processing_timeout_seconds,
            max_attempts=settings.http_max_attempts,
            retry_backoff_seconds=settings.http_retry_backoff_seconds,
        ) as document_client,
    ):
        application = BotApplication(
            settings=settings,
            max_client=max_client,
            document_client=document_client,
        )
        runner = asyncio.create_task(application.run(), name="max-long-polling")
        loop = asyncio.get_running_loop()
        installed_signals: list[signal.Signals] = []
        signals_to_install: tuple[signal.Signals, ...] = (
            signal.SIGTERM,
            signal.SIGINT,
        )
        for signum in signals_to_install:
            try:
                loop.add_signal_handler(signum, runner.cancel)
            except NotImplementedError:
                continue
            installed_signals.append(signum)

        try:
            await runner
        except asyncio.CancelledError:
            pass
        finally:
            for signum in installed_signals:
                loop.remove_signal_handler(signum)


def main() -> int:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR)
        logger.critical("Invalid configuration: %s", exc)
        return 2

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(_serve(settings))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
