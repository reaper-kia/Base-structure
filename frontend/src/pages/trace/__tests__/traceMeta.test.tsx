import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TracePage } from '../TracePage';
import { api } from '../../../shared/api';

async function createTerminalDocument(): Promise<string> {
  const doc = await api.createDocument({
    draft:
      'Директору ООО «Ромашка» Петрову П.П. от Иванова И.И. Прошу отпуск с 10 июня 2025 на 14 дней.',
    doc_type: 'memo',
    template_id: 'classic',
  });

  for (let i = 0; i < 6; i += 1) {
    const current = await api.getDocument(doc.id);
    if (current.status !== 'processing') break;
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

describe('FE-13: метаданные журнала', () => {
  beforeAll(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterAll(() => {
    vi.restoreAllMocks();
  });

  it('показывает кэш, длительности и версии, когда они есть в журнале', async () => {
    const id = await createTerminalDocument();
    renderTrace(id);

    await waitFor(
      () => {
        expect(screen.getByText('кэш: промах')).toBeInTheDocument();
      },
      { timeout: 15000 }
    );
    expect(screen.getByText('42.1 с')).toBeInTheDocument();
    expect(screen.getByText('модель: qwen2.5:7b-instruct')).toBeInTheDocument();
  }, 15000);

  it('ошибка рендера видна в журнале', async () => {
    await api.setAiForceFailure(true);
    const id = await createTerminalDocument();
    await api.setAiForceFailure(false);

    renderTrace(id);

    await waitFor(
      () => {
        expect(screen.getByText(/Ошибка на стадии/)).toBeInTheDocument();
      },
      { timeout: 15000 }
    );
  }, 15000);
});