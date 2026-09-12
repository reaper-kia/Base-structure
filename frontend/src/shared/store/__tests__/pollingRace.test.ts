import { describe, it, expect } from 'vitest';
import { useDocumentStore } from '../documentStore';
import { api } from '../../api';

describe('FE-15: гонки опроса и восстановление', () => {
  it('поздний ответ по старому id не перезаписывает текущий документ', async () => {
    const a = await api.createDocument({
      draft: 'Первый черновик для теста гонки',
      doc_type: 'memo',
      template_id: 'classic',
    });
    const b = await api.createDocument({
      draft: 'Второй черновик для теста гонки',
      doc_type: 'memo',
      template_id: 'classic',
    });

    await useDocumentStore.getState().fetchDocument(b.id);
    expect(useDocumentStore.getState().document?.id).toBe(b.id);

    const written = await useDocumentStore.getState().fetchDocumentSafe(a.id);

    expect(written).toBe(false);
    expect(useDocumentStore.getState().document?.id).toBe(b.id);
  });

  it('перезагрузка до отправки сохраняет текст и выбор', () => {
    useDocumentStore.getState().setDraft('Важный черновик ещё не отправлен');
    useDocumentStore.getState().setDocType('memo');
    useDocumentStore.getState().setTemplateId('classic');

    const raw = sessionStorage.getItem('doc3-wizard-session');
    expect(raw).toBeTruthy();

    const parsed = JSON.parse(raw as string);
    expect(parsed.draft).toBe('Важный черновик ещё не отправлен');
    expect(parsed.docType).toBe('memo');
    expect(parsed.templateId).toBe('classic');
  });

  it('таймаут не даёт цикл 409: возобновление только продолжает ждать', () => {
    useDocumentStore.getState().setPollingTimedOut(true);
    expect(useDocumentStore.getState().pollingTimedOut).toBe(true);

    useDocumentStore.getState().resumePolling();
    expect(useDocumentStore.getState().pollingTimedOut).toBe(false);
  });
});