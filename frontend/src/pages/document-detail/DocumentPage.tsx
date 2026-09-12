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
          <p style={{ color: 'var(--muted-foreground)' }}>Загрузка документа…</p>
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

      <h1
        className="text-xl font-bold mb-4"
        style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
      >
        {docTypeName}
      </h1>

      {showTimeout ? (
        <TimeoutScreen onRetry={handleRetry} />
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