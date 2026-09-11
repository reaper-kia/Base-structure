import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocumentStore } from '../../shared/store/documentStore';
import { usePollDocument } from '../../shared/hooks/usePollDocument';
import { DraftInput } from './DraftInput';
import { DocTypeSelector } from './DocTypeSelector';
import { TemplateSelector } from './TemplateSelector';

export function WizardPage() {
  const navigate = useNavigate();
  const {
    draft,
    docType,
    templateId,
    document,
    isCreating,
    transportError,
    loadDocTypes,
    loadTemplates,
    createDocument,
  } = useDocumentStore();

  usePollDocument(document?.id || null);

  useEffect(() => {
    loadDocTypes();
    loadTemplates();
  }, [loadDocTypes, loadTemplates]);

  // Если документ создан и обрабатывается — переходим на страницу документа
  useEffect(() => {
    if (document && document.status === 'processing') {
      navigate(`/documents/${document.id}`);
    }
  }, [document, navigate]);

  const trimmedLength = draft.trim().length;
  const isOverLimit = draft.length > 20000;
  const canCreate =
    trimmedLength > 0 &&
    !isOverLimit &&
    docType !== null &&
    templateId !== null &&
    !isCreating;

  const getDisabledReason = (): string | null => {
    if (isCreating) return 'Создание документа...';
    if (isOverLimit) return 'Текст превышает 20000 символов';
    if (trimmedLength === 0) return 'Введите текст документа';
    if (!docType) return 'Выберите тип документа';
    if (!templateId) return 'Выберите шаблон оформления';
    return null;
  };

  const disabledReason = getDisabledReason();

  return (
    <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', marginBottom: '24px' }}>
        Создание документа
      </h1>

      {transportError && (
        <div
          role="alert"
          style={{
            padding: '12px 16px',
            backgroundColor: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '14px',
          }}
        >
          {transportError}
        </div>
      )}

      <DraftInput />
      <DocTypeSelector />
      <TemplateSelector />

      {/* Кнопка создания */}
      <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button
          type="button"
          onClick={createDocument}
          disabled={!canCreate}
          aria-label={disabledReason || 'Создать документ'}
          style={{
            padding: '14px 32px',
            fontSize: '16px',
            fontWeight: 600,
            backgroundColor: canCreate ? '#007bff' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: canCreate ? 'pointer' : 'not-allowed',
            alignSelf: 'flex-start',
            transition: 'background-color 0.15s',
          }}
        >
          {isCreating ? 'Создание...' : 'Создать документ'}
        </button>

        {disabledReason && !isCreating && (
          <span style={{ fontSize: '13px', color: '#999' }}>
            {disabledReason}
          </span>
        )}
      </div>
    </div>
  );
}