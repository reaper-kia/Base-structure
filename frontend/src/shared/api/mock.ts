import { Document as DocxDocument, Packer, Paragraph, TextRun } from 'docx';
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
  ChangeItem,
} from './types';

// Переключатель сценария мока — одна константа, не три ветки кода
export const MOCK_SCENARIO: MockScenario = 'all_found';

// Задержка для имитации асинхронности
const MOCK_DELAY = 1500;

// Скорость обработки: 'fast' для разработки, 'slow' для проверки экрана (~60 сек)
export const MOCK_SPEED: 'fast' | 'slow' = 'fast';
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
let documentCounter = 0;
const pollCounts = new Map<string, number>();

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

// ====== Правила трансформации черновика и генерации DOCX ======

const DOC_TYPE_FILE_NAMES: Record<string, string> = {
  memo: 'sluzhebnaya-zapiska',
  report: 'dokladnaya-zapiska',
  reference: 'informacionnaya-spravka',
  letter: 'pismo',
};

function formatDateForFilename(date: Date): string {
  const dd = String(date.getDate()).padStart(2, '0');
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const yyyy = date.getFullYear();
  return `${dd}-${mm}-${yyyy}`;
}

const STRUCTURE_HEADER = 'Служебная записка\nО предоставлении отпуска';

const IMPROVEMENT_RULES: {
  change: ChangeItem;
  apply: (text: string) => string;
}[] = [
  {
    change: { type: 'spelling', from: 'заявленее', to: 'заявление' },
    apply: (text) => text.replace(/заявленее/gi, 'заявление'),
  },
  {
    change: {
      type: 'punctuation',
      from: 'с 10 июня 2025 на 14 дней',
      to: 'с 10 июня 2025 года на 14 календарных дней',
    },
    apply: (text) =>
      text.replace(
        /с 10 июня 2025 на 14 дней/gi,
        'с 10 июня 2025 года на 14 календарных дней'
      ),
  },
  {
    change: {
      type: 'style',
      from: 'а то я уже задолбался работать без отдыха и хочу отдохнуть',
      to: '',
    },
    apply: (text) =>
      text.replace(
        /[ \t]*а то я уже задолбался работать без отдыха и хочу отдохнуть/gi,
        ''
      ),
  },
];

export function buildImprovedText(draft: string): string {
  let text = draft;

  for (const rule of IMPROVEMENT_RULES) {
    text = rule.apply(text);
  }

  if (!/служебная записка/i.test(text)) {
    text = `${STRUCTURE_HEADER}\n\n${text}`;
  }

  return text;
}

export function buildChanges(draft: string, improved: string): ChangeItem[] {
  const changes: ChangeItem[] = IMPROVEMENT_RULES.filter((rule) =>
    draft.toLowerCase().includes(rule.change.from.toLowerCase())
  ).map((rule) => rule.change);

  if (!/служебная записка/i.test(draft) && improved.includes(STRUCTURE_HEADER)) {
    changes.push({ type: 'structure', from: '', to: STRUCTURE_HEADER });
  }

  return changes;
}

const FACT_ANCHORS = [
  '10 июня 2025',
  '14 календарных дней',
  '85 000 руб.',
  '92 500 руб.',
  '7 500 руб.',
  '15 сентября 2025',
];

async function buildDocxBlob(doc: DocumentState): Promise<Blob> {
  const text = doc.improved_text ?? doc.draft;
  const paragraphs = text.split('\n').map(
    (line) =>
      new Paragraph({
        children: [new TextRun(line)],
        spacing: { after: 120 },
      })
  );

  const docxDocument = new DocxDocument({
    sections: [{ children: paragraphs }],
  });

  return Packer.toBlob(docxDocument);
}

// ====== Финальный статус документа в зависимости от сценария ======

function getTerminalDocumentState(
  draft: string,
  docType: string,
  templateId: string,
  id: string
): DocumentState {
  const improvedText = buildImprovedText(draft);
  const changes = buildChanges(draft, improvedText);

  const source = FACT_ANCHORS.filter((anchor) => draft.includes(anchor));
  const preserved = source.filter((anchor) => improvedText.includes(anchor));

  const baseState: DocumentState = {
    id,
    status: 'processed',
    stage: null,
    doc_type: docType,
    template_id: templateId,
    draft,
    improved_text: improvedText,
    changes,
    requisites: [
      {
        key: 'addressee',
        label: 'Адресат',
        value: 'Директору ООО «Ромашка» Петрову П.П.',
        status: 'found_in_draft' as RequisiteStatus,
        required: true,
      },
      {
        key: 'author',
        label: 'Автор',
        value: 'Иванов И.И.',
        status: 'found_in_draft' as RequisiteStatus,
        required: true,
      },
      {
        key: 'position',
        label: 'Должность автора',
        value: 'Менеджер отдела продаж',
        status: 'found_in_draft' as RequisiteStatus,
        required: true,
      },
      {
        key: 'subject',
        label: 'Заголовок к тексту',
        value: 'О предоставлении отпуска',
        status: 'found_in_draft' as RequisiteStatus,
        required: true,
      },
      {
        key: 'doc_date',
        label: 'Дата документа',
        value: '11.09.2026',
        status: 'auto_filled' as RequisiteStatus,
        required: true,
      },
    ],
    fact_guard: {
      verdict: 'clean',
      preserved,
      lost: source.filter((anchor) => !preserved.includes(anchor)),
      added: [],
      source_count: source.length,
      preserved_count: preserved.length,
    },
    is_fallback: false,
    error: null,
  };

  if (MOCK_SCENARIO === 'no_addressee') {
    return {
      ...baseState,
      requisites: baseState.requisites.map((req) =>
        req.key === 'addressee'
          ? { ...req, value: null, status: 'missing' as const }
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
        message:
          'ИИ-компонент недоступен. Черновик сохранён, попробуйте ещё раз.',
        recoverable: true,
      },
    };
  }

  return baseState;
}

// ====== API моки ======

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
    pollCounts.set(id, 0);
    documents.set(id, doc);
    return doc;
  },

  async getDocument(id: string): Promise<DocumentState> {
    await delay(MOCK_POLL_DELAY);
    const doc = documents.get(id);
    if (!doc) {
      throw new Error('Документ не найден');
    }

    if (doc.status !== 'processing') {
      return { ...doc };
    }

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

    if (doc.status === 'processing') {
      throw new Error('Документ уже обрабатывается');
    }

    pollCounts.set(id, 0);

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

    const blob = await buildDocxBlob(doc);
    const baseName = DOC_TYPE_FILE_NAMES[doc.doc_type] ?? 'document';
    const filename = `${baseName}-${formatDateForFilename(new Date())}.docx`;

    return { blob, filename };
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
          auto_filled: doc.requisites
            .filter((r) => r.status === 'auto_filled')
            .map((r) => r.key),
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