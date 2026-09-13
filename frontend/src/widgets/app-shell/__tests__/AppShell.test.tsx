import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppShell } from '../AppShell';

function renderShell() {
  return render(
    <MemoryRouter>
      <AppShell />
    </MemoryRouter>
  );
}

describe('AppShell', () => {
  it('имеет skip-link для навигации с клавиатуры', () => {
    renderShell();

    const skipLink = screen.getByText('Перейти к содержимому');
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute('href', '#main-content');
  });

  it('верхняя панель закреплена при прокрутке', () => {
    renderShell();

    expect(screen.getByTestId('top-bar')).toHaveClass('sticky');
  });

  it('основная область имеет id для skip-link', () => {
    renderShell();

    expect(document.getElementById('main-content')).toBeTruthy();
  });

  it('показывает название сервиса в шапке', () => {
    renderShell();

    expect(screen.getByText('Документ за 3 шага')).toBeInTheDocument();
  });

  it('содержит ссылку на управление шаблонами', () => {
    renderShell();

    expect(
      screen.getByRole('link', { name: 'Управление шаблонами' })
    ).toHaveAttribute('href', '/admin');
  });
});
