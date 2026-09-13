import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDocumentStore } from '../../shared/store/documentStore';
import { usePollDocument } from '../../shared/hooks/usePollDocument';
import { Banner } from '../../shared/ui/Banner';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';
import { ProcessingScreen } from './ProcessingScreen';
import { TimeoutScreen } from './TimeoutScreen';
import { FailedScreen } from './FailedScreen';
import { ResultScreen } from './ResultScreen';

export function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const document = useDocumentStore((state) => state.document);
  const pollingTimedOut = useDocumentStore((state) => state.pollingTimedOut);
  const transportError = useDocumentStore((state) => state.transportError);
  const docTypes = useDocumentStore((state) => state.docTypes);
  const fetchDocument = useDocumentStore((state) => state.fetchDocument);
  const loadDocTypes = useDocumentStore((state) => state.loadDocTypes);
  const reprocessDocument = useDocumentStore((state) => state.reprocessDocument);
  const resumePolling = useDocumentStore((state) => state.resumePolling);
  const resetWizard = useDocumentStore((state) => state.resetWizard);

  usePollDocument(id || null);

  useEffect(() => {
    if (!id) return;
    const current = useDocumentStore.getState().document;
    if (!current || current.id !== id) {
      fetchDocument(id);
    }
  }, [id, fetchDocument]);

  useEffect(() => {
    if (docTypes.length === 0) {
      loadDocTypes();
    }
  }, [docTypes.length, loadDocTypes]);

  const handleRetry = () => {
    if (id) {
      reprocessDocument(id);
    }
  };

  const handleNewDocument = () => {
    resetWizard();
    navigate('/wizard');
  };

  if (!document) {
    return (
      <div className="space-y-4">
        {transportError ? (
          <>
            <Banner level="error">{transportError}</Banner>
            <div className="flex gap-3 flex-wrap">
              <PrimaryButton onClick={() => navigate('/wizard')}>
                Создать новый документ
              </PrimaryButton>
              <PrimaryButton
                variant="ghost"
                onClick={() => id && fetchDocument(id)}
              >
                Повторить запрос
              </PrimaryButton>
            </div>
          </>
        ) : (
          <div
            data-testid="document-skeleton"
            aria-label="Загружаю документ"
            className="space-y-4"
          >
            <div
              className="h-6 rounded animate-pulse"
              style={{ background: 'var(--muted)', width: '40%' }}
            />
            <div
              className="h-28 rounded animate-pulse"
              style={{ background: 'var(--muted)' }}
            />
            <div
              className="h-64 rounded animate-pulse"
              style={{ background: 'var(--muted)' }}
            />
            <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
              Загружаю документ…
            </p>
          </div>
        )}
      </div>
    );
  }

  const docTypeName =
    docTypes.find((type) => type.id === document.doc_type)?.name ?? 'Документ';

  const showTimeout = pollingTimedOut && document.status === 'processing';

  return (
    <div>
      {transportError && (
        <div className="mb-4">
          <Banner level="error">{transportError}</Banner>
        </div>
      )}

      <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <h1
          className="text-xl font-bold"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          {docTypeName}
        </h1>
        {document.status !== 'processing' && (
          <PrimaryButton variant="ghost" onClick={handleNewDocument}>
            + Создать ещё документ
          </PrimaryButton>
        )}
      </div>

      {showTimeout ? (
        <TimeoutScreen onContinue={resumePolling} />
      ) : document.status === 'processing' ? (
        <ProcessingScreen document={document} />
      ) : document.status === 'failed' ? (
        <FailedScreen document={document} onRetry={handleRetry} />
      ) : (
        <ResultScreen document={document} />
      )}
    </div>
  );
}