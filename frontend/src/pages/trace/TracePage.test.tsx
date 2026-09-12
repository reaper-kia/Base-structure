import { describe, it, expect, beforeAll, afterAll, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TracePage } from './TracePage';
import { api } from '../../shared/api';

async function createReadyDocument(): Promise<string> {
  const doc = await api.createDocument({
    draft: 'Директору ООО Ромашка Петрову П.П. от Иванова И.И. Прошу отпуск.',
    doc_type: 'memo',
    template_id: 'classic',
  });

  // Прогоняем до терминального состояния
  for (let i = 0; i < 5; i += 1) {
    const current = await api.getDocument(doc.id);
    if (current.status !== 'processing') {
      return doc.id;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  return doc.id;
}

function renderTrace(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/trace/${id}`]}>
      <Routes>
        <Route path="/trace/:id" element={<TracePage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('TracePage', () => {
  beforeAll(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('отображает список стадий обработки', async () => {
    const id = await createReadyDocument();
    renderTrace(id);

    await waitFor(
      () => {
        expect(screen.getByText('anchors')).toBeInTheDocument();
        expect(screen.getByText('llm_request')).toBeInTheDocument();
        expect(screen.getByText('fact_guard')).toBeInTheDocument();
        expect(screen.getByText('render')).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  }, 10000);

  it('показывает ссылку возврата на документ', async () => {
    const id = await createReadyDocument();
    renderTrace(id);

    await waitFor(
      () => {
        expect(screen.getByText('anchors')).toBeInTheDocument();
      },
      { timeout: 5000 }
    );

    const backLink = screen.getByText('← Вернуться к документу');
    expect(backLink).toHaveAttribute('href', `/documents/${id}`);
  }, 10000);

  it('показывает ошибку при несуществующем id', async () => {
    renderTrace('definitely-non-existent-id-12345');

    await waitFor(
      () => {
        expect(screen.getByText(/Документ не найден/)).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  }, 10000);
});