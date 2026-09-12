import { Outlet, useLocation, Link } from 'react-router-dom';
import { useDocumentStore } from '../../shared/store/documentStore';
import { ThemeToggle } from '../../shared/ui/ThemeToggle';

const STEPS = [
  { label: 'Черновик', sub: 'Введите текст' },
  { label: 'Настройки', sub: 'Тип и шаблон' },
  { label: 'Обработка', sub: 'ИИ-анализ' },
];

function StepBar({ current }: { current: 0 | 1 | 2 }) {
  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, index) => (
        <div key={step.label} className="flex items-center">
          <div className="flex flex-col items-center gap-0.5 px-2">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all"
              style={{
                background:
                  index < current
                    ? '#22c55e'
                    : index === current
                      ? 'var(--accent)'
                      : 'var(--header-overlay)',
                color: '#fff',
              }}
            >
              {index < current ? '✓' : index + 1}
            </div>
            <span
              className="text-xs text-center whitespace-nowrap"
              style={{
                color:
                  index <= current
                    ? 'var(--header-on-soft)'
                    : 'var(--header-on-faint)',
              }}
            >
              {step.label}
            </span>
          </div>
          {index < 2 && (
            <div
              className="w-10 h-px mb-4"
              style={{
                background: index < current ? '#22c55e' : 'var(--header-line)',
              }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export function AppShell() {
  const location = useLocation();
  const draft = useDocumentStore((state) => state.draft);

  const current: 0 | 1 | 2 = location.pathname.startsWith('/documents')
    ? 2
    : draft.trim().length > 0
      ? 1
      : 0;

  return (
    <div
      className="min-h-full flex flex-col"
      style={{ fontFamily: 'var(--font-sans)', background: 'var(--background)' }}
    >
      <a href="#main-content" className="skip-link">
        Перейти к содержимому
      </a>

      {/* Липкая верхняя панель: логотип, название, тема, шаги */}
      <div data-testid="top-bar" className="top-bar sticky top-0 z-50">
        <div
          style={{
            background: 'var(--header-bar-bg)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            boxShadow: 'var(--header-shadow)',
          }}
        >
          <div className="max-w-4xl mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0"
              style={{
                background: 'var(--header-overlay)',
                border: '1.5px solid var(--header-overlay-border)',
                color: 'var(--header-on)',
              }}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="8" height="8" rx="1.5" fill="currentColor" fillOpacity="0.9" />
                <rect x="13" y="3" width="8" height="8" rx="1.5" fill="currentColor" fillOpacity="0.6" />
                <rect x="3" y="13" width="8" height="8" rx="1.5" fill="currentColor" fillOpacity="0.6" />
                <rect x="13" y="13" width="8" height="8" rx="1.5" fill="currentColor" fillOpacity="0.9" />
              </svg>
            </div>
            <div className="flex items-center gap-3">
              <div>
                <div
                  className="text-xs font-medium"
                  style={{ color: 'var(--header-on-muted)', letterSpacing: '0.04em' }}
                >
                  Портал государственных сервисов
                </div>
                <div
                  className="font-bold"
                  style={{
                    fontSize: '1.05rem',
                    letterSpacing: '-0.01em',
                    color: 'var(--header-on)',
                  }}
                >
                  Документ за 3 шага
                </div>
              </div>
              <ThemeToggle />
            </div>
          </div>
          <StepBar current={current} />
          </div>
        </div>
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            height: 16,
            pointerEvents: 'none',
            background:
              'linear-gradient(to bottom, var(--header-bar-fade), transparent)',
          }}
        />
      </div>

      <header style={{ background: 'var(--header-gradient)' }}>
        <div className="max-w-4xl mx-auto px-4 md:px-6 pt-6 pb-8">
          <div className="flex items-end justify-between gap-4 flex-wrap">
            <div>
              <div
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full mb-3 text-xs font-medium"
                style={{
                  background: 'var(--header-overlay)',
                  color: 'var(--header-on-soft)',
                  border: '1px solid var(--header-overlay-border)',
                }}
              >
                <span style={{ color: 'var(--accent)' }}>●</span> ИИ-конструктор
                служебных документов
              </div>
              <h1
                className="text-2xl md:text-3xl font-bold leading-tight mb-2"
                style={{ letterSpacing: '-0.02em', color: 'var(--header-on)' }}
              >
                Создайте официальный документ
                <br className="hidden md:block" /> без лишних усилий
              </h1>
              <p
                className="text-sm"
                style={{ color: 'var(--header-on-muted)', maxWidth: 460 }}
              >
                ИИ исправит текст, проверит реквизиты и сформирует готовый
                .docx-файл по выбранному шаблону
              </p>
            </div>
            <div className="flex flex-col gap-1.5 flex-shrink-0">
              {[
                '✓ Официально-деловой стиль',
                '✓ Проверка реквизитов',
                '✓ Скачивание DOCX',
              ].map((feature) => (
                <div
                  key={feature}
                  className="text-xs px-3 py-1.5 rounded-md font-medium"
                  style={{
                    background: 'var(--header-overlay)',
                    color: 'var(--header-on-soft)',
                    border: '1px solid var(--header-overlay-border)',
                  }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div
          aria-hidden="true"
          style={{
            height: 120,
            marginTop: -32,
            background:
              'linear-gradient(to bottom, transparent, var(--background))',
            pointerEvents: 'none',
          }}
        />
      </header>

      <main
        id="main-content"
        className="flex-1 max-w-4xl w-full mx-auto px-4 md:px-6 py-8"
      >
        <Outlet />
      </main>

      <footer
        className="border-t py-3 flex-shrink-0"
        style={{ borderColor: 'var(--border)', background: 'var(--card)' }}
      >
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-between gap-4 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
            Документ за 3 шага · ФСП Россия · 2026
          </span>
          <Link
            to="/dev"
            className="text-xs underline"
            style={{ color: 'var(--muted-foreground)' }}
          >
            Dev-панель
          </Link>
          <span
            className="text-xs"
            style={{ color: 'var(--muted-foreground)', fontFamily: 'var(--font-mono)' }}
          >
            ГОСТ Р 7.0.97-2016
          </span>
        </div>
      </footer>
    </div>
  );
}