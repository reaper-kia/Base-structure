import { describe, it, expect, beforeEach } from 'vitest';
import { useDocumentStore } from "../../shared/store/documentStore";

describe('documentStore', () => {
  beforeEach(() => {
    // Сбрасываем стор перед каждым тестом
    useDocumentStore.setState({
      docTypes: [],
      templates: [],
      draft: '',
      docType: null,
      templateId: null,
      document: null,
      mockScenario: 'all_found',
      isCreating: false,
      isPatchingRequisites: false,
      isRendering: false,
      transportError: null,
    });
  });

  it('сохраняет draft после установки', () => {
    const { setDraft } = useDocumentStore.getState();
    setDraft('Тестовый черновик');
    expect(useDocumentStore.getState().draft).toBe('Тестовый черновик');
  });

  it('draft остаётся целым при ошибке создания документа', async () => {
    const { setDraft, createDocument } = useDocumentStore.getState();
    setDraft('Важный текст');
    
    // Пытаемся создать без docType и templateId
    await createDocument();
    
    // Draft должен остаться
    expect(useDocumentStore.getState().draft).toBe('Важный текст');
  });

  it('загружает типы документов', async () => {
    const { loadDocTypes } = useDocumentStore.getState();
    await loadDocTypes();
    
    const { docTypes } = useDocumentStore.getState();
    expect(docTypes.length).toBeGreaterThan(0);
    expect(docTypes[0].id).toBe('memo');
  });

  it('загружает шаблоны', async () => {
    const { loadTemplates } = useDocumentStore.getState();
    await loadTemplates();
    
    const { templates } = useDocumentStore.getState();
    expect(templates.length).toBeGreaterThan(0);
    expect(templates[0].id).toBe('classic');
  });
});