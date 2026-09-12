import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PrimaryButton } from '../PrimaryButton';
import { Banner } from '../Banner';

describe('a11y: базовая доступность', () => {
  it('PrimaryButton передаёт aria-label', () => {
    render(<PrimaryButton aria-label="Сохранить документ">Сохранить</PrimaryButton>);

    expect(screen.getByRole('button', { name: 'Сохранить документ' })).toBeInTheDocument();
  });

  it('PrimaryButton disabled имеет aria-disabled', () => {
    render(<PrimaryButton disabled>Неактивна</PrimaryButton>);

    const button = screen.getByRole('button', { name: 'Неактивна' });
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toBeDisabled();
  });

  it('Banner уровня error имеет role="alert"', () => {
    render(<Banner level="error">Критическая ошибка</Banner>);

    expect(screen.getByRole('alert')).toHaveTextContent('Критическая ошибка');
  });

  it('Banner уровня info имеет role="status"', () => {
    render(<Banner level="info">Информационное сообщение</Banner>);

    expect(screen.getByRole('status')).toHaveTextContent('Информационное сообщение');
  });
});