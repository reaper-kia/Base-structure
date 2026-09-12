import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DevPanel } from '../DevPanel';
import { api } from '../../../shared/api';

describe('FE-14: интеграция dev-панели', () => {
  beforeEach(async () => {
    await api.setAiForceFailure(false);
  });

  afterEach(async () => {
    await api.setAiForceFailure(false);
  });

  it('включение тумблера приводит к failed на следующем черновике', async () => {
    // Включаем отказ
    await api.setAiForceFailure(true);

    // Создаём документ
    const doc = await api.createDocument({
      draft: 'Директору ООО Ромашка Петрову П.П. от Иванова И.И. Прошу отпуск.',
      doc_type: 'memo',
      template_id: 'classic',
    });

    // Опрашиваем до терминального состояния
    let finalState = await api.getDocument(doc.id);
    for (let i = 0; i < 6; i += 1) {
      if (finalState.status !== 'processing') break;
      await new Promise((resolve) => setTimeout(resolve, 100));
      finalState = await api.getDocument(doc.id);
    }

    expect(finalState.status).toBe('failed');
    expect(finalState.error?.code).toBe('llm_unavailable');
  });

  it('подпись под тумблером объясняет демонстрационный режим', async () => {
    render(
      <MemoryRouter>
        <DevPanel />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Демонстрационный режим/)).toBeInTheDocument();
    });
  });
});