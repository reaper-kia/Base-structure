import { create } from 'zustand';
import { mockApi } from '../api/mock';
import type { DocumentState, DocType, Template, MockScenario, DevState } from '../api/types';

interface WizardState {
  // Справочники
  docTypes: DocType[];
  templates: Template[];

  // Ввод пользователя - НИКОГДА не перезаписывается ответом сервера
  draft: string;
  docType: string | null;
  templateId: string | null;

  // Текущий документ
  document: DocumentState | null;

  // Mock
  mockScenario: MockScenario;

  // UI-состояние
  isCreating: boolean;
  isPatchingRequisites: boolean;
  isRendering: boolean;
  transportError: string | null;
  pollingTimedOut: boolean;
  devState: DevState | null;
  renderFallback: string | null;
  setPollingTimedOut: (value: boolean) => void;
  loadDevState: () => Promise<void>;
  setAiForceFailure: (enabled: boolean) => Promise<void>;

  // Actions
  setDraft: (value: string) => void;
  setDocType: (id: string) => void;
  setTemplateId: (id: string) => void;
  setMockScenario: (scenario: MockScenario) => void;

  loadDocTypes: () => Promise<void>;
  loadTemplates: () => Promise<void>;

  createDocument: () => Promise<void>;
  fetchDocument: (id: string) => Promise<void>;
  patchRequisites: (values: Record<string, string | null>) => Promise<void>;
  reprocessDocument: (id: string) => Promise<void>;
  renderDocument: (id: string) => Promise<void>;
}

export const useDocumentStore = create<WizardState>((set, get) => ({
  docTypes: [],
  templates: [],
  draft: '',
  docType: null,
  templateId: null,
  document: null,
  mockScenario: 'all_found',
  isCreating: false,
  isPatchingRequisites: false,
  isRendering: false,
  transportError: null,
  pollingTimedOut: false,
  devState: null,
  renderFallback: null,
  setPollingTimedOut: (value) => set({ pollingTimedOut: value }),

  setDraft: (value) => set({ draft: value }),
  setDocType: (id) => set({ docType: id }),
  setTemplateId: (id) => set({ templateId: id }),
  setMockScenario: (scenario) => set({ mockScenario: scenario }),

  loadDocTypes: async () => {
    try {
      const docTypes = await mockApi.getDocTypes();
      set({ docTypes, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить типы документов' });
    }
  },

  loadTemplates: async () => {
    try {
      const templates = await mockApi.getTemplates();
      set({ templates, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить шаблоны' });
    }
  },

  createDocument: async () => {
    const { draft, docType, templateId } = get();
    if (!docType || !templateId || !draft.trim()) {
      return;
    }

    set({
      isCreating: true,
      transportError: null,
      pollingTimedOut: false,
      renderFallback: null,
    });
    try {
      const document = await mockApi.createDocument({
        draft,
        doc_type: docType,
        template_id: templateId,
      });
      set({ document, isCreating: false });
    } catch {
      set({
        isCreating: false,
        transportError: 'Не удалось создать документ',
      });
    }
  },

  fetchDocument: async (id) => {
    try {
      const document = await mockApi.getDocument(id);
      set({ document, transportError: null });
    } catch {
      set({ transportError: 'Не удалось получить документ' });
    }
  },

  patchRequisites: async (values) => {
    const { document } = get();
    if (!document) return;

    set({ isPatchingRequisites: true, transportError: null });
    try {
      const updated = await mockApi.patchRequisites(document.id, values);
      set({ document: updated, isPatchingRequisites: false });
    } catch {
      set({
        isPatchingRequisites: false,
        transportError: 'Не удалось обновить реквизиты',
      });
    }
  },

  reprocessDocument: async (id) => {
    try {
      const document = await mockApi.reprocessDocument(id);
      set({ document, transportError: null, pollingTimedOut: false });
    } catch {
      set({ transportError: 'Не удалось запустить повторную обработку' });
    }
  },

  renderDocument: async (id) => {
    set({ isRendering: true, transportError: null });
    try {
      const result = await mockApi.renderDocument(id);
      set({ renderFallback: result.fallbackReason, isRendering: false });

      const url = URL.createObjectURL(result.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = result.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      set({
        isRendering: false,
        transportError: 'Не удалось скачать документ',
      });
    }
  },

    loadDevState: async () => {
    try {
      const devState = await mockApi.getDevState();
      set({ devState, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить состояние dev-панели' });
    }
  },

  setAiForceFailure: async (enabled) => {
    try {
      const devState = await mockApi.setAiForceFailure(enabled);
      set({ devState });
    } catch {
      set({ transportError: 'Не удалось переключить режим отказа ИИ' });
    }
  },
}));