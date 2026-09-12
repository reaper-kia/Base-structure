import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { DocumentState } from '../../shared/api/types';
import { useDocumentStore } from '../../shared/store/documentStore';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';

interface FailedScreenProps {
  document: DocumentState;
  onRetry: () => void;
}

export function FailedScreen({ document, onRetry }: FailedScreenProps) {
  const navigate = useNavigate();
  const setDraft = useDocumentStore((state) => state.setDraft);
  const [copied, setCopied] = useState(false);

  const recoverable = document.error?.recoverable ?? false;

  const handleEditDraft = () => {
    setDraft(document.draft);
    navigate('/wizard');
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(document.draft);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // буфер недоступен — текст всё равно виден и выделяется вручную
    }
  };

  return (
    <section
      data-testid="failed-screen"
      className="flex flex-col items-center gap-6 py-10 text-center"
    >
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold"
        style={{
          background: 'var(--banner-error-bg)',
          border: '2px solid var(--banner-error-border)',
          color: 'var(--banner-error-text)',
        }}
        aria-hidden="true"
      >
        ✕
      </div>

      <div>
        <h2
          className="text-lg font-semibold mb-2"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          Не удалось обработать документ
        </h2>
        <p className="text-sm max-w-md" style={{ color: 'var(--muted-foreground)' }}>
          {document.error?.message ?? 'Неизвестная ошибка. Попробуйте ещё раз.'}
        </p>
      </div>

      <div
        className="w-full max-w-xl p-4 text-left"
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
        }}
      >
        <div className="flex items-center justify-between gap-3 mb-2">
          <div
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Ваш черновик сохранён целиком
          </div>
          <button
            type="button"
            onClick={handleCopy}
            className="text-xs underline flex-shrink-0"
            style={{ color: 'var(--muted-foreground)' }}
          >
            {copied ? 'Скопировано ✓' : 'Скопировать черновик'}
          </button>
        </div>
        <pre
          data-testid="failed-draft"
          className="text-sm leading-relaxed"
          style={{
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            wordBreak: 'break-word',
            color: 'var(--foreground)',
            maxHeight: 320,
            overflowY: 'auto',
            margin: 0,
          }}
        >
          {document.draft}
        </pre>
      </div>

      <div className="flex gap-3 flex-wrap justify-center">
        {recoverable && <PrimaryButton onClick={onRetry}>Повторить</PrimaryButton>}
        <PrimaryButton variant="ghost" onClick={handleEditDraft}>
          Изменить черновик
        </PrimaryButton>
      </div>
    </section>
  );
}