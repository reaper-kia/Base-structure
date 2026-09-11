import type { DocumentState } from '../../shared/api/types';
import { StageStepper } from './StageStepper';

interface ProcessingScreenProps {
  document: DocumentState;
}

export function ProcessingScreen({ document }: ProcessingScreenProps) {
  return (
    <section style={{ padding: '24px 0' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: '22px' }}>
        Обрабатываем документ
      </h2>
      <p style={{ margin: '0 0 24px 0', color: '#666', fontSize: '14px' }}>
        Обычно это занимает до минуты. Прогресс обновляется автоматически —
        вы можете оставаться на странице.
      </p>

      <StageStepper currentStage={document.stage} />

      <details style={{ marginTop: '32px' }}>
        <summary
          style={{ cursor: 'pointer', fontSize: '14px', color: '#007bff' }}
        >
          Показать черновик
        </summary>
        <pre
          style={{
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            wordBreak: 'break-word',
            padding: '12px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            maxHeight: '300px',
            overflowY: 'auto',
            fontSize: '13px',
            marginTop: '8px',
          }}
        >
          {document.draft}
        </pre>
      </details>
    </section>
  );
}