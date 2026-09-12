import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DraftInput } from '../DraftInput';
import { useDocumentStore } from '../../../shared/store/documentStore';
import { DEMO_DRAFTS } from '../../../shared/api/demoDrafts';

describe('DraftInput', () => {
  beforeEach(() => {
    useDocumentStore.setState({ draft: '', docType: null });
  });

  it('счётчик обновляется при вводе', () => {
    render(<DraftInput onNext={() => {}} />);
    const textarea = screen.getByLabelText('Текст черновика');

    fireEvent.change(textarea, { target: { value: 'Привет мир' } });

    expect(screen.getByText('10 / 20000 символов')).toBeInTheDocument();
  });

  it('демо-кнопка заполняет textarea черновиком организаторов', () => {
    render(<DraftInput onNext={() => {}} />);

    fireEvent.click(screen.getByText('Чистый черновик'));

    const textarea = screen.getByLabelText('Текст черновика') as HTMLTextAreaElement;
    expect(textarea.value).toBe(DEMO_DRAFTS[0].text);
  });

  it('демо-кнопка выставляет тип документа своего черновика', () => {
    render(<DraftInput onNext={() => {}} />);

    fireEvent.click(screen.getByText('Информационная справка'));

    expect(useDocumentStore.getState().docType).toBe('reference');
  });

  it('ввод длиннее лимита обрезается до 20000 символов', () => {
    render(<DraftInput onNext={() => {}} />);
    const textarea = screen.getByLabelText('Текст черновика');

    fireEvent.change(textarea, { target: { value: 'а'.repeat(20001) } });

    expect((textarea as HTMLTextAreaElement).value).toHaveLength(20000);
    expect(screen.getByText('20000 / 20000 символов')).toBeInTheDocument();
  });
});