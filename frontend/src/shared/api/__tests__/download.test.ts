import { describe, it, expect, vi, afterEach } from 'vitest';

function fakeRenderResponse(headers: Record<string, string>) {
  return {
    ok: true,
    status: 200,
    blob: async () => new Blob([new Uint8Array([80, 75, 3, 4, 1, 2, 3, 4])]),
    headers: {
      get: (name: string) => headers[name.toLowerCase()] ?? null,
    },
  };
}

describe('FE-12: httpApi.renderDocument', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it('имя файла берётся из Content-Disposition (filename*=UTF-8)', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        fakeRenderResponse({
          'content-disposition':
            "attachment; filename*=UTF-8''sluzhebnaya-zapiska-11-09-2026.docx",
        })
      )
    );

    const { httpApi } = await import('../httpApi');
    const result = await httpApi.renderDocument('id-1');

    expect(result.filename).toBe('sluzhebnaya-zapiska-11-09-2026.docx');
  });

  it('X-Template-Fallback-Reason показывается декодированным', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        fakeRenderResponse({
          'x-template-fallback': 'true',
          'x-template-fallback-reason':
            '%D0%A8%D0%B0%D0%B1%D0%BB%D0%BE%D0%BD%20%C2%ABmodern%C2%BB%20%D0%BF%D0%BE%D0%B2%D1%80%D0%B5%D0%B6%D0%B4%D1%91%D0%BD%2C%20%D0%BF%D1%80%D0%B8%D0%BC%D0%B5%D0%BD%D1%91%D0%BD%20%C2%ABclassic%C2%BB',
          'content-disposition': 'attachment; filename="doc.docx"',
        })
      )
    );

    const { httpApi } = await import('../httpApi');
    const result = await httpApi.renderDocument('id-1');

    expect(result.fallback).toBe(true);
    expect(result.fallbackReason).toBe(
      'Шаблон «modern» повреждён, применён «classic»'
    );
  });

  it('скачанный blob имеет ненулевой размер', async () => {
    const { api } = await import('../index');
    const { mockApi } = await import('../mock');

    const doc = await mockApi.createDocument({
      draft:
        'Директору ООО «Ромашка» Петрову П.П. от Иванова И.И. Прошу предоставить отпуск с 10 июня 2025 на 14 дней.',
      doc_type: 'memo',
      template_id: 'classic',
    });

    for (let i = 0; i < 6; i += 1) {
      const current = await mockApi.getDocument(doc.id);
      if (current.status !== 'processing') break;
    }

    const result = await api.renderDocument(doc.id);
    expect(result.blob.size).toBeGreaterThan(0);
  });
});