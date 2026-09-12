import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Banner } from '../../shared/ui/Banner';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';
import { useDocumentStore } from '../../shared/store/documentStore';
import { DraftInput } from './DraftInput';
import { DocTypeSelector } from './DocTypeSelector';
import { TemplateSelector } from './TemplateSelector';

export function WizardPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState<1 | 2>(1);

  const draft = useDocumentStore((state) => state.draft);
  const docType = useDocumentStore((state) => state.docType);
  const templateId = useDocumentStore((state) => state.templateId);
  const docTypes = useDocumentStore((state) => state.docTypes);
  const templates = useDocumentStore((state) => state.templates);
  const loadDocTypes = useDocumentStore((state) => state.loadDocTypes);
  const loadTemplates = useDocumentStore((state) => state.loadTemplates);
  const createDocument = useDocumentStore((state) => state.createDocument);
  const isCreating = useDocumentStore((state) => state.isCreating);
  const transportError = useDocumentStore((state) => state.transportError);
  const document = useDocumentStore((state) => state.document);

  useEffect(() => {
    if (docTypes.length === 0) {
      loadDocTypes();
    }
    if (templates.length === 0) {
      loadTemplates();
    }
  }, [docTypes.length, templates.length, loadDocTypes, loadTemplates]);

  // После успешного создания уходим на страницу документа
  useEffect(() => {
    if (document?.id && !isCreating && step === 2) {
      navigate(`/documents/${document.id}`);
    }
  }, [document?.id, isCreating, step, navigate]);

  const canCreate = Boolean(
    draft.trim().length >= 10 && docType && templateId && !isCreating
  );

  const handleCreate = async () => {
    await createDocument();
  };

  return (
    <div className="space-y-6">
      {transportError && (
        <div className="mb-4">
          <Banner level="error">{transportError}</Banner>
        </div>
      )}

      {step === 1 && <DraftInput onNext={() => setStep(2)} />}

      {step === 2 && (
        <div className="space-y-6">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-sm px-4 py-2.5"
              style={{ color: 'var(--muted-foreground)' }}
            >
              ← Назад к черновику
            </button>
          </div>

          <DocTypeSelector />
          <TemplateSelector />

          <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-sm"
              style={{ color: 'var(--muted-foreground)' }}
            >
              Изменить черновик
            </button>
            <PrimaryButton
              disabled={!canCreate}
              onClick={handleCreate}
              aria-label={
                !canCreate
                  ? 'Выберите тип и шаблон документа, чтобы запустить обработку'
                  : 'Запустить ИИ-обработку и создать документ'
              }
            >
              {isCreating ? 'Создаём документ…' : 'Запустить обработку →'}
            </PrimaryButton>
          </div>
        </div>
      )}
    </div>
  );
}