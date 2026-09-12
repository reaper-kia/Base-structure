import { useEffect, useRef } from 'react';
import { useDocumentStore } from '../store/documentStore';

const POLL_INTERVAL = 1000;
const MAX_ATTEMPTS = 120;

export function usePollDocument(id: string | null) {
  const status = useDocumentStore((state) => state.document?.status);
  const pollingTimedOut = useDocumentStore((state) => state.pollingTimedOut);
  const fetchDocumentSafe = useDocumentStore(
    (state) => state.fetchDocumentSafe
  );
  const setPollingTimedOut = useDocumentStore(
    (state) => state.setPollingTimedOut
  );
  const attemptsRef = useRef(0);

  const isProcessing = status === 'processing';

  useEffect(() => {
    if (!id || !isProcessing || pollingTimedOut) {
      if (!pollingTimedOut) attemptsRef.current = 0;
      return;
    }

    // Старт заново после «Продолжить ждать» на экране таймаута
    if (attemptsRef.current >= MAX_ATTEMPTS) attemptsRef.current = 0;

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const tick = async () => {
      if (stopped || controller.signal.aborted) return;

      attemptsRef.current += 1;
      if (attemptsRef.current >= MAX_ATTEMPTS) {
        // По правилу TL-12 не жмём reprocess вслепую: экран таймаута
        // сам предлагает только безопасные действия
        setPollingTimedOut(true);
        return;
      }

      await fetchDocumentSafe(id, controller.signal);
      if (stopped || controller.signal.aborted) return;

      // Следующий запрос планируем ТОЛЬКО после ответа предыдущего
      timer = setTimeout(() => {
        void tick();
      }, POLL_INTERVAL);
    };

    timer = setTimeout(() => {
      void tick();
    }, POLL_INTERVAL);

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      controller.abort();
    };
  }, [id, isProcessing, pollingTimedOut, fetchDocumentSafe, setPollingTimedOut]);
}