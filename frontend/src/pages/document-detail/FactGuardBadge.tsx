import type { FactGuard } from '../../shared/api/types';

interface FactGuardBadgeProps {
  factGuard: FactGuard | null;
}

export function FactGuardBadge({ factGuard }: FactGuardBadgeProps) {
  if (!factGuard) {
    return null;
  }

  const total = factGuard.source_count;

  if (total === 0) {
    return (
      <section
        aria-label="Fact Guard"
        className="p-3 md:p-4"
        style={{
          background: 'var(--muted)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
        }}
      >
        <div className="flex items-start gap-2">
          <span aria-hidden="true" className="flex-shrink-0 text-base">
            —
          </span>
          <div>
            <div
              className="text-sm font-semibold"
              style={{ color: 'var(--foreground)' }}
            >
              Проверенные значения: проверка не выполнялась
            </div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
              В тексте не найдено дат, сумм и других проверяемых фактов.
            </div>
          </div>
        </div>
      </section>
    );
  }

  const lost = factGuard.lost;
  const isSuccess = lost.length === 0;

  return (
    <section
      aria-label="Fact Guard"
      className="p-3 md:p-4"
      style={{
        background: isSuccess ? 'var(--chip-found-bg)' : 'var(--chip-missing-bg)',
        border: `1px solid ${
          isSuccess ? 'var(--chip-found-border)' : 'var(--chip-missing-border)'
        }`,
        borderRadius: 'var(--radius)',
        color: isSuccess ? 'var(--chip-found-text)' : 'var(--chip-missing-text)',
      }}
    >
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="flex-shrink-0 text-base font-bold">
          {isSuccess ? '✓' : '⚠'}
        </span>
        <div>
          <div className="text-sm font-semibold">
            Проверенные значения: сохранено {factGuard.preserved_count} из {total}
            {lost.length > 0 && ` · потеряно ${lost.length}`}
          </div>
          {lost.length > 0 && (
            <div className="text-xs mt-1">Из текста пропало: {lost.join(', ')}</div>
          )}
        </div>
      </div>
    </section>
  );
}