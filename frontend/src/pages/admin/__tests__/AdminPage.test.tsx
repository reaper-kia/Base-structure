import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AdminPage } from '../AdminPage';

const apiMock = vi.hoisted(() => ({
  getTemplates: vi.fn(),
  uploadTemplate: vi.fn(),
}));

vi.mock('../../../shared/api', () => ({ api: apiMock }));

function renderPage() {
  return render(
    <MemoryRouter>
      <AdminPage />
    </MemoryRouter>
  );
}

describe('AdminPage', () => {
  beforeEach(() => {
    sessionStorage.clear();
    apiMock.getTemplates.mockReset().mockResolvedValue([
      {
        id: 'classic',
        name: 'Классический',
        description: 'Встроенный шаблон',
        available: true,
      },
    ]);
    apiMock.uploadTemplate.mockReset().mockResolvedValue({
      id: 'custom',
      name: 'Загруженный шаблон',
      rules: {},
      warnings: [],
    });
  });

  it('загружает DOCX с введённым административным токеном', async () => {
    renderPage();
    await screen.findByText('Классический');

    const file = new File(['docx'], 'custom.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    fireEvent.change(screen.getByLabelText('Ключ администратора'), {
      target: { value: 'admin-secret' },
    });
    fireEvent.change(screen.getByLabelText('DOCX-файл'), {
      target: { files: [file] },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Загрузить шаблон' })
    );

    await waitFor(() => {
      expect(apiMock.uploadTemplate).toHaveBeenCalledWith(
        file,
        'admin-secret'
      );
    });
    expect(
      await screen.findByText(/Шаблон «Загруженный шаблон» добавлен/)
    ).toBeInTheDocument();
    expect(apiMock.getTemplates).toHaveBeenCalledTimes(2);
    expect(sessionStorage.getItem('doc3-admin-token')).toBe('admin-secret');
  });

  it('не отправляет файл без токена', async () => {
    renderPage();
    await screen.findByText('Классический');

    expect(
      screen.getByRole('button', { name: 'Загрузить шаблон' })
    ).toBeDisabled();
    expect(apiMock.uploadTemplate).not.toHaveBeenCalled();
  });

  it('показывает ответ backend при неверном токене', async () => {
    apiMock.uploadTemplate.mockRejectedValue(
      new Error('Недействительный ключ администратора')
    );
    renderPage();
    await screen.findByText('Классический');

    const file = new File(['docx'], 'custom.docx');
    fireEvent.change(screen.getByLabelText('Ключ администратора'), {
      target: { value: 'wrong-token' },
    });
    fireEvent.change(screen.getByLabelText('DOCX-файл'), {
      target: { files: [file] },
    });
    fireEvent.click(
      screen.getByRole('button', { name: 'Загрузить шаблон' })
    );

    expect(
      await screen.findByText('Недействительный ключ администратора')
    ).toBeInTheDocument();
  });
});
