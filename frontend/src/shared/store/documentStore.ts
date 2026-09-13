import { create } from 'zustand';
import { api } from '../api';
import type {
  DocumentState,
  DocType,
  Template,
  MockScenario,
  DevState,
} from '../api/types';

// FE-F3, осознанное решение: черновик живёт в sessionStorage — переживает
// F5 и перезагрузку внутри вкладки, но не тащит старый текст в новую
// сессию после закрытия вкладки. Это выбор, а не баг.
const WIZARD_SESSION_KEY = 'doc3-wizard-session';

interface WizardSession {
  draft: string;
  docType: string | null;
  templateId: string | null;
}

function readWizardSession(): WizardSession {
  const empty: WizardSession = { draft: '', docType: null, templateId: null };
  try {
    const raw = sessionStorage.getItem(WIZARD_SESSION_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as Partial<WizardSession>;
    return {
      draft: typeof parsed.draft === 'string' ? parsed.draft : '',
      docType: typeof parsed.docType === 'string' ? parsed.docType : null,
      templateId: typeof parsed.templateId === 'string' ? parsed.templateId : null,
    };
  } catch {
    return empty;
  }
}

export function persistWizardSession(state: WizardSession): void {
  try {
    sessionStorage.setItem(WIZARD_SESSION_KEY, JSON.stringify(state));
  } catch {
    // sessionStorage недоступен (приватный режим) — не критично
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Неизвестная ошибка';
}

interface WizardState {
  docTypes: DocType[];
  templates: Template[];

  // Ввод пользователя: никогда не перезаписывается ответом сервера
  draft: string;
  docType: string | null;
  templateId: string | null;

  activeDocumentId: string | null;
  document: DocumentState | null;

  mockScenario: MockScenario;

  isCreating: boolean;
  isPatchingRequisites: boolean;
  isRendering: boolean;
  renderFallback: string | null;
  transportError: string | null;
  pollingTimedOut: boolean;

  devState: DevState | null;

  setDraft: (value: string) => void;
  setDocType: (id: string) => void;
  setTemplateId: (id: string) => void;
  setMockScenario: (scenario: MockScenario) => void;

  loadDocTypes: () => Promise<void>;
  loadTemplates: () => Promise<void>;

  createDocument: () => Promise<void>;
  fetchDocument: (id: string) => Promise<void>;
  fetchDocumentSafe: (id: string, signal?: AbortSignal) => Promise<boolean>;
  resumePolling: () => void;
  patchRequisites: (values: Record<string, string | null>) => Promise<void>;
  reprocessDocument: (id: string) => Promise<void>;
  renderDocument: (id: string) => Promise<void>;

  loadDevState: () => Promise<void>;
  setAiForceFailure: (enabled: boolean) => Promise<void>;
  setPollingTimedOut: (value: boolean) => void;
  resetWizard: () => void;
}

const session = readWizardSession();

export const useDocumentStore = create<WizardState>((set, get) => ({
  docTypes: [],
  templates: [],

  draft: session.draft,
  docType: session.docType,
  templateId: session.templateId,

  activeDocumentId: null,
  document: null,

  mockScenario: 'all_found',

  isCreating: false,
  isPatchingRequisites: false,
  isRendering: false,
  renderFallback: null,
  transportError: null,
  pollingTimedOut: false,

  devState: null,

  setDraft: (value) => {
    set({ draft: value });
    const s = get();
    persistWizardSession({
      draft: s.draft,
      docType: s.docType,
      templateId: s.templateId,
    });
  },

  setDocType: (id) => {
    set({ docType: id });
    const s = get();
    persistWizardSession({
      draft: s.draft,
      docType: s.docType,
      templateId: s.templateId,
    });
  },

  setTemplateId: (id) => {
    set({ templateId: id });
    const s = get();
    persistWizardSession({
      draft: s.draft,
      docType: s.docType,
      templateId: s.templateId,
    });
  },

  setMockScenario: (scenario) => set({ mockScenario: scenario }),

  loadDocTypes: async () => {
    try {
      const docTypes = await api.getDocTypes();
      set({ docTypes, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить типы документов' });
    }
  },

  loadTemplates: async () => {
    try {
      const templates = await api.getTemplates();
      set({ templates, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить шаблоны' });
    }
  },

  createDocument: async () => {
    const { draft, docType, templateId } = get();
    if (!docType || !templateId || !draft.trim()) return;

    set({
      isCreating: true,
      transportError: null,
      pollingTimedOut: false,
      renderFallback: null,
    });
    try {
      const document = await api.createDocument({
        draft,
        doc_type: docType,
        template_id: templateId,
      });
      set({ document, activeDocumentId: document.id, isCreating: false });
    } catch {
      set({ isCreating: false, transportError: 'Не удалось создать документ' });
    }
  },

  fetchDocument: async (id) => {
    set({ activeDocumentId: id });
    try {
      const document = await api.getDocument(id);
      if (get().activeDocumentId !== id) return;
      set({ document, transportError: null });
    } catch (error) {
      if (get().activeDocumentId !== id) return;
      set({ transportError: errorMessage(error) });
    }
  },

  // Ответ по старому id игнорируется: пишем только если это всё ещё
  // актуальный документ и запрос не отменён
  fetchDocumentSafe: async (id, signal) => {
    try {
      const document = await api.getDocument(id);
      if (signal?.aborted) return false;
      if (get().activeDocumentId !== id) return false;
      set({ document, transportError: null });
      return true;
    } catch {
      return false;
    }
  },

  resumePolling: () => set({ pollingTimedOut: false }),

  patchRequisites: async (values) => {
    const { document } = get();
    if (!document) return;

    set({ isPatchingRequisites: true });
    try {
      const updated = await api.patchRequisites(document.id, values);
      set({ document: updated, isPatchingRequisites: false });
    } catch (error) {
      set({ isPatchingRequisites: false });
      throw error;
    }
  },

  reprocessDocument: async (id) => {
    try {
      const document = await api.reprocessDocument(id);
      set({
        document,
        activeDocumentId: id,
        transportError: null,
        pollingTimedOut: false,
      });
    } catch {
      set({ transportError: 'Не удалось запустить повторную обработку' });
    }
  },

  renderDocument: async (id) => {
    set({ isRendering: true, transportError: null });
    try {
      const result = await api.renderDocument(id);
      set({ renderFallback: result.fallbackReason, isRendering: false });

      const url = URL.createObjectURL(result.blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = result.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      set({ isRendering: false, transportError: 'Не удалось скачать документ' });
    }
  },

  loadDevState: async () => {
    try {
      const devState = await api.getDevState();
      set({ devState, transportError: null });
    } catch {
      set({ transportError: 'Не удалось загрузить состояние dev-панели' });
    }
  },

  setAiForceFailure: async (enabled) => {
    try {
      const devState = await api.setAiForceFailure(enabled);
      set({ devState });
    } catch {
      set({ transportError: 'Не удалось переключить режим отказа ИИ' });
    }
  },

  setPollingTimedOut: (value) => set({ pollingTimedOut: value }),

  // FE-F2: единая точка сброса визарда. Чистит и sessionStorage,
  // чтобы новый документ начинался с чистого шага 1.
  resetWizard: () => {
    set({
      draft: '',
      docType: null,
      templateId: null,
      document: null,
      activeDocumentId: null,
      renderFallback: null,
      transportError: null,
      pollingTimedOut: false,
      isCreating: false,
      isPatchingRequisites: false,
      isRendering: false,
    });
    try {
      sessionStorage.removeItem(WIZARD_SESSION_KEY);
    } catch {
      // sessionStorage недоступен — очищать нечего
    }
  },
}));