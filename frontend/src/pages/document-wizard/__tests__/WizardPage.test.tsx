import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WizardPage } from '../WizardPage';
import { useDocumentStore } from '../../../shared/store/documentStore';

vi.mock('../../../shared/hooks/usePollDocument', () => ({
  usePollDocument: () => {},
}));

function renderWizard() {
  return render(
    <MemoryRouter>
      <WizardPage />
    </MemoryRouter>
  );
}

describe('WizardPage', () => {
  beforeEach(() => {
    useDocumentStore.setState({
      draft: '',
      docType: null,
      templateId: null,
      document: null,
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
      isCreating: false,
      transportError: null,
    });
  });

  it('кнопка "Создать" неактивна без типа', () => {
    useDocumentStore.setState({ draft: 'Текст', templateId: 'classic' });
    renderWizard();

    expect(screen.getByText(/Создать документ/)).toBeDisabled();
  });

  it('недоступный шаблон нельзя выбрать', () => {
    renderWizard();

    const card = screen.getByTestId('template-broken');
    expect(card).toBeDisabled();
    expect(card).toHaveAttribute('aria-disabled', 'true');
  });

  it('порядок типов совпадает с порядком из API', () => {
    renderWizard();

    const cards = screen.getAllByTestId(/^doc-type-/);
    expect(cards[0]).toHaveTextContent('Служебная записка');
    expect(cards[1]).toHaveTextContent('Докладная записка');
  });
});