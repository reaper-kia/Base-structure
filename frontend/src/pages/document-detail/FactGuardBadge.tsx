import type { FactGuard } from '../../shared/api/types';

const VERDICT_STYLES = {
  clean: { bg: '#d1fae5', border: '#a7f3d0', color: '#065f46' },
  warning: { bg: '#fef3c7', border: '#fde68a', color: '#92400e' },
  blocked: { bg: '#fee2e2', border: '#fca5a5', color: '#7f1d1d' },
} as const;

interface FactGuardBadgeProps {
  factGuard: FactGuard | null;
}

export function FactGuardBadge({ factGuard }: FactGuardBadgeProps) {
  if (!factGuard) return null;

  const style = VERDICT_STYLES[factGuard.verdict];

  return (
    <section
      className="p-3 md:p-4"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: 'var(--radius)',
        color: style.color,
      }}
      aria-label="Fact Guard"
    >
      <div className="text-sm font-semibold">
        Fact Guard: Сохранено {factGuard.preserved_count} из{' '}
        {factGuard.source_count} фактов · Добавлено {factGuard.added.length}
      </div>

      {factGuard.verdict === 'warning' && factGuard.lost.length > 0 && (
        <div className="text-xs mt-1">
          Из текста пропало: {factGuard.lost.join(', ')}
        </div>
      )}

      {factGuard.verdict === 'blocked' && (
        <div className="text-xs mt-1">
          Обнаружены факты, которых не было в исходном черновике.
        </div>
      )}
    </section>
  );
}