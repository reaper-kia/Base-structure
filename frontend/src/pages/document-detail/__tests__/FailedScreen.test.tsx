import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { FailedScreen } from '../FailedScreen';
import { useDocumentStore } from '../../../shared/store/documentStore';
import type { DocumentState } from '../../../shared/api/types';

function makeFailedDocument(): DocumentState {
  return {
    id: 'doc-fail',
    status: 'failed',
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'Очень важный текст черновика, который нельзя потерять.',
    improved_text: null,
    changes: [],
    requisites: [],
    fact_guard: null,
    is_fallback: false,
    error: {
      code: 'llm_unavailable',
      message: 'ИИ-компонент недоступен. Черновик сохранён, попробуйте ещё раз.',
      recoverable: true,
    },
  };
}

function renderFailed(document: DocumentState = makeFailedDocument(), onRetry = () => {}) {
  return render(
    <MemoryRouter>
      <FailedScreen document={document} onRetry={onRetry} />
    </MemoryRouter>
  );
}

describe('FailedScreen', () => {
  beforeEach(() => {
    useDocumentStore.setState({ draft: '' });
  });

  it('показывает черновик целиком, а не словами о сохранении', () => {
    renderFailed();

    expect(screen.getByTestId('failed-draft')).toHaveTextContent(
      'Очень важный текст черновика, который нельзя потерять.'
    );
  });

  it('показывает error.message как есть', () => {
    renderFailed();

    expect(
      screen.getByText('ИИ-компонент недоступен. Черновик сохранён, попробуйте ещё раз.')
    ).toBeInTheDocument();
  });

  it('кнопка «Повторить» вызывает reprocess', () => {
    const onRetry = vi.fn();
    renderFailed(makeFailedDocument(), onRetry);

    fireEvent.click(screen.getByText('Повторить'));

    expect(onRetry).toHaveBeenCalled();
  });

  it('«Изменить черновик» возвращает на шаг 1 с текстом', () => {
    renderFailed();

    fireEvent.click(screen.getByText('Изменить черновик'));

    expect(useDocumentStore.getState().draft).toBe(
      'Очень важный текст черновика, который нельзя потерять.'
    );
  });
});