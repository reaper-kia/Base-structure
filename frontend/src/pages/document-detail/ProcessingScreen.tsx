import type { DocumentState } from '../../shared/api/types';
import { StageStepper } from './StageStepper';

interface ProcessingScreenProps {
  document: DocumentState;
}

export function ProcessingScreen({ document }: ProcessingScreenProps) {
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
          className="relative w-16 h-16"
          role="img"
          aria-label="Идёт обработка документа"
        >
          <div
            className="absolute inset-0 rounded-full border-4 border-transparent animate-spin"
            style={{
              borderTopColor: 'var(--primary)',
              borderRightColor: 'var(--accent)',
            }}
          />
          <div
            className="absolute inset-2 rounded-full border-2 border-transparent animate-spin"
            style={{
              borderTopColor: 'var(--accent)',
              animationDirection: 'reverse',
              animationDuration: '0.8s',
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
            Обычно это занимает до минуты. Прогресс обновляется автоматически.
          </div>
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