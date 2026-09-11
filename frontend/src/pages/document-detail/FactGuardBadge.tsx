import type { FactGuard } from '../../shared/api/types';

interface FactGuardBadgeProps {
  factGuard: FactGuard | null;
}

export function FactGuardBadge({ factGuard }: FactGuardBadgeProps) {
  if (!factGuard) return null;

  const addedCount = factGuard.added.length;

  return (
    <section
      className={`fact-guard fact-guard--${factGuard.verdict}`}
      aria-label="Fact Guard"
    >
      <div className="fact-guard__main">
        Fact Guard: Сохранено {factGuard.preserved_count} из{' '}
        {factGuard.source_count} фактов · Добавлено {addedCount}
      </div>

      {factGuard.verdict === 'warning' && factGuard.lost.length > 0 && (
        <div className="fact-guard__warning">
          Из текста пропало: {factGuard.lost.join(', ')}
        </div>
      )}

      {factGuard.verdict === 'blocked' && (
        <div className="fact-guard__warning">
          Обнаружены факты, которых не было в исходном черновике.
        </div>
      )}
    </section>
  );
}