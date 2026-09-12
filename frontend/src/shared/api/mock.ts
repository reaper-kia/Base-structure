import { Document as DocxDocument, Packer, Paragraph, TextRun } from 'docx';
import type { DocumentApi } from './contract';
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

const MOCK_DELAY = 1500;

// Скорость обработки: 'fast' для разработки, 'slow' для проверки экрана (~60 сек)
export const MOCK_SPEED: 'fast' | 'slow' = 'fast';
const POLLS_PER_STAGE = MOCK_SPEED === 'fast' ? 1 : 20;
const MOCK_POLL_DELAY = 300;

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
      { key: 'author', label: 'Автор', required: true },
      { key: 'subject', label: 'Заголовок к тексту', required: true },
      { key: 'doc_date', label: 'Дата документа', required: true },
      { key: 'signature', label: 'Подпись', required: true },
      { key: 'addressee', label: 'Адресат', required: false },
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

const documents = new Map<string, DocumentState>();
let documentCounter = 0;
const pollCounts = new Map<string, number>();

let devState: DevState = {
  ai_force_failure: false,
  ml_service_url: 'http://ml_service:8100',
  ml_reachable: true,
  model_version: 'qwen2.5:7b-instruct',
  templates_loaded: ['classic', 'modern'],
};
let templateBroken = false;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function generateId(): string {
  return `${Date.now()}-${++documentCounter}`;
}

// ====== Мини-ИИ: извлечение реквизитов из черновика ======

const DOC_TYPE_HEADERS: Record<string, string> = {
  memo: 'Служебная записка',
  report: 'Докладная записка',
  reference: 'Информационная справка',
  letter: 'Письмо',
};

const NAME_RE = /^[А-ЯЁ][а-яё]+(\s[А-ЯЁ]\.[А-ЯЁ]\.)+$/;
const SHORT_NAME_RE = /^[А-ЯЁ][а-яё]+$/;
const DATE_RE = /^\d{1,2}\.\d{1,2}\.\d{4}$/;

function isName(line: string): boolean {
  return NAME_RE.test(line) || (SHORT_NAME_RE.test(line) && line.length >= 4);
}

function isPosition(line: string): boolean {
  return (
    /^[А-ЯЁ]/.test(line) &&
    !isName(line) &&
    !DATE_RE.test(line) &&
    !/^(прошу|довожу|настоящая|уважаемый|основание)/i.test(line) &&
    line.length <= 60
  );
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function todayDate(): string {
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, '0');
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  return `${dd}.${mm}.${now.getFullYear()}`;
}

function hasTypeHeader(text: string): boolean {
  const lines = text.split('\n').map((line) => line.trim().toLowerCase());
  return lines.some((line) =>
    Object.values(DOC_TYPE_HEADERS).some(
      (header) => line === header.toLowerCase()
    )
  );
}

export function extractRequisites(
  draft: string,
  docType: string
): RequisiteState[] {
  const lines = draft
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  const addresseeLine =
    lines.find((line) =>
      /^(директору|руководителю|начальнику|адресат)/i.test(line)
    ) ?? null;

  let authorFromSignature: string | null = null;
  let positionFromSignature: string | null = null;
  for (let i = lines.length - 1; i >= 0 && i >= lines.length - 4; i -= 1) {
    if (DATE_RE.test(lines[i])) continue;
    if (!authorFromSignature && isName(lines[i])) {
      authorFromSignature = lines[i];
      continue;
    }
    if (authorFromSignature && isPosition(lines[i])) {
      positionFromSignature = lines[i];
      break;
    }
    if (authorFromSignature) break;
  }

  let authorFromFrom: string | null = null;
  let positionFromFrom: string | null = null;
  const fromLine = lines.find((line) => /^от\s/i.test(line));
  if (fromLine) {
    const rest = fromLine.replace(/^от\s+/i, '');
    const match = rest.match(
      /^(.*?)\s+([А-ЯЁ][а-яё]+(?:\s[А-ЯЁ]\.[А-ЯЁ]\.)+|[А-ЯЁ][а-яё]+)$/
    );
    if (match) {
      positionFromFrom = capitalize(match[1]);
      authorFromFrom = match[2];
    } else {
      authorFromFrom = rest;
    }
  }

  const author = authorFromSignature ?? authorFromFrom;
  const position = positionFromSignature ?? positionFromFrom;
  const subjectLine =
    lines.find((line) => /^(о|об)\s+[а-яёa-z]/i.test(line)) ?? null;
  const dateLine = lines.find((line) => DATE_RE.test(line)) ?? null;

  const extracted: Record<string, { value: string | null; auto?: boolean }> = {
    addressee: { value: addresseeLine },
    author: { value: author },
    position: { value: position },
    subject: { value: subjectLine },
    signature: { value: authorFromSignature },
    doc_date: { value: dateLine ?? todayDate(), auto: !dateLine },
  };

  const schema =
    mockDocTypes.find((type) => type.id === docType)?.requisites ?? [];

  return schema.map((field) => {
    const entry = extracted[field.key] ?? { value: null };
    return {
      key: field.key,
      label: field.label,
      value: entry.value,
      status: (entry.auto
        ? 'auto_filled'
        : entry.value
          ? 'found_in_draft'
          : 'missing') as RequisiteStatus,
      required: field.required,
    };
  });
}

// ====== Правила улучшения текста ======

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

