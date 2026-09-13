import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { DocumentPage } from '../DocumentPage';
import { useDocumentStore } from '../../../shared/store/documentStore';

describe('FE-F3: загрузка без мелькания', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      document: null,
      transportError: null,
      pollingTimedOut: false,
      docTypes: [],
      loadDocTypes: vi.fn(),
    });
  });

  it('пока документ грузится, показывает скелетон, а не «не найдено»', () => {
    useDocumentStore.setState({
      fetchDocument: vi.fn(() => new Promise<void>(() => {})),
    });

    render(
      <MemoryRouter initialEntries={['/documents/some-id']}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('document-skeleton')).toBeInTheDocument();
    expect(screen.queryByText(/Документ не найден/)).not.toBeInTheDocument();
  });
});