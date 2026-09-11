import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePollDocument } from '../usePollDocument';
import { useDocumentStore } from '../../store/documentStore';
import type { DocumentState } from '../../api/types';

function makeProcessingDocument(): DocumentState {
  return {
    id: 'test-id',
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

describe('usePollDocument', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useDocumentStore.setState({
      document: makeProcessingDocument(),
      fetchDocument: vi.fn(),
      setPollingTimedOut: vi.fn(),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('не запускает поллинг, если документ не в обработке', () => {
    useDocumentStore.setState({
      document: { ...makeProcessingDocument(), status: 'processed' },
    });

    renderHook(() => usePollDocument('test-id'));
    vi.advanceTimersByTime(3000);

    const { fetchDocument } = useDocumentStore.getState();
    expect(fetchDocument).not.toHaveBeenCalled();
  });

  it('показывает ошибку после 120 попыток, а не крутится вечно', () => {
    renderHook(() => usePollDocument('test-id'));

    vi.advanceTimersByTime(121000);

    const { setPollingTimedOut, fetchDocument } = useDocumentStore.getState();
    expect(setPollingTimedOut).toHaveBeenCalledWith(true);
    expect(
      (fetchDocument as ReturnType<typeof vi.fn>).mock.calls.length
    ).toBeLessThanOrEqual(120);
  });

  it('останавливает поллинг при размонтировании', () => {
    const { unmount } = renderHook(() => usePollDocument('test-id'));

    vi.advanceTimersByTime(3000);
    const callsBefore = (
      useDocumentStore.getState().fetchDocument as ReturnType<typeof vi.fn>
    ).mock.calls.length;

    unmount();

    vi.advanceTimersByTime(5000);
    const callsAfter = (
      useDocumentStore.getState().fetchDocument as ReturnType<typeof vi.fn>
    ).mock.calls.length;

    expect(callsAfter).toBe(callsBefore);
  });
});