export function buildImprovedText(draft: string, docType: string): string {
  let text = draft;

  for (const rule of IMPROVEMENT_RULES) {
    text = rule.apply(text);
  }

  if (!hasTypeHeader(text)) {
    const header = DOC_TYPE_HEADERS[docType] ?? DOC_TYPE_HEADERS.memo;
    const out = text.split('\n');
    let index = out.findIndex((line) => /^(о|об)\s/i.test(line.trim()));
    if (index < 0) {
      index = out.findIndex((line) =>
        /^(прошу|довожу|настоящая|уважаемый)/i.test(line.trim())
      );
    }
    if (index < 0) {
      text = `${header}\n\n${text}`;
    } else {
      out.splice(index, 0, header, '');
      text = out.join('\n');
    }
  }

  return text;
}

export function buildChanges(
  draft: string,
  improved: string,
  docType: string
): ChangeItem[] {
  void improved;

  const changes: ChangeItem[] = IMPROVEMENT_RULES.filter((rule) =>
    draft.toLowerCase().includes(rule.change.from.toLowerCase())
  ).map((rule) => rule.change);

  if (!hasTypeHeader(draft)) {
    const header = DOC_TYPE_HEADERS[docType] ?? DOC_TYPE_HEADERS.memo;
    changes.push({ type: 'structure', from: '', to: header });
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

// ====== Рендерер: реквизиты накладываются на документ ======

function placeholderFor(requisite: RequisiteState): string {
  return `[${requisite.label}]`;
}

export function buildFinalDocumentText(doc: DocumentState): string {
  const base = doc.improved_text ?? doc.draft;
  let lines = base.split('\n');

  const byKey = new Map(doc.requisites.map((req) => [req.key, req]));

  const replaceOrPlace = (
    predicate: (line: string) => boolean,
    replacement: string,
    ifNotFound: 'prepend' | 'append'
  ) => {
    const index = lines.findIndex(predicate);
    if (index >= 0) {
      lines[index] = replacement;
      return;
    }
    lines =
      ifNotFound === 'prepend'
        ? [replacement, '', ...lines]
        : [...lines, replacement];
  };

  const addressee = byKey.get('addressee');
  if (addressee) {
    replaceOrPlace(
      (line) => /^(директору|руководителю|начальнику|адресат)/i.test(line.trim()),
      addressee.value ?? placeholderFor(addressee),
      'prepend'
    );
  }

  const author = byKey.get('author');
  const position = byKey.get('position');
  if (author || position) {
    const parts = [
      position ? position.value ?? placeholderFor(position) : null,
      author ? author.value ?? placeholderFor(author) : null,
    ].filter(Boolean);
    replaceOrPlace(
      (line) => /^от\s/i.test(line.trim()),
      `от ${parts.join(' ')}`,
      'prepend'
    );
  }

  const subject = byKey.get('subject');
  if (subject) {
    replaceOrPlace(
      (line) => /^(о|об)\s/i.test(line.trim()),
      subject.value ?? placeholderFor(subject),
      'append'
    );
  }

  const docDate = byKey.get('doc_date');
  if (docDate) {
    replaceOrPlace(
      (line) => /^\s*\d{1,2}\.\d{1,2}\.\d{4}\s*$/.test(line),
      docDate.value ?? placeholderFor(docDate),
      'append'
    );
  }

  return lines.join('\n');
}

function lineToRuns(line: string): TextRun[] {
  return line
    .split(/(\[[^\]]+\])/g)
    .filter((part) => part.length > 0)
    .map((part) =>
      part.startsWith('[') && part.endsWith(']')
        ? new TextRun({ text: part, highlight: 'yellow' })
        : new TextRun({ text: part })
    );
}

async function buildDocxBlob(doc: DocumentState): Promise<Blob> {
  const text = buildFinalDocumentText(doc);
  const paragraphs = text.split('\n').map(
    (line) =>
      new Paragraph({
        children: lineToRuns(line),
        spacing: { after: 120 },
      })
  );

  const docxDocument = new DocxDocument({
    sections: [{ children: paragraphs }],
  });

  return Packer.toBlob(docxDocument);
}

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

// ====== Финальное состояние документа ======

function getTerminalDocumentState(
  draft: string,
  docType: string,
  templateId: string,
  id: string
): DocumentState {
  const improvedText = buildImprovedText(draft, docType);
  const changes = buildChanges(draft, improvedText, docType);
  const requisites = extractRequisites(draft, docType);

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
    requisites,
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

export const mockApi: DocumentApi = {
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

  async renderDocument(id: string): Promise<{
    blob: Blob;
    filename: string;
    fallback: boolean;
    fallbackReason: string | null;
  }> {  
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

    const fallback = templateBroken && doc.template_id === 'modern';

    return {
      blob,
      filename,
      fallback,
      fallbackReason: fallback
        ? 'Шаблон «modern» повреждён, применён «classic»'
        : null,
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
        payload: {
          date: ['10 июня 2025'],
          amount: ['14 календарных дней'],
        },
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
          missing: doc.requisites
            .filter((req) => req.status === 'missing')
            .map((req) => req.key),
          auto_filled: doc.requisites
            .filter((req) => req.status === 'auto_filled')
            .map((req) => req.key),
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

    async getTemplateBroken(): Promise<boolean> {
    await delay(MOCK_DELAY / 2);
    return templateBroken;
  },

  async setTemplateBroken(enabled: boolean): Promise<{ template_broken: boolean }> {
    await delay(MOCK_DELAY / 2);
    templateBroken = enabled;
    return { template_broken: enabled };
  },
};