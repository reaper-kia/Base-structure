import { useEffect, useRef } from 'react';
import { useDocumentStore } from '../store/documentStore';

const POLL_INTERVAL = 1000;
const MAX_ATTEMPTS = 120;

export function usePollDocument(id: string | null) {
  const status = useDocumentStore((state) => state.document?.status);
  const fetchDocument = useDocumentStore((state) => state.fetchDocument);
  const setPollingTimedOut = useDocumentStore(
    (state) => state.setPollingTimedOut
  );
  const attemptsRef = useRef(0);

  const isProcessing = status === 'processing';

  useEffect(() => {
    if (!id || !isProcessing) {
      attemptsRef.current = 0;
      return;
    }

    const interval = setInterval(() => {
      attemptsRef.current += 1;

      if (attemptsRef.current >= MAX_ATTEMPTS) {
        clearInterval(interval);
        setPollingTimedOut(true);
        return;
      }

      fetchDocument(id);
    }, POLL_INTERVAL);

    return () => {
      clearInterval(interval);
    };
  }, [id, isProcessing, fetchDocument, setPollingTimedOut]);
}