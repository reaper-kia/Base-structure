import { Link } from 'react-router-dom';
import type { DocumentState } from '../../shared/api/types';
import { useDocumentStore } from '../../shared/store/documentStore';
import { DegradedBanner } from './DegradedBanner';
import { FactGuardBadge } from './FactGuardBadge';
import { DiffView } from './diff/DiffView';
import './ResultScreen.css';

interface ResultScreenProps {
  document: DocumentState;
}

export function ResultScreen({ document }: ResultScreenProps) {
  const renderDocument = useDocumentStore((state) => state.renderDocument);
  const isRendering = useDocumentStore((state) => state.isRendering);

  const canDownload =
    document.status === 'processed' || document.status === 'degraded';

  return (
    <section className="result-screen">
      <div className="result-screen__top">
        <div>
          <h2 className="result-screen__title">Документ обработан</h2>
          <p className="result-muted">
            Тип: {document.doc_type} · Шаблон: {document.template_id}
          </p>
        </div>

        <button
          type="button"
          className="result-download-button"
          disabled={!canDownload || isRendering}
          onClick={() => renderDocument(document.id)}
        >
          {isRendering ? 'Готовим DOCX...' : 'Скачать DOCX'}
        </button>
      </div>

      {document.status === 'degraded' && <DegradedBanner />}

      <FactGuardBadge factGuard={document.fact_guard} />

      <DiffView
        draft={document.draft}
        improvedText={document.improved_text}
        changes={document.changes}
      />

      <section className="result-card result-card--placeholder">
        <h2 className="result-card__title">Реквизиты</h2>
        <p className="result-muted">
          Панель реквизитов будет отдельным блоком на следующем шаге.
        </p>
      </section>

      <Link className="result-trace-link" to={`/trace/${document.id}`}>
        Смотреть технический trace
      </Link>
    </section>
  );
}