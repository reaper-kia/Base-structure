import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDocumentStore } from '../../shared/store/documentStore';
import { usePollDocument } from '../../shared/hooks/usePollDocument';
import { ProcessingScreen } from './ProcessingScreen';
import { TimeoutScreen } from './TimeoutScreen';
import { ResultScreen } from './ResultScreen';

export function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const document = useDocumentStore((state) => state.document);
  const pollingTimedOut = useDocumentStore((state) => state.pollingTimedOut);
  const fetchDocument = useDocumentStore((state) => state.fetchDocument);
  const reprocessDocument = useDocumentStore((state) => state.reprocessDocument);

  usePollDocument(id || null);

  // Восстанавливаем состояние по document.id при монтировании или смене id
  useEffect(() => {
    if (!id) return;
    const current = useDocumentStore.getState().document;
    if (!current || current.id !== id) {
      fetchDocument(id);
    }
  }, [id, fetchDocument]);

  const handleRetry = () => {
    if (id) {
      reprocessDocument(id);
    }
  };

  if (!document) {
    return (
      <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <p>Загрузка документа...</p>
      </div>
    );
  }

  const showTimeout = pollingTimedOut && document.status === 'processing';

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>
        Документ: {document.doc_type}
      </h1>

      {showTimeout ? (
        <TimeoutScreen onRetry={handleRetry} />
      ) : document.status === 'processing' ? (
        <ProcessingScreen document={document} />
      ) : document.status === 'failed' ? (
        <section style={{ padding: '24px 0' }}>
          <h2>Не удалось обработать документ</h2>
          {document.error && <p>{document.error.message}</p>}
          <button
            type="button"
            onClick={handleRetry}
            style={{
              padding: '12px 24px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
          >
            Повторить
          </button>
        </section>
            ) : (
        <ResultScreen document={document} />
      )}
    </div>
  );
}