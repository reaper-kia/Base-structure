import { describe, expect, it } from 'vitest';
import { buildChanges, buildImprovedText } from '../mock';

describe('mock transformations', () => {
  it('исправляет ошибки и отдаёт правки для диффа', () => {
    const draft =
      'заявленее прошу предоставить отпуск с 10 июня 2025 на 14 дней а то я уже задолбался работать без отдыха и хочу отдохнуть';

    const improved = buildImprovedText(draft);
    const changes = buildChanges(draft, improved);

    expect(improved).toContain('заявление');
    expect(improved).not.toContain('задолбался');
    expect(changes.some((change) => change.type === 'spelling')).toBe(true);
    expect(changes.some((change) => change.type === 'style')).toBe(true);
  });

  it('не меняет чистый черновик', () => {
    const draft =
      'Служебная записка\nО предоставлении отпуска\n\nПрошу предоставить мне ежегодный оплачиваемый отпуск с 10 июня 2025 года на 14 календарных дней.';

    expect(buildImprovedText(draft)).toBe(draft);
    expect(buildChanges(draft, buildImprovedText(draft))).toHaveLength(0);
  });
});