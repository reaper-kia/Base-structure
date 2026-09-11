import type { ChangeItem } from '../../../shared/api/types';
import { buildDiff, type DiffSegment } from './buildDiff';
import { DiffLegend } from './DiffLegend';

interface DiffViewProps {
  draft: string;
  improvedText: string | null;
  changes: ChangeItem[];
}

function getTooltip(segment: DiffSegment): string | undefined {
  if (segment.kind === 'equal') return undefined;

  const before = segment.before && segment.before.length > 0 ? segment.before : '—';
  const after = segment.after && segment.after.length > 0 ? segment.after : '—';

  return `Было: ${before}\nСтало: ${after}`;
}

function renderSegment(segment: DiffSegment) {
  const className =
    segment.kind === 'equal'
      ? 'diff-token'
      : `diff-token diff-token--changed diff-token--${segment.kind} diff-token--${segment.changeType}`;

  return (
    <span
      key={segment.id}
      className={className}
      title={getTooltip(segment)}
      data-change-type={segment.changeType}
      data-diff-kind={segment.kind}
    >
      {segment.text}
    </span>
  );
}

export function DiffView({ draft, improvedText, changes }: DiffViewProps) {
  if (improvedText === null) {
    return (
      <section className="result-card">
        <h2 className="result-card__title">Что изменила система</h2>
        <p className="result-muted">Результат обработки ещё не готов.</p>
      </section>
    );
  }

  const diff = buildDiff(draft, improvedText, changes);

  return (
    <section className="result-card">
      <div className="result-card__header">
        <div>
          <h2 className="result-card__title">Что изменила система</h2>
          <p className="result-muted">
            Слева исходный черновик, справа — улучшенный документ.
            Наведите на подсветку, чтобы увидеть «было → стало».
          </p>
        </div>
      </div>

      <DiffLegend />

      <div className="diff-view" data-testid="diff-view">
        <div className="diff-pane">
          <h3 className="diff-pane__title">Черновик</h3>
          <div className="diff-pane__body" aria-label="Исходный черновик">
            {diff.left.map(renderSegment)}
          </div>
        </div>

        <div className="diff-pane">
          <h3 className="diff-pane__title">Результат</h3>
          <div className="diff-pane__body" aria-label="Улучшенный документ">
            {diff.right.map(renderSegment)}
          </div>
        </div>
      </div>
    </section>
  );
}