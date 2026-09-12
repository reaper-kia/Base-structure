const LEGEND_ITEMS = [
  { type: 'spelling', label: 'Орфография', color: 'var(--diff-spelling)' },
  { type: 'punctuation', label: 'Пунктуация', color: 'var(--diff-punctuation)' },
  { type: 'style', label: 'Деловой стиль', color: 'var(--diff-style)' },
  { type: 'structure', label: 'Структура', color: 'var(--diff-structure)' },
  { type: 'neutral', label: 'Неподтверждённое изменение', color: 'var(--diff-neutral)' },
] as const;

export function DiffLegend() {
  return (
    <div
      className="flex flex-wrap gap-2 mb-3"
      aria-label="Легенда типов правок"
    >
      {LEGEND_ITEMS.map((item) => (
        <span
          key={item.type}
          className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1"
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--muted-foreground)',
          }}
        >
          <span
            className="w-3 h-3 rounded-sm"
            style={{ background: item.color }}
            aria-hidden="true"
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}