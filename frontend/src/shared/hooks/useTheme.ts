import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    ) {
      return 'dark';
    }
  } catch {
    // localStorage недоступен — остаёмся на светлой
  }
  return 'light';
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    const apply = () => root.setAttribute('data-theme', theme);

    apply();
    try {
      localStorage.setItem('theme', theme);
    } catch {
      // игнорируем: приватный режим и т.п.
    }

    // Плавные переходы темы включаем после первой отрисовки,
    // чтобы загрузка страницы не «мигала» перекраской
    const timer = window.setTimeout(
      () => document.body.classList.add('theme-ready'),
      50
    );

    // Защита значения: ThemeProvider из базовой заготовки может
    // перезаписать data-theme при старте. Возвращаем наше значение.
    const observer = new MutationObserver(() => {
      if (root.getAttribute('data-theme') !== theme) {
        apply();
      }
    });
    observer.observe(root, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    return () => {
      window.clearTimeout(timer);
      observer.disconnect();
    };
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const setTheme = (next: Theme) => {
    setThemeState(next);
  };

  return { theme, toggleTheme, setTheme };
}