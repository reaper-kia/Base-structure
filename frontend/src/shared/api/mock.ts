import type {
  DocumentState,
  DocType,
  Template,
  MockScenario,
  TraceEntry,
  DevState,
  RequisiteState,
  RequisiteStatus,
  ProcessingStage,
} from './types';

// Переключатель сценария мока - одна константа, не три ветки кода
export const MOCK_SCENARIO: MockScenario = 'all_found';

// Задержка для имитации асинхронности
const MOCK_DELAY = 1500;

// Скорость обработки: 'fast' для разработки, 'slow' для проверки экрана (~60 сек)
export const MOCK_SPEED: 'fast' | 'slow' = 'slow';
const POLLS_PER_STAGE = MOCK_SPEED === 'fast' ? 1 : 20;
const MOCK_POLL_DELAY = 300;

// Моковые данные для справочников
const mockDocTypes: DocType[] = [
  {
    id: 'memo',
    name: 'Служебная записка',
    description: 'Внутренний документ с просьбой или предложением',
    requisites: [
      { key: 'addressee', label: 'Адресат', required: true },
      { key: 'author', label: 'Автор', required: true },
      { key: 'position', label: 'Должность автора', required: true },
      { key: 'subject', label: 'Заголовок к тексту', required: true },
      { key: 'doc_date', label: 'Дата документа', required: true },
    ],
  },
  {
    id: 'report',
    name: 'Докладная записка',
    description: 'Сообщение о событии или нарушении',
    requisites: [
      { key: 'addressee', label: 'Адресат', required: true },
      { key: 'author', label: 'Автор', required: true },
      { key: 'position', label: 'Должность автора', required: true },
      { key: 'subject', label: 'Заголовок', required: true },
      { key: 'doc_date', label: 'Дата документа', required: true },
    ],
  },
  {
    id: 'reference',
    name: 'Информационная справка',
    description: 'Справка о статусе или фактах',
    requisites: [
      { key: 'addressee', label: 'Адресат', required: true },
      { key: 'author', label: 'Автор', required: true },
      { key: 'position', label: 'Должность автора', required: true },
      { key: 'subject', label: 'Заголовок', required: true },
      { key: 'doc_date', label: 'Дата документа', required: true },
    ],
  },
  {
    id: 'letter',
    name: 'Письмо',
    description: 'Внешнее письмо контрагенту',
    requisites: [
      { key: 'addressee', label: 'Адресат', required: true },
      { key: 'author', label: 'Автор', required: true },
      { key: 'position', label: 'Должность автора', required: true },
      { key: 'subject', label: 'Тема письма', required: true },
      { key: 'doc_date', label: 'Дата документа', required: true },
    ],
  },
];

const mockTemplates: Template[] = [
  {
    id: 'classic',
    name: 'Классический',
    description: 'ГОСТ-подобное оформление: Times New Roman 14, поля 30 мм',
    preview_url: '/static/templates/classic.png',
    available: true,
  },
  {
    id: 'modern',
    name: 'Современный',
    description: 'Arial 12, узкие поля, колонтитул с названием организации',
    preview_url: '/static/templates/modern.png',
    available: true,
  },
  {
    id: 'corporate',
    name: 'Корпоративный',
    description: 'Фирменный стиль компании с логотипом',
    preview_url: '/static/templates/corporate.png',
    available: false,
  },
];

// Хранилище документов в памяти
const documents = new Map<string, DocumentState>();
const pollCounts = new Map<string, number>();
let documentCounter = 0;

// Состояние dev-панели
let devState: DevState = {
  ai_force_failure: false,
  ml_service_url: 'http://ml_service:8100',
  ml_reachable: true,
  model_version: 'qwen2.5:7b-instruct',
  templates_loaded: ['classic', 'modern'],
};

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function generateId(): string {
  return `${Date.now()}-${++documentCounter}`;
}

// Получить финальный статус документа в зависимости от сценария
function getTerminalDocumentState(
  draft: string,
  docType: string,
  templateId: string,
  id: string
): DocumentState {
  const baseState: DocumentState = {
    id,
    status: 'processed',
    stage: null,
    doc_type: docType,
    template_id: templateId,
    draft,
    improved_text: 'Прошу предоставить мне ежегодный оплачиваемый отпуск с 10 июня 2025 года на 14 календарных дней.',
    changes: [
      { type: 'spelling', from: 'заявленее', to: 'заявление' },
      { type: 'style', from: 'а то я уже задолбался', to: '' },
    ],
    requisites: [
      {
        key: 'addressee',
        label: 'Адресат',
        value: 'Директору ООО «Ромашка» Петрову П.П.',
        status: 'found_in_draft',
        required: true,
      },
      {
        key: 'author',
        label: 'Автор',
        value: 'Иванов И.И.',
        status: 'found_in_draft',
        required: true,
      },
      {
        key: 'position',
        label: 'Должность автора',
        value: 'Менеджер отдела продаж',
        status: 'found_in_draft',
        required: true,
      },
      {
        key: 'subject',
        label: 'Заголовок к тексту',
        value: 'О предоставлении отпуска',
        status: 'found_in_draft',
        required: true,
      },
      {
        key: 'doc_date',
        label: 'Дата документа',
        value: '11.09.2026',
        status: 'auto_filled',
        required: true,
      },
    ],
    fact_guard: {
      verdict: 'clean',
      preserved: ['10 июня 2025', '14 календарных дней'],
      lost: [],
      added: [],
      source_count: 2,
      preserved_count: 2,
    },
    is_fallback: false,
    error: null,
  };

  if (MOCK_SCENARIO === 'no_addressee') {
    return {
      ...baseState,
      requisites: baseState.requisites.map((req) =>
        req.key === 'addressee'
          ? { ...req, value: null, status: 'missing' }
          : req
      ),
    };
  }

  if (MOCK_SCENARIO === 'ai_failed' || devState.ai_force_failure) {
    return {
      ...baseState,
      status: 'failed',
      improved_text: null,
      changes: [],
      requisites: [],
      fact_guard: null,
      error: {
        code: 'llm_unavailable',
        message: 'ИИ-компонент недоступен. Черновик сохранён, попробуйте ещё раз.',
        recoverable: true,
      },
    };
  }

  return baseState;
}

