import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Menu, Moon, Sun, X } from 'lucide-react';
import { useLanguage } from '../../app/providers/LanguageProvider';
import { useTheme } from '../../app/providers/ThemeProvider';

/**
 * Каркас публичной части: шапка с навигацией, переключатели темы и языка,
 * подвал. Добавляй свои пункты в массив nav.
 */
export function PublicLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { language, setLanguage, t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [location.pathname]);

  const nav: Array<[string, string]> = [
    ['/', t('home')],
  ];

  return (
    <div className="site-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <div className="container site-header__inner">
          <Link to="/" className="brand">
            <span className="brand__mark">APP</span>
            <span className="brand__caption">hackathon template</span>
          </Link>
          <nav className={mobileOpen ? 'site-nav site-nav--open' : 'site-nav'} aria-label="Main navigation">
            {nav.map(([path, label]) => (
              <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="site-header__tools">
            <button className="icon-button language-toggle" type="button"
              onClick={() => setLanguage(language === 'ru' ? 'en' : 'ru')} aria-label="Change language">
              {language === 'ru' ? 'EN' : 'RU'}
            </button>
            <button className="icon-button" type="button" onClick={toggleTheme} aria-label="Change theme">
              {theme === 'light' ? <Moon size={19} /> : <Sun size={19} />}
            </button>
            <button className="icon-button mobile-toggle" type="button"
              onClick={() => setMobileOpen((value) => !value)} aria-label="Menu" aria-expanded={mobileOpen}>
              {mobileOpen ? <X size={21} /> : <Menu size={21} />}
            </button>
          </div>
        </div>
      </header>
      <main id="main-content"><Outlet /></main>
      <footer className="site-footer">
        <div className="container site-footer__bottom">
          <Link to="/login">{t('admin')}</Link>
        </div>
      </footer>
    </div>
  );
}
