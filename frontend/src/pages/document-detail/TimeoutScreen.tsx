import { PrimaryButton } from '../../shared/ui/PrimaryButton';

interface TimeoutScreenProps {
  onRetry: () => void;
}

export function TimeoutScreen({ onRetry }: TimeoutScreenProps) {
  return (
    <section className="flex flex-col items-center justify-center py-16 text-center gap-6">
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
        style={{ background: '#fee2e2', border: '2px solid #fca5a5' }}
      >
        ⏱
      </div>
      <div>
        <div
          className="text-lg font-semibold mb-2"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          Обработка заняла слишком много времени
        </div>
        <div className="text-sm max-w-md" style={{ color: 'var(--muted-foreground)' }}>
          Мы ждали две минуты, но документ ещё не готов. Попробуйте повторить
          обработку.
        </div>
      </div>
      <PrimaryButton onClick={onRetry}>Повторить</PrimaryButton>
    </section>
  );
}