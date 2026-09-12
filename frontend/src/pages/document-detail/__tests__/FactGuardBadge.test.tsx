import { describe, it, expect } from 'vitest';
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
      screen.getByText(/Проверенные значения: сохранено 2 из 2/)
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

  it('при нуле якорей объясняет, что проверка не выполнялась', () => {
    render(
      <FactGuardBadge
        factGuard={{
          verdict: 'clean',
          preserved: [],
          lost: [],
          added: [],
          source_count: 0,
          preserved_count: 0,
        }}
      />
    );

    expect(
      screen.getByText(/Проверенные значения: проверка не выполнялась/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/сохранено 0 из 0/i)).not.toBeInTheDocument();
  });
});