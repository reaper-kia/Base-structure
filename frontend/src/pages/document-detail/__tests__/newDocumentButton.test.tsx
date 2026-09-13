import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DocumentPage } from '../DocumentPage';
import { useDocumentStore } from '../../../shared/store/documentStore';
import type { DocumentState } from '../../../shared/api/types';

function processedDoc(): DocumentState {
  return {
    id: 'doc-1',
    status: 'processed',
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: 'черновик',
    improved_text: 'улучшенный',
    changes: [],
    requisites: [],
    fact_guard: null,
    is_fallback: false,
    error: null,
  };
}

describe('FE-F2: кнопка «Создать ещё документ»', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      document: processedDoc(),
      transportError: null,
      pollingTimedOut: false,
      docTypes: [
        { id: 'memo', name: 'Служебная записка', description: '', requisites: [] },
      ],
      fetchDocument: vi.fn(),
      loadDocTypes: vi.fn(),
    });
  });

  it('сбрасывает визард и возвращает на чистый шаг 1', () => {
    useDocumentStore.getState().setDraft('старый черновик');

    render(
      <MemoryRouter initialEntries={['/documents/doc-1']}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentPage />} />
          <Route path="/wizard" element={<div>WIZARD_PAGE</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('+ Создать ещё документ'));

    expect(screen.getByText('WIZARD_PAGE')).toBeInTheDocument();
    expect(useDocumentStore.getState().draft).toBe('');
  });
});