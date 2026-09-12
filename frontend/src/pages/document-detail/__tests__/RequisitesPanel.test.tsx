import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RequisitesPanel } from '../RequisitesPanel';
import type { RequisiteState } from '../../../shared/api/types';

describe('RequisitesPanel', () => {
  const mockRequisites: RequisiteState[] = [
    {
      key: 'addressee',
      label: 'Адресат',
      value: 'Директору ООО «Ромашка»',
      status: 'found_in_draft',
      required: true,
    },
    {
      key: 'position',
      label: 'Должность',
      value: null,
      status: 'missing',
      required: true,
    },
    {
      key: 'doc_date',
      label: 'Дата документа',
      value: '11.09.2026',
      status: 'auto_filled',
      required: true,
    },
  ];

  let mockOnPatch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnPatch = vi.fn().mockResolvedValue(undefined);
  });

  it('missing рендерится жёлтым с двумя кнопками', () => {
    render(
      <RequisitesPanel
        requisites={mockRequisites}
        onPatch={mockOnPatch}
        isPatching={false}
      />
    );

    const missingChip = screen.getByText('Должность').closest('[class*="p-3"]');
    expect(missingChip).toBeTruthy();
    expect(screen.getByText('Указать')).toBeTruthy();
    expect(screen.getByText('Оставить пустым')).toBeTruthy();
  });

  it('auto_filled показывает подпись про систему', () => {
    render(
      <RequisitesPanel
        requisites={mockRequisites}
        onPatch={mockOnPatch}
        isPatching={false}
      />
    );

    expect(screen.getByText('Подставлено системой: текущая дата')).toBeTruthy();
  });

  it('ввод значения вызывает PATCH с непустой строкой', async () => {
    render(
      <RequisitesPanel
        requisites={mockRequisites}
        onPatch={mockOnPatch}
        isPatching={false}
      />
    );

    fireEvent.click(screen.getByText('Указать'));

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Менеджер' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(mockOnPatch).toHaveBeenCalledWith({ position: 'Менеджер' });
    });
  });

  it('«Оставить пустым» вызывает PATCH с null', async () => {
    render(
      <RequisitesPanel
        requisites={mockRequisites}
        onPatch={mockOnPatch}
        isPatching={false}
      />
    );

    fireEvent.click(screen.getByText('Оставить пустым'));

    await waitFor(() => {
      expect(mockOnPatch).toHaveBeenCalledWith({ position: null });
    });
  });
});