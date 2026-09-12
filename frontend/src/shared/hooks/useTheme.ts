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

    return () => observer.disconnect();
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const setTheme = (next: Theme) => {
    setThemeState(next);
  };

  return { theme, toggleTheme, setTheme };
}