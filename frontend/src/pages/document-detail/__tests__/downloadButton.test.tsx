import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ResultScreen } from '../ResultScreen';
import { useDocumentStore } from '../../../shared/store/documentStore';
import type { DocumentState } from '../../../shared/api/types';

function makeDocument(status: DocumentState['status']): DocumentState {
  return {
    id: 'doc-1',
    status,
    stage: status === 'processing' ? 'llm' : null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'черновик',
    improved_text: status === 'processing' ? null : 'черновик улучшенный',
    changes: [],
    requisites: [],
    fact_guard: null,
    is_fallback: false,
    error:
      status === 'failed'
        ? {
            code: 'llm_unavailable',
            message: 'ИИ-компонент недоступен.',
            recoverable: true,
          }
        : null,
  };
}

describe('FE-12: состояния кнопки скачивания', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      renderFallback: null,
      transportError: null,
      isRendering: false,
    });
  });

  it('при processing кнопка неактивна с подписью «Идёт обработка…»', () => {
    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument('processing')} />
      </MemoryRouter>
    );

    const button = screen.getByText('Идёт обработка…');
    expect(button).toBeDisabled();
  });

  it('при failed кнопки скачивания нет', () => {
    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument('failed')} />
      </MemoryRouter>
    );

    expect(screen.queryByText(/Скачать DOCX/)).not.toBeInTheDocument();
    expect(screen.queryByText('Идёт обработка…')).not.toBeInTheDocument();
  });

  it('при processed кнопка активна', () => {
    render(
      <MemoryRouter>
        <ResultScreen document={makeDocument('processed')} />
      </MemoryRouter>
    );

    expect(screen.getByText('⬇ Скачать DOCX')).not.toBeDisabled();
  });

  it('ошибка render показывает сообщение, а не тихий провал', async () => {
    useDocumentStore.setState({ document: makeDocument('failed') });

    await useDocumentStore.getState().renderDocument('doc-1');

    expect(useDocumentStore.getState().transportError).toBeTruthy();
    expect(useDocumentStore.getState().isRendering).toBe(false);
  });
});