// API моки
export const mockApi = {
  async getDocTypes(): Promise<DocType[]> {
    await delay(MOCK_DELAY);
    return mockDocTypes;
  },

  async getTemplates(): Promise<Template[]> {
    await delay(MOCK_DELAY);
    return mockTemplates;
  },

  async createDocument(data: {
    draft: string;
    doc_type: string;
    template_id: string;
  }): Promise<DocumentState> {
    await delay(MOCK_DELAY);
    const id = generateId();
    const doc: DocumentState = {
      id,
      status: 'processing',
      stage: 'llm',
      doc_type: data.doc_type,
      template_id: data.template_id,
      draft: data.draft,
      improved_text: null,
      changes: [],
      requisites: [],
      fact_guard: null,
      is_fallback: false,
      error: null,
    };
    documents.set(id, doc);
    pollCounts.set(id, 0);
    return doc;
  },

  async getDocument(id: string): Promise<DocumentState> {
    await delay(MOCK_POLL_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    // Если документ уже в терминальном статусе — возвращаем как есть
    if (doc.status !== 'processing') {
      return { ...doc };
    }

    // Продвигаем стадию в зависимости от количества поллингов
    const count = (pollCounts.get(id) || 0) + 1;
    pollCounts.set(id, count);

    const stageIndex = Math.floor((count - 1) / POLLS_PER_STAGE);

    if (stageIndex >= 3) {
      const terminal = getTerminalDocumentState(
        doc.draft,
        doc.doc_type,
        doc.template_id,
        doc.id
      );
      documents.set(id, terminal);
      return { ...terminal };
    }

    const stages: ProcessingStage[] = ['llm', 'fact_guard', 'validation'];
    const updated: DocumentState = { ...doc, stage: stages[stageIndex] };
    documents.set(id, updated);
    return { ...updated };
  },

  async patchRequisites(
    id: string,
    values: Record<string, string | null>
  ): Promise<DocumentState> {
    await delay(MOCK_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    if (doc.status === 'processing') {
      throw new Error('Документ ещё обрабатывается');
    }

    const updatedRequisites: RequisiteState[] = doc.requisites.map((req) => {
      if (req.key in values) {
        const value = values[req.key];
        const status: RequisiteStatus =
          value === null ? 'left_blank' : 'user_provided';
        return {
          ...req,
          value,
          status,
        };
      }
      return req;
    });

    const updated: DocumentState = {
      ...doc,
      requisites: updatedRequisites,
    };
    documents.set(id, updated);
    return updated;
  },

  async reprocessDocument(id: string): Promise<DocumentState> {
    await delay(MOCK_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    pollCounts.set(id, 0);
    if (doc.status === 'processing') {
      throw new Error('Документ уже обрабатывается');
    }

    const reprocessing: DocumentState = {
      ...doc,
      status: 'processing',
      stage: 'llm',
      improved_text: null,
      changes: [],
      fact_guard: null,
      error: null,
    };
    documents.set(id, reprocessing);
    return reprocessing;
  },

  async renderDocument(id: string): Promise<{ blob: Blob; filename: string }> {
    await delay(MOCK_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    if (doc.status === 'processing' || doc.status === 'failed') {
      throw new Error('Документ ещё не обработан');
    }

    // Создаём фиктивный DOCX
    const content = `Документ: ${doc.doc_type}\n\nЧерновик:\n${doc.draft}\n\nУлучшенный текст:\n${doc.improved_text || 'Нет'}`;
    const blob = new Blob([content], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    return {
      blob,
      filename: `${doc.doc_type}-${new Date().toISOString().split('T')[0]}.docx`,
    };
  },

  async getTrace(id: string): Promise<TraceEntry[]> {
    await delay(MOCK_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    return [
      {
        stage: 'anchors',
        payload: { date: ['10 июня 2025'], amount: ['14 календарных дней'] },
      },
      {
        stage: 'llm_request',
        payload: {
          prompt: 'Ты — помощник делопроизводителя...',
          doc_type: doc.doc_type,
        },
      },
      {
        stage: 'llm_raw',
        payload: {
          improved_text: doc.improved_text,
          requisites: doc.requisites,
        },
      },
      {
        stage: 'fact_guard',
        payload: doc.fact_guard || { verdict: 'clean', added: [], lost: [] },
      },
      {
        stage: 'validation',
        payload: {
          missing: doc.requisites.filter((r) => r.status === 'missing').map((r) => r.key),
          auto_filled: doc.requisites.filter((r) => r.status === 'auto_filled').map((r) => r.key),
        },
      },
      {
        stage: 'render',
        payload: {
          template_id: doc.template_id,
          rules_applied: { font: 'Times New Roman', size_pt: 14 },
        },
      },
    ];
  },

  async getDevState(): Promise<DevState> {
    await delay(MOCK_DELAY / 2);
    return { ...devState };
  },

  async setAiForceFailure(enabled: boolean): Promise<DevState> {
    await delay(MOCK_DELAY / 2);
    devState = { ...devState, ai_force_failure: enabled };
    return { ...devState };
  },
};