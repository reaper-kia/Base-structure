import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DraftInput } from '../DraftInput';
import { useDocumentStore } from '../../../shared/store/documentStore';

describe('DraftInput', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      draft: '',
      setDraft: (value: string) => useDocumentStore.setState({ draft: value }),
    });
  });

  it('счётчик обновляется при вводе', () => {
    render(<DraftInput />);
    const textarea = screen.getByLabelText('Черновик документа');

    fireEvent.change(textarea, { target: { value: 'Привет мир' } });

    expect(screen.getByText(/10 \/ 20000 символов/)).toBeTruthy();
  });

  it('демо-кнопка заполняет textarea', () => {
    render(<DraftInput />);
    const demoButton = screen.getByText('Чистый черновик');

    fireEvent.click(demoButton);

    const textarea = screen.getByLabelText('Черновик документа') as HTMLTextAreaElement;
    expect(textarea.value.length).toBeGreaterThan(100);
  });

  it('показывает предупреждение о превышении лимита', () => {
    const longText = 'a'.repeat(20001);
    useDocumentStore.setState({ draft: longText });

    render(<DraftInput />);

    expect(screen.getByText(/Превышен лимит/)).toBeTruthy();
  });
});