const LEGEND_ITEMS = [
  { type: 'spelling', label: 'Орфография' },
  { type: 'punctuation', label: 'Пунктуация' },
  { type: 'style', label: 'Деловой стиль' },
  { type: 'structure', label: 'Структура' },
] as const;

export function DiffLegend() {
  return (
    <div className="diff-legend" aria-label="Легенда типов правок">
      {LEGEND_ITEMS.map((item) => (
        <span key={item.type} className="diff-legend__item">
          <span
            className={`diff-legend__marker diff-token--${item.type}`}
            aria-hidden="true"
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}