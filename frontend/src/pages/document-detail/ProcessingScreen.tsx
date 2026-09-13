import { useEffect } from 'react';
import type { DocumentState } from '../../shared/api/types';
import { useDocumentStore } from '../../shared/store/documentStore';
import { StageStepper } from './StageStepper';

const STAGE_LABELS: Record<string, string> = {
  llm: 'Исправление орфографии и стиля…',
  fact_guard: 'Проверка сохранности фактов…',
  validation: 'Проверка реквизитов…',
};

interface ProcessingScreenProps {
  document: DocumentState;
}

export function ProcessingScreen({ document }: ProcessingScreenProps) {
  const devState = useDocumentStore((state) => state.devState);
  const loadDevState = useDocumentStore((state) => state.loadDevState);

  useEffect(() => {
    if (!devState) {
      loadDevState();
    }
  }, [devState, loadDevState]);

  const etaSeconds = devState?.eta_seconds ?? null;
  const stageIndex =
    document.stage === 'llm' ? 0 : document.stage === 'fact_guard' ? 1 : 2;
  const progress = Math.min(100, (stageIndex + 1) * 28);

  return (
    <section
      className="p-6 md:p-8"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="flex flex-col items-center gap-6 py-4">
        <div
          className="relative w-20 h-20 flex items-center justify-center"
          role="img"
          aria-label="Идёт обработка документа"
        >
          <div
            className="absolute inset-0 rounded-full anim-pulse-ring"
            style={{ background: 'var(--primary)', opacity: 0.15 }}
          />
          <div
            className="absolute inset-2 rounded-full anim-pulse-ring"
            style={{ background: 'var(--primary)', opacity: 0.1, animationDelay: '0.5s' }}
          />
          <div
            className="relative w-14 h-14 rounded-full border-4 border-transparent animate-spin"
            style={{ borderTopColor: 'var(--primary)', borderRightColor: 'var(--accent)' }}
          />
          <div
            className="absolute inset-5 rounded-full border-2 border-transparent animate-spin"
            style={{
              borderTopColor: 'var(--accent)',
              animationDirection: 'reverse',
              animationDuration: '0.7s',
            }}
          />
        </div>

        <div className="text-center">
          <div
            className="font-semibold mb-1"
            style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
          >
            ИИ обрабатывает черновик
          </div>
          <div className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
            {STAGE_LABELS[document.stage ?? ''] ?? 'Подготовка документа…'}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--muted-foreground)' }}>
            {etaSeconds
              ? `Обычно занимает около ${etaSeconds} секунд.`
              : 'Обычно занимает до минуты.'}{' '}
            Прогресс обновляется автоматически.
          </div>
        </div>

        <div
          className="w-64 h-1.5 rounded-full overflow-hidden"
          style={{ background: 'var(--secondary)' }}
        >
          <div
            className="h-full rounded-full transition-all duration-700 anim-shimmer"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="w-full max-w-sm">
          <StageStepper currentStage={document.stage} />
        </div>

        <details className="w-full max-w-sm">
          <summary
            className="cursor-pointer text-xs text-center"
            style={{ color: 'var(--muted-foreground)' }}
          >
            Показать черновик
          </summary>
          <pre
            className="mt-2 p-3 text-left"
            style={{
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
              wordBreak: 'break-word',
              background: 'var(--muted)',
              borderRadius: 'var(--radius)',
              maxHeight: 300,
              overflowY: 'auto',
              fontSize: '0.75rem',
            }}
          >
            {document.draft}
          </pre>
        </details>
      </div>
    </section>
  );
}