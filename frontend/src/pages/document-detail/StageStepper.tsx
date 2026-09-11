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
    ? STAGES.findIndex((s) => s.key === currentStage)
    : -1;

  return (
    <ol
      style={{
        listStyle: 'none',
        padding: 0,
        margin: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
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
            style={{ display: 'flex', alignItems: 'center', gap: '12px' }}
          >
            <span
              aria-hidden="true"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: 600,
                backgroundColor: isDone
                  ? '#28a745'
                  : isActive
                    ? '#007bff'
                    : '#e9ecef',
                color: isDone || isActive ? 'white' : '#999',
                flexShrink: 0,
              }}
            >
              {isDone ? '✓' : index + 1}
            </span>
            <span
              style={{
                fontSize: '16px',
                color: isPending ? '#999' : isActive ? '#007bff' : '#212529',
                fontWeight: isActive ? 600 : 400,
              }}
            >
              {stage.label}
              {isActive && <span style={{ marginLeft: '8px' }}>…</span>}
            </span>
          </li>
        );
      })}
    </ol>
  );
}