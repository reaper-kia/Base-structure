import { Link } from 'react-router-dom';
import type { DocumentState } from '../../shared/api/types';
import { useDocumentStore } from '../../shared/store/documentStore';
import { SectionHeader } from '../../shared/ui/SectionHeader';
import { DegradedBanner } from './DegradedBanner';
import { FactGuardBadge } from './FactGuardBadge';
import { DiffView } from './diff/DiffView';
import { RequisitesPanel } from './RequisitesPanel';
import { Banner } from '../../shared/ui/Banner';

interface ResultScreenProps {
  document: DocumentState;
}

export function ResultScreen({ document }: ResultScreenProps) {
  const renderDocument = useDocumentStore((state) => state.renderDocument);
  const patchRequisites = useDocumentStore((state) => state.patchRequisites);
  const isRendering = useDocumentStore((state) => state.isRendering);
  const renderFallback = useDocumentStore((state) => state.renderFallback);
  const isPatchingRequisites = useDocumentStore(
    (state) => state.isPatchingRequisites
  );

  const canDownload =
    document.status === 'processed' || document.status === 'degraded';

  return (
    <div className="space-y-4">
      <SectionHeader
        step={3}
        title="Документ обработан"
        hint="Проверьте, что изменил ИИ, уточните реквизиты и скачайте готовый файл"
      />

      {document.status === 'degraded' && <DegradedBanner />}

      {renderFallback && <Banner level="info">{renderFallback}</Banner>}

      {document.fact_guard && document.fact_guard.verdict !== 'clean' && (
        <Banner level="warning">
          Fact Guard не подтвердил сохранность всех фактов — проверьте текст
          глазами.
        </Banner>
      )}

      <FactGuardBadge factGuard={document.fact_guard} />

      <DiffView
        draft={document.draft}
        improvedText={document.improved_text}
        changes={document.changes}
      />

      <RequisitesPanel
        requisites={document.requisites}
        onPatch={patchRequisites}
        isPatching={isPatchingRequisites}
      />

      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link
          className="text-xs underline"
          style={{ color: 'var(--muted-foreground)' }}
          to={`/trace/${document.id}`}
        >
          Смотреть технический trace
        </Link>
        <button
          type="button"
          disabled={!canDownload || isRendering}
          onClick={() => renderDocument(document.id)}
          className="flex items-center gap-2.5 px-8 py-3 font-semibold text-sm transition-all"
          style={{
            background:
              !canDownload || isRendering ? 'var(--muted)' : 'var(--accent)',
            color:
              !canDownload || isRendering ? 'var(--muted-foreground)' : '#fff',
            borderRadius: 'var(--radius)',
            cursor: !canDownload || isRendering ? 'not-allowed' : 'pointer',
            letterSpacing: '0.04em',
          }}
        >
          {isRendering ? 'Формируется DOCX…' : '⬇ Скачать DOCX'}
        </button>
      </div>
    </div>
  );
}