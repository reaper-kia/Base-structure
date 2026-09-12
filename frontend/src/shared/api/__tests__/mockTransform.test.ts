import { describe, expect, it } from 'vitest';
import { buildChanges, buildImprovedText, extractRequisites } from '../mock';

const ERRORS_DRAFT =
  'Директору ООО Ромашка Петрову П.П.\nот менеджера Иванова И.И.\n\nзаявленее\n\nпрошу предоставить мне отпуск с 10 июня 2025 на 14 дней а то я уже задолбался работать без отдыха и хочу отдохнуть\n\nИванов';

const REPORT_DRAFT =
  'Директору ООО «Ромашка» Петрову П.П.\nот главного бухгалтера Сидоровой А.В.\n\nДокладная записка\nО перерасчёте заработной платы\n\nДовожу до Вашего сведения, что при начислении заработной платы за август 2025 года была допущена ошибка.\n\nГлавный бухгалтер\nСидорова А.В.\n05.09.2025';

describe('mock transformations', () => {
  it('исправляет ошибки и вставляет шапку выбранного типа', () => {
    const improved = buildImprovedText(ERRORS_DRAFT, 'memo');
    const changes = buildChanges(ERRORS_DRAFT, improved, 'memo');

    expect(improved).toContain('заявление');
    expect(improved).not.toContain('задолбался');
    expect(improved).toContain('Служебная записка');
    expect(changes.some((change) => change.type === 'spelling')).toBe(true);
    expect(changes.some((change) => change.type === 'structure')).toBe(true);
  });

  it('не меняет чистый черновик с шапкой', () => {
    const clean =
      'Служебная записка\nО предоставлении отпуска\n\nПрошу предоставить мне ежегодный оплачиваемый отпуск с 10 июня 2025 года на 14 календарных дней.';

    expect(buildImprovedText(clean, 'memo')).toBe(clean);
    expect(buildChanges(clean, clean, 'memo')).toHaveLength(0);
  });

  it('извлекает реквизиты из черновика, а не из зашитого сценария', () => {
    const requisites = extractRequisites(REPORT_DRAFT, 'report');
    const byKey = new Map(requisites.map((req) => [req.key, req]));

    expect(byKey.get('addressee')?.value).toBe(
      'Директору ООО «Ромашка» Петрову П.П.'
    );
    expect(byKey.get('author')?.value).toBe('Сидорова А.В.');
    expect(byKey.get('position')?.value).toBe('Главный бухгалтер');
    expect(byKey.get('subject')?.value).toBe('О перерасчёте заработной платы');
    expect(byKey.get('doc_date')?.value).toBe('05.09.2025');
    expect(byKey.get('doc_date')?.status).toBe('found_in_draft');
  });

  it('помечает дату системой, если её нет в черновике', () => {
    const requisites = extractRequisites(ERRORS_DRAFT, 'memo');
    const byKey = new Map(requisites.map((req) => [req.key, req]));

    expect(byKey.get('doc_date')?.status).toBe('auto_filled');
  });
});