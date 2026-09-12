import { parseContentDisposition } from './contentDisposition';
import type { DocumentApi, RenderResult } from './contract';
import type {
  DevState,
  DocumentState,
  DocType,
  Template,
  TraceEntry,
} from './types';

const BASE = '/api';

const STATUS_MESSAGES: Record<number, string> = {
  404: 'Документ не найден',
  409: 'Документ ещё обрабатывается',
  422: 'Проверьте введённые данные',
  500: 'Сервис временно недоступен',
};

function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === 'object') {
    const record = payload as Record<string, unknown>;
    if (typeof record.detail === 'string') return record.detail;
    if (Array.isArray(record.detail) && record.detail.length > 0) {
      const first = record.detail[0] as Record<string, unknown>;
      if (typeof first.msg === 'string') return first.msg;
    }
    if (typeof record.message === 'string') return record.message;
  }
  return STATUS_MESSAGES[status] ?? `Ошибка запроса (${status})`;
}

function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const hasBody = options.body !== undefined;
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined);
    throw new Error(extractMessage(payload, response.status));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const httpApi: DocumentApi = {
  getDocTypes: () => request<DocType[]>('/doc-types'),

  getTemplates: async () => {
    const json = await request<unknown>('/templates');
    // Пока форма ответа не зафиксирована TL-10, принимаем оба варианта:
    // массив (канон api.md) и обёртку { templates: [...] }
    if (Array.isArray(json)) return json as Template[];
    const wrapped = json as { templates?: Template[] };
    return wrapped.templates ?? [];
  },

  createDocument: (data) =>
    request<DocumentState>('/documents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getDocument: (id) => request<DocumentState>(`/documents/${id}`),

  patchRequisites: (id, values) =>
    request<DocumentState>(`/documents/${id}/requisites`, {
      method: 'PATCH',
      body: JSON.stringify({ values }),
    }),

  updateText: (id, improvedText) =>
    request<DocumentState>(`/documents/${id}/text`, {
      method: 'PATCH',
      body: JSON.stringify({ improved_text: improvedText }),
    }),

  reprocessDocument: (id) =>
    request<DocumentState>(`/documents/${id}/reprocess`, { method: 'POST' }),

  renderDocument: async (id): Promise<RenderResult> => {
    const response = await fetch(`${BASE}/documents/${id}/render`, {
      method: 'POST',
    });

    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => undefined);
      throw new Error(extractMessage(payload, response.status));
    }

    const blob = await response.blob();
    const rawReason = response.headers.get('X-Template-Fallback-Reason');

    return {
      blob,
      filename: parseContentDisposition(
        response.headers.get('Content-Disposition'),
        'document.docx'
      ),
      fallback: response.headers.get('X-Template-Fallback') === 'true',
      fallbackReason: rawReason ? safeDecode(rawReason) : null,
    };
  },

  getTrace: (id) => request<TraceEntry[]>(`/trace/${id}`),

  getDevState: () => request<DevState>('/dev/state'),

  setAiForceFailure: (enabled) =>
    request<DevState>('/dev/break-ai', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),

  // Повреждение шаблона воспроизводимо только в демо-режиме
  getTemplateBroken: async () => false,
  setTemplateBroken: async () => ({ template_broken: false }),
};