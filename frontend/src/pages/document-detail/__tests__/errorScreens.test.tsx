import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DocumentPage } from '../DocumentPage';
import { DegradedBanner } from '../DegradedBanner';
import { FailedScreen } from '../FailedScreen';
import { useDocumentStore } from '../../../shared/store/documentStore';
import type { DocumentState } from '../../../shared/api/types';

function failedDoc(): DocumentState {
  return {
    id: 'doc-fail',
    status: 'failed',
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'Черновик, который нельзя потерять и можно скопировать.',
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

function processedDoc(): DocumentState {
  return {
    id: 'doc-ok',
    status: 'processed',
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'черновик',
    improved_text: 'черновик улучшенный',
    changes: [],
    requisites: [],
    fact_guard: null,
    is_fallback: false,
    error: null,
  };
}

describe('FE-11: экраны ошибок', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      document: null,
      transportError: null,
      docTypes: [],
      pollingTimedOut: false,
      loadDocTypes: vi.fn(),
    });
  });

  it('404 завершает загрузку ошибкой, а не вечной загрузкой', async () => {
    useDocumentStore.setState({
      fetchDocument: vi.fn().mockImplementation(async () => {
        useDocumentStore.setState({ transportError: 'Документ не найден' });
      }),
    });

    render(
      <MemoryRouter initialEntries={['/documents/missing-id']}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Документ не найден')).toBeInTheDocument();
    });
    expect(screen.queryByText(/Загрузка документа/)).not.toBeInTheDocument();
    expect(screen.getByText('Создать новый документ')).toBeInTheDocument();
  });

  it('transportError виден на странице документа', async () => {
    useDocumentStore.setState({
      document: processedDoc(),
      transportError: 'Не удалось скачать документ',
      fetchDocument: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/documents/doc-ok']}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Не удалось скачать документ')).toBeInTheDocument();
    });
  });

  it('три reason_code дают три разных текста', () => {
    const { rerender } = render(<DegradedBanner reason="model_unavailable" />);
    expect(screen.getByText(/ИИ-компонент недоступен/)).toBeInTheDocument();

    rerender(<DegradedBanner reason="schema_invalid" />);
    expect(screen.getByText(/Модель вернула некорректный ответ/)).toBeInTheDocument();

    rerender(<DegradedBanner reason="facts_unverified" />);
    expect(screen.getByText(/сохранность фактов/)).toBeInTheDocument();
  });

  it('в резервном режиме сказано, что текст не исправлялся', () => {
    render(<DegradedBanner reason="model_unavailable" />);
    expect(screen.getByText(/Текст не исправлялся/)).toBeInTheDocument();
  });

  it('черновик на экране ошибки можно скопировать', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    render(
      <MemoryRouter>
        <FailedScreen document={failedDoc()} onRetry={() => {}} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Скопировать черновик'));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(failedDoc().draft);
    });
  });
});