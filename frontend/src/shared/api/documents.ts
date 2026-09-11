import { apiClient } from './client';

export type RequisiteStatus =
  | 'found_in_draft'
  | 'user_provided'
  | 'auto_filled'
  | 'missing';

export interface Requisite {
  key: string;
  label: string;
  value: string | null;
  status: RequisiteStatus;
  required: boolean;
}

export interface DocumentState {
  id: string;
  status: 'created' | 'processed' | 'degraded' | 'failed';
  draft: string;
  improved_text: string | null;
  changes: { type: string; from: string; to: string }[];
  requisites: Requisite[];
  fact_guard: { preserved: string[]; lost: string[]; added: string[]; verdict: string } | null;
  error: { code: string; message: string; recoverable: boolean } | null;
}

// Пока бэкенд не готов - переключить на моки одной строкой.
export const documentsApi = {
  docTypes: () => apiClient.get<{ id: string; name: string }[]>('/api/doc-types'),
  templates: () => apiClient.get<{ id: string; name: string; description: string }[]>('/api/templates'),
  create: (draft: string, docType: string, templateId: string) =>
    apiClient.post<DocumentState>('/api/documents', {
      draft,
      doc_type: docType,
      template_id: templateId,
    }),
  get: (id: string) => apiClient.get<DocumentState>(`/api/documents/${id}`),
  updateRequisites: (id: string, values: Record<string, string | null>) =>
    apiClient.patch<DocumentState>(`/api/documents/${id}/requisites`, { values }),
  renderUrl: (id: string) => `/api/documents/${id}/render`,
};
