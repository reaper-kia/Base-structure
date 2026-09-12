import { PrimaryButton } from '../../shared/ui/PrimaryButton';

interface TimeoutScreenProps {
  onContinue: () => void;
}

export function TimeoutScreen({ onContinue }: TimeoutScreenProps) {
  return (
    <section className="flex flex-col items-center gap-6 py-10 text-center">
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold"
        style={{
          background: 'var(--banner-warn-bg)',
          border: '2px solid var(--banner-warn-border)',
          color: 'var(--banner-warn-text)',
        }}
        aria-hidden="true"
      >
        ⏱
      </div>

      <div>
        <h2
          className="text-lg font-semibold mb-2"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          Обработка занимает больше времени, чем обычно
        </h2>
        <p className="text-sm max-w-md" style={{ color: 'var(--muted-foreground)' }}>
          Документ всё ещё обрабатывается на сервере — данные не потеряны.
          Можно продолжить ждать: мы снова начнём опрашивать статус.
        </p>
      </div>

      <PrimaryButton onClick={onContinue}>Продолжить ждать</PrimaryButton>
    </section>
  );
}