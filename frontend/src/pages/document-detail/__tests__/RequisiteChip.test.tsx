import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RequisiteChip } from '../RequisiteChip';
import type { RequisiteState } from '../../../shared/api/types';

describe('RequisiteChip', () => {
  it('auto_filled показывает подпись про систему', () => {
    const req: RequisiteState = {
      key: 'doc_date',
      label: 'Дата документа',
      value: '12.09.2026',
      status: 'auto_filled',
      required: true,
    };

    render(<RequisiteChip requisite={req} onEdit={() => {}} />);

    expect(screen.getByText('Подставлено системой: текущая дата')).toBeInTheDocument();
  });

  it('found_in_draft не показывает подпись про систему', () => {
    const req: RequisiteState = {
      key: 'author',
      label: 'Автор',
      value: 'Иванов И.И.',
      status: 'found_in_draft',
      required: true,
    };

    render(<RequisiteChip requisite={req} onEdit={() => {}} />);

    expect(screen.queryByText(/Подставлено системой/)).not.toBeInTheDocument();
  });

  it('missing показывает подсказку про [Адресат]', () => {
    const req: RequisiteState = {
      key: 'addressee',
      label: 'Адресат',
      value: null,
      status: 'missing',
      required: true,
    };

    render(
      <RequisiteChip
        requisite={req}
        onEdit={() => {}}
        onLeaveBlank={() => {}}
      />
    );

    expect(screen.getByText(/\[Адресат\]/)).toBeInTheDocument();
  });

  it('left_blank показывает подпись про пометку', () => {
    const req: RequisiteState = {
      key: 'addressee',
      label: 'Адресат',
      value: null,
      status: 'left_blank',
      required: true,
    };

    render(<RequisiteChip requisite={req} onEdit={() => {}} />);

    expect(screen.getByText(/Будет помечено в документе/)).toBeInTheDocument();
  });
});