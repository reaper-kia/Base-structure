export function DegradedBanner() {
  return (
    <div
      className="px-4 py-3 text-sm flex items-start gap-2"
      role="status"
      style={{
        background: 'var(--banner-warn-bg)',
        border: '1px solid var(--banner-warn-border)',
        borderRadius: 'var(--radius)',
        color: 'var(--banner-warn-text)',
      }}
    >
      <span className="flex-shrink-0">⚠️</span>
      <span>Обработано в резервном режиме: ИИ-компонент был недоступен.</span>
    </div>
  );
}