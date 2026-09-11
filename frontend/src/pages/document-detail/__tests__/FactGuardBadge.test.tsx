import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FactGuardBadge } from '../FactGuardBadge';

describe('FactGuardBadge', () => {
  it('показывает корректные числа', () => {
    render(
      <FactGuardBadge
        factGuard={{
          verdict: 'clean',
          preserved: ['10 июня 2025', '14 календарных дней'],
          lost: [],
          added: [],
          source_count: 2,
          preserved_count: 2,
        }}
      />
    );

    expect(
      screen.getByText('Fact Guard: Сохранено 2 из 2 фактов · Добавлено 0')
    ).toBeInTheDocument();
  });

  it('при warning показывает список потерянных фактов', () => {
    render(
      <FactGuardBadge
        factGuard={{
          verdict: 'warning',
          preserved: ['10 июня 2025'],
          lost: ['50 000 руб.'],
          added: [],
          source_count: 2,
          preserved_count: 1,
        }}
      />
    );

    expect(screen.getByText('Из текста пропало: 50 000 руб.')).toBeInTheDocument();
  });
});