import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocumentStore } from '../../shared/store/documentStore';
import { usePollDocument } from '../../shared/hooks/usePollDocument';
import { DraftInput } from './DraftInput';
import { DocTypeSelector } from './DocTypeSelector';
import { TemplateSelector } from './TemplateSelector';
import { SectionHeader } from '../../shared/ui/SectionHeader';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';

export function WizardPage() {
  const navigate = useNavigate();
  const draft = useDocumentStore((state) => state.draft);
  const docType = useDocumentStore((state) => state.docType);
  const templateId = useDocumentStore((state) => state.templateId);
  const document = useDocumentStore((state) => state.document);
  const isCreating = useDocumentStore((state) => state.isCreating);
  const transportError = useDocumentStore((state) => state.transportError);
  const loadDocTypes = useDocumentStore((state) => state.loadDocTypes);
  const loadTemplates = useDocumentStore((state) => state.loadTemplates);
  const createDocument = useDocumentStore((state) => state.createDocument);

  usePollDocument(document?.id ?? null);

  useEffect(() => {
    loadDocTypes();
    loadTemplates();
  }, [loadDocTypes, loadTemplates]);

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
    if (isCreating) return 'Создание документа…';
    if (isOverLimit) return 'Текст превышает 20000 символов';
    if (trimmedLength === 0) return 'Введите текст документа';
    if (!docType) return 'Выберите тип документа';
    if (!templateId) return 'Выберите шаблон оформления';
    return null;
  };

  const disabledReason = getDisabledReason();

  return (
    <div>
      {transportError && (
        <div
          role="alert"
          className="mb-4 px-4 py-3 text-sm"
          style={{
            background: 'var(--banner-error-bg)',
            border: '1px solid var(--banner-error-border)',
            borderRadius: 'var(--radius)',
            color: 'var(--banner-error-text)',
          }}
        >
          {transportError}
        </div>
      )}

      <SectionHeader
        step={1}
        title="Введите черновик"
        hint="Напишите или вставьте текст — ИИ исправит ошибки и приведёт к деловому стилю"
      />
      <DraftInput />

      <div className="mt-10">
        <SectionHeader
          step={2}
          title="Тип документа и шаблон"
          hint="Тип определяет структуру и реквизиты; шаблон — оформление итогового файла"
        />
        <DocTypeSelector />
        <TemplateSelector />
      </div>

      <div className="mt-6 flex items-center justify-end gap-4 flex-wrap">
        {disabledReason && !isCreating && (
          <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
            {disabledReason}
          </span>
        )}
        <PrimaryButton disabled={!canCreate} onClick={createDocument}>
          {isCreating ? 'Создание…' : 'Создать документ →'}
        </PrimaryButton>
      </div>
    </div>
  );
}