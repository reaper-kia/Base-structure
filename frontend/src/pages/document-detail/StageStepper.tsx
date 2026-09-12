import type { ProcessingStage } from '../../shared/api/types';

const STAGES: { key: ProcessingStage; label: string }[] = [
  { key: 'llm', label: 'Обрабатываем текст' },
  { key: 'fact_guard', label: 'Проверяем факты' },
  { key: 'validation', label: 'Проверяем реквизиты' },
];

interface StageStepperProps {
  currentStage: ProcessingStage | null;
}

export function StageStepper({ currentStage }: StageStepperProps) {
  const currentIndex = currentStage
    ? STAGES.findIndex((stage) => stage.key === currentStage)
    : -1;

  return (
    <ol className="list-none p-0 m-0 flex flex-col gap-3">
      {STAGES.map((stage, index) => {
        const isDone = index < currentIndex;
        const isActive = index === currentIndex;
        const isPending = index > currentIndex;
        const status = isDone ? 'done' : isActive ? 'active' : 'pending';

        return (
          <li
            key={stage.key}
            data-testid={`stage-${stage.key}`}
            data-status={status}
            className="flex items-center gap-3"
          >
            <span
              aria-hidden="true"
              className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0 transition-all"
              style={{
                background: isDone
                  ? '#22c55e'
                  : isActive
                    ? 'var(--accent)'
                    : 'var(--secondary)',
                color: isPending ? 'var(--muted-foreground)' : '#fff',
              }}
            >
              {isDone ? '✓' : index + 1}
            </span>
            <span
              className="text-sm font-medium"
              style={{
                color: isPending ? 'var(--muted-foreground)' : 'var(--foreground)',
              }}
            >
              {stage.label}
              {isActive && (
                <span
                  className="ml-2 text-xs font-semibold"
                  style={{ color: 'var(--accent)' }}
                >
                  выполняется…
                </span>
              )}
            </span>
          </li>
        );
      })}
    </ol>
  );
}