import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DraftInput } from '../DraftInput';
import { useDocumentStore } from '../../../shared/store/documentStore';

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

  it('демо-кнопка заполняет textarea', () => {
    render(<DraftInput onNext={() => {}} />);

    fireEvent.click(screen.getByText('Заявление на отпуск'));

    const textarea = screen.getByLabelText('Текст черновика') as HTMLTextAreaElement;
    expect(textarea.value.length).toBeGreaterThan(100);
  });

  it('ввод длиннее лимита обрезается до 20000 символов', () => {
    render(<DraftInput onNext={() => {}} />);
    const textarea = screen.getByLabelText('Текст черновика');

    fireEvent.change(textarea, { target: { value: 'а'.repeat(20001) } });

    expect((textarea as HTMLTextAreaElement).value).toHaveLength(20000);
    expect(screen.getByText('20000 / 20000 символов')).toBeInTheDocument();
  });
});