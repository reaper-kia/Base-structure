import type { CSSProperties } from 'react';
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

  const before =
    segment.before && segment.before.length > 0 ? segment.before : '—';
  const after = segment.after && segment.after.length > 0 ? segment.after : '—';

  return `Было: ${before}\nСтало: ${after}`;
}

function segmentStyle(segment: DiffSegment): CSSProperties {
  if (segment.kind === 'equal') return {};

  return {
    background: `var(--diff-${segment.changeType})`,
    borderRadius: 3,
    padding: '1px 2px',
    cursor: 'help',
    textDecoration: segment.kind === 'delete' ? 'line-through' : 'none',
  };
}

interface PaneProps {
  title: string;
  label: string;
  segments: DiffSegment[];
}

function Pane({ title, label, segments }: PaneProps) {
  return (
    <div
      className="min-w-0 flex flex-col"
      style={{
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        background: 'var(--card)',
      }}
    >
      <div
        className="px-3 py-2 text-xs font-semibold uppercase tracking-wider border-b flex-shrink-0"
        style={{
          color: 'var(--muted-foreground)',
          borderColor: 'var(--border)',
          letterSpacing: '0.1em',
        }}
      >
        {title}
      </div>
      <div
        className="p-3 flex-1 overflow-auto"
        aria-label={label}
        style={{
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem',
          lineHeight: 1.7,
          maxHeight: 560,
          minHeight: 220,
        }}
      >
        {segments.map((segment) => (
          <span
            key={segment.id}
            style={segmentStyle(segment)}
            title={getTooltip(segment)}
            data-change-type={segment.changeType}
            data-diff-kind={segment.kind}
          >
            {segment.text}
          </span>
        ))}
      </div>
    </div>
  );
}

export function DiffView({ draft, improvedText, changes }: DiffViewProps) {
  if (improvedText === null) {
    return (
      <section
        className="p-4"
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
        }}
      >
        <div className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          Результат обработки ещё не готов.
        </div>
      </section>
    );
  }

  const diff = buildDiff(draft, improvedText, changes);

  return (
    <section
      className="p-4 md:p-5"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="mb-3">
        <h2
          className="text-lg font-bold"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          Что изменила система
        </h2>
        <p className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
          Слева исходный черновик, справа — улучшенный документ. Наведите на
          подсветку, чтобы увидеть «было → стало».
        </p>
      </div>

      <DiffLegend />

      <div className="diff-view grid md:grid-cols-2 gap-3" data-testid="diff-view">
        <Pane title="Черновик" label="Исходный черновик" segments={diff.left} />
        <Pane title="Результат" label="Улучшенный документ" segments={diff.right} />
      </div>
    </section>
  );
}