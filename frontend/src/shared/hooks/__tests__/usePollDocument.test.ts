import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { usePollDocument } from '../usePollDocument';
import { useDocumentStore } from '../../store/documentStore';
import type { DocumentState } from '../../api/types';

function processingDoc(): DocumentState {
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
    useDocumentStore.setState({
      document: processingDoc(),
      pollingTimedOut: false,
      activeDocumentId: 'test-id',
      fetchDocumentSafe: vi.fn().mockResolvedValue(true),
      setPollingTimedOut: vi.fn(),
    });
  });

  it('не опрашивает, если документ не в обработке', async () => {
    useDocumentStore.setState({
      document: { ...processingDoc(), status: 'processed' },
    });

    renderHook(() => usePollDocument('test-id'));
    await new Promise((resolve) => setTimeout(resolve, 2200));

    expect(useDocumentStore.getState().fetchDocumentSafe).not.toHaveBeenCalled();
  });

  it('останавливает опрос при размонтировании', async () => {
    const { unmount } = renderHook(() => usePollDocument('test-id'));
    await new Promise((resolve) => setTimeout(resolve, 2500));
    unmount();

    const calls = (
      useDocumentStore.getState().fetchDocumentSafe as ReturnType<typeof vi.fn>
    ).mock.calls.length;

    await new Promise((resolve) => setTimeout(resolve, 2500));

    expect(
      (useDocumentStore.getState().fetchDocumentSafe as ReturnType<typeof vi.fn>)
        .mock.calls.length
    ).toBe(calls);
  }, 15000);

  it('сообщает о таймауте после предела попыток', async () => {
    vi.useFakeTimers();

    renderHook(() => usePollDocument('test-id'));
    await vi.advanceTimersByTimeAsync(121000);

    expect(useDocumentStore.getState().setPollingTimedOut).toHaveBeenCalledWith(true);
    expect(
      (useDocumentStore.getState().fetchDocumentSafe as ReturnType<typeof vi.fn>)
        .mock.calls.length
    ).toBeLessThanOrEqual(120);

    vi.useRealTimers();
  });
});