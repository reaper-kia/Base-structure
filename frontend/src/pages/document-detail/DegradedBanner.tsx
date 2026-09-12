export function DegradedBanner() {
  return (
    <div
      className="px-4 py-3 text-sm flex items-start gap-2"
      role="status"
      style={{
        background: '#fef3c7',
        border: '1px solid #fde68a',
        borderRadius: 'var(--radius)',
        color: '#92400e',
      }}
    >
      <span className="flex-shrink-0">⚠️</span>
      <span>Обработано в резервном режиме: ИИ-компонент был недоступен.</span>
    </div>
  );
}