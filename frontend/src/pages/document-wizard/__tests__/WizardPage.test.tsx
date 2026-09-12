import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WizardPage } from '../WizardPage';
import { useDocumentStore } from '../../../shared/store/documentStore';

function renderWizard() {
  return render(
    <MemoryRouter>
      <WizardPage />
    </MemoryRouter>
  );
}

function goToStep2() {
  fireEvent.click(screen.getByText(/Далее: выбор типа и шаблона/));
}

describe('WizardPage', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      draft: '',
      docType: null,
      templateId: null,
      document: null,
      isCreating: false,
      transportError: null,
      docTypes: [
        {
          id: 'memo',
          name: 'Служебная записка',
          description: 'Внутренний документ',
          requisites: [{ key: 'addressee', label: 'Адресат', required: true }],
        },
        {
          id: 'report',
          name: 'Докладная записка',
          description: 'Сообщение о событии',
          requisites: [],
        },
      ],
      templates: [
        {
          id: 'classic',
          name: 'Классический',
          description: 'ГОСТ',
          preview_url: '/test.png',
          available: true,
        },
        {
          id: 'broken',
          name: 'Сломанный',
          description: 'Нет файлов',
          preview_url: '/test2.png',
          available: false,
        },
      ],
    });
  });

  it('кнопка «Далее» неактивна без текста', () => {
    renderWizard();

    expect(screen.getByText(/Далее: выбор типа и шаблона/)).toBeDisabled();
  });

  it('на шаге 2 запуск неактивен без шаблона', () => {
    useDocumentStore.setState({ draft: 'Текст черновика достаточной длины' });
    renderWizard();
    goToStep2();

    expect(screen.getByText(/Запустить обработку/)).toBeDisabled();
  });

  it('недоступный шаблон нельзя выбрать', () => {
    useDocumentStore.setState({ draft: 'Текст черновика достаточной длины' });
    renderWizard();
    goToStep2();

    const card = screen.getByTestId('template-broken');
    expect(card).toBeDisabled();
    expect(card).toHaveAttribute('aria-disabled', 'true');
  });

  it('порядок типов совпадает с порядком из API', () => {
    useDocumentStore.setState({ draft: 'Текст черновика достаточной длины' });
    renderWizard();
    goToStep2();

    const cards = screen.getAllByTestId(/^doc-type-/);
    expect(cards[0]).toHaveTextContent('Служебная записка');
    expect(cards[1]).toHaveTextContent('Докладная записка');
  });
});