import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePollDocument } from '../usePollDocument';
import { useDocumentStore } from '../../store/documentStore';
import type { DocumentState } from '../../api/types';

function processingDoc(id: string): DocumentState {
  return {
    id,
    status: 'processing',
    stage: 'llm',
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'test',
    improved_text: null,
    changes: [],
    requisites: [],
    fact_guard: null,
    is_fallback: false,
    error: null,
  };
}

describe('FE-15: последовательность опроса', () => {
  it('нет двух одновременных запросов статуса', async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    let calls = 0;

    useDocumentStore.setState({
      document: processingDoc('doc-seq'),
      pollingTimedOut: false,
      activeDocumentId: 'doc-seq',
      fetchDocumentSafe: vi.fn(async () => {
        calls += 1;
        inFlight += 1;
        maxInFlight = Math.max(maxInFlight, inFlight);
        // Ответ медленнее интервала: setInterval бы наложил запросы
        await new Promise((resolve) => setTimeout(resolve, 1500));
        inFlight -= 1;
        return true;
      }),
    });

    const { unmount } = renderHook(() => usePollDocument('doc-seq'));

    await new Promise((resolve) => setTimeout(resolve, 5200));
    unmount();

    expect(calls).toBeGreaterThanOrEqual(2);
    expect(maxInFlight).toBe(1);
  }, 15000);
});