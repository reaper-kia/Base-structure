import { describe, expect, it } from 'vitest';
import { buildFinalDocumentText } from '../mock';
import type { DocumentState, RequisiteState } from '../types';

function makeDoc(requisites: RequisiteState[], improved: string): DocumentState {
  return {
    id: 'doc-1',
    status: 'processed',
    stage: null,
    doc_type: 'memo',
    template_id: 'classic',
    draft: improved,
    improved_text: improved,
    changes: [],
    requisites,
    fact_guard: null,
    is_fallback: false,
    error: null,
  };
}

describe('buildFinalDocumentText', () => {
  it('подставляет изменённую дату вместо даты из черновика', () => {
    const doc = makeDoc(
      [
        {
          key: 'doc_date',
          label: 'Дата документа',
          value: '10.09.2026',
          status: 'user_provided',
          required: true,
        },
      ],
      'Служебная записка\nТекст\n05.09.2025'
    );

    const result = buildFinalDocumentText(doc);

    expect(result).toContain('10.09.2026');
    expect(result.split('\n')).not.toContain('05.09.2025');
  });

  it('оставляет пустой реквизит пометкой [Адресат]', () => {
    const doc = makeDoc(
      [
        {
          key: 'addressee',
          label: 'Адресат',
          value: null,
          status: 'left_blank',
          required: true,
        },
      ],
      'Текст без адресата'
    );

    expect(buildFinalDocumentText(doc)).toContain('[Адресат]');
  });

  it('адресат из панели появляется в итоговом тексте', () => {
    const doc = makeDoc(
      [
        {
          key: 'addressee',
          label: 'Адресат',
          value: 'Директору ООО «Ромашка» Петрову П.П.',
          status: 'user_provided',
          required: true,
        },
      ],
      'Текст без адресата'
    );

    const result = buildFinalDocumentText(doc);

    expect(result).toContain('Директору ООО «Ромашка» Петрову П.П.');
  });

  it('пустой адресат превращается в [Адресат]', () => {
    const doc = makeDoc(
      [
        {
          key: 'addressee',
          label: 'Адресат',
          value: null,
          status: 'left_blank',
          required: true,
        },
      ],
      'Текст без адресата'
    );

    const result = buildFinalDocumentText(doc);

    expect(result).toContain('[Адресат]');
  });

  it('заменяет строку авторства значением пользователя', () => {
    const doc = makeDoc(
      [
        {
          key: 'author',
          label: 'Автор',
          value: 'Петров П.П.',
          status: 'user_provided',
          required: true,
        },
        {
          key: 'position',
          label: 'Должность автора',
          value: 'инженера',
          status: 'user_provided',
          required: true,
        },
      ],
      'от менеджера отдела продаж Иванова И.И.'
    );

    expect(buildFinalDocumentText(doc)).toContain('от инженера Петров П.П.');
  });
});