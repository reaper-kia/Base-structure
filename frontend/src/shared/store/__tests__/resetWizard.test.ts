import { describe, it, expect } from 'vitest';
import { useDocumentStore } from '../documentStore';

describe('FE-F2: resetWizard', () => {
  it('обнуляет поля визарда и чистит sessionStorage', () => {
    useDocumentStore.getState().setDraft('текст черновика');
    useDocumentStore.getState().setDocType('memo');
    useDocumentStore.getState().setTemplateId('classic');

    useDocumentStore.getState().resetWizard();

    const state = useDocumentStore.getState();
    expect(state.draft).toBe('');
    expect(state.docType).toBeNull();
    expect(state.templateId).toBeNull();
    expect(state.document).toBeNull();
    expect(state.activeDocumentId).toBeNull();
    expect(state.renderFallback).toBeNull();
    expect(state.transportError).toBeNull();
    expect(state.pollingTimedOut).toBe(false);
    expect(sessionStorage.getItem('doc3-wizard-session')).toBeNull();
  });
});