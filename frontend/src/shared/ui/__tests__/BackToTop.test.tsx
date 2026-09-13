import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { act, render, screen, fireEvent } from '@testing-library/react';
import { BackToTop } from '../BackToTop';

function setScrollY(value: number) {
  Object.defineProperty(window, 'scrollY', {
    value,
    writable: true,
    configurable: true,
  });
}

describe('BackToTop', () => {
  beforeEach(() => {
    setScrollY(0);
    window.scrollTo = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('скрыта, пока страница не прокручена', () => {
    render(<BackToTop />);

    expect(
      screen.queryByRole('button', { name: 'Вернуться к началу страницы' })
    ).toBeNull();
  });

  it('появляется после прокрутки ниже порога', () => {
    render(<BackToTop />);

    act(() => {
      setScrollY(500);
      window.dispatchEvent(new Event('scroll'));
    });

    expect(
      screen.getByRole('button', { name: 'Вернуться к началу страницы' })
    ).toBeInTheDocument();
  });

  it('по клику прокручивает окно в начало', () => {
    render(<BackToTop />);

    act(() => {
      setScrollY(500);
      window.dispatchEvent(new Event('scroll'));
    });

    fireEvent.click(
      screen.getByRole('button', { name: 'Вернуться к началу страницы' })
    );

    expect(window.scrollTo).toHaveBeenCalledWith(
      expect.objectContaining({ top: 0 })
    );
  });

  it('снимает обработчик прокрутки при размонтировании', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = render(<BackToTop />);

    unmount();

    expect(removeSpy).toHaveBeenCalledWith('scroll', expect.any(Function));
  });
});
