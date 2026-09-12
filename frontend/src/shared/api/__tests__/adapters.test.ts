import { describe, it, expect, vi, afterEach } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

function collectFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      collectFiles(full, acc);
    } else if (/\.(ts|tsx)$/.test(entry)) {
      acc.push(full);
    }
  }
  return acc;
}

function fakeResponse(json: unknown) {
  return {
    ok: true,
    status: 200,
    json: async () => json,
    headers: { get: () => null },
  };
}

describe('FE-09: один API, два адаптера', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it('при USE_MOCK=false стор ходит в httpApi (fetch)', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const fetchMock = vi.fn().mockResolvedValue(
      fakeResponse([
        { id: 'memo', name: 'Служебная записка', description: '', requisites: [] },
      ])
    );
    vi.stubGlobal('fetch', fetchMock);

    const { useDocumentStore } = await import('../../store/documentStore');
    await useDocumentStore.getState().loadDocTypes();

    expect(fetchMock).toHaveBeenCalled();
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/doc-types');
  });

  it('httpApi понимает обе формы ответа GET /templates', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    const fetchMock = vi.fn().mockResolvedValue(
      fakeResponse({
        templates: [
          {
            id: 'classic',
            name: 'Классический',
            description: '',
            preview_url: '',
            available: true,
          },
        ],
      })
    );
    vi.stubGlobal('fetch', fetchMock);

    const { httpApi } = await import('../httpApi');
    const templates = await httpApi.getTemplates();

    expect(Array.isArray(templates)).toBe(true);
    expect(templates[0].id).toBe('classic');
  });

  it('справка: 5 реквизитов, 4 обязательных, адресат необязательный', async () => {
    const { mockApi } = await import('../mock');
    const types = await mockApi.getDocTypes();
    const reference = types.find((type) => type.id === 'reference');

    expect(reference?.requisites).toHaveLength(5);
    expect(reference?.requisites.filter((req) => req.required)).toHaveLength(4);
    expect(
      reference?.requisites.find((req) => req.key === 'addressee')?.required
    ).toBe(false);
    expect(
      reference?.requisites.some((req) => req.key === 'signature')
    ).toBe(true);
  });

  it('компоненты не импортируют mock напрямую', () => {
    const roots = [
      'src/pages',
      'src/widgets',
      'src/features',
      'src/shared/store',
      'src/shared/ui',
      'src/shared/hooks',
    ];
    const offenders: string[] = [];

    for (const root of roots) {
      for (const file of collectFiles(join(process.cwd(), root))) {
        const source = readFileSync(file, 'utf8');
        if (/from\s+['"][^'"]*\/mock['"]/.test(source)) {
          offenders.push(file);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});