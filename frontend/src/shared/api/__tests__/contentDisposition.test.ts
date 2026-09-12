import { describe, it, expect } from 'vitest';
import { parseContentDisposition } from '../contentDisposition';

describe('parseContentDisposition', () => {
  it('берёт имя из filename="..."', () => {
    expect(
      parseContentDisposition(
        'attachment; filename="sluzhebnaya-zapiska-11-09-2026.docx"',
        'document.docx'
      )
    ).toBe('sluzhebnaya-zapiska-11-09-2026.docx');
  });

  it('берёт имя из filename без кавычек', () => {
    expect(
      parseContentDisposition('attachment; filename=report.docx', 'document.docx')
    ).toBe('report.docx');
  });

  it('декодирует filename*=UTF-8', () => {
    expect(
      parseContentDisposition(
        "attachment; filename*=UTF-8''%D0%94%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82.docx",
        'document.docx'
      )
    ).toBe('Документ.docx');
  });

  it('возвращает fallback при отсутствии заголовка', () => {
    expect(parseContentDisposition(null, 'fallback.docx')).toBe('fallback.docx');
    expect(parseContentDisposition(undefined, 'fallback.docx')).toBe('fallback.docx');
    expect(parseContentDisposition('', 'fallback.docx')).toBe('fallback.docx');
  });
});