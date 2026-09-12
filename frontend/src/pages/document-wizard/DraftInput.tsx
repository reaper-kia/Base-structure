import { useCallback } from 'react';
import { useDocumentStore } from '../../shared/store/documentStore';
import { DEMO_DRAFTS } from '../../shared/api/demoDrafts';
import { FieldLabel } from '../../shared/ui/FieldLabel';
import { DocIcon, type DocIconId } from '../../shared/ui/docIcons';

const MAX_LENGTH = 20000;

const DEMO_ICONS: DocIconId[] = ['memo', 'memo', 'letter', 'report', 'reference'];

const cardStyle = {
  background: 'var(--card)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
} as const;

export function DraftInput() {
  const draft = useDocumentStore((state) => state.draft);
  const setDraft = useDocumentStore((state) => state.setDraft);

  const trimmedLength = draft.trim().length;
  const isOverLimit = draft.length > MAX_LENGTH;

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setDraft(text);
    } catch {
      // браузер не дал доступ к буферу обмена
    }
  }, [setDraft]);

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className="md:col-span-2">
        <FieldLabel>Текст черновика</FieldLabel>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={
            'Введите или вставьте текст документа...\n\nМожно вводить неаккуратно — ИИ исправит орфографию, стиль и структуру.'
          }
          rows={12}
          aria-label="Черновик документа"
          className="w-full outline-none resize-none transition-all py-4 px-4 text-sm leading-relaxed"
          style={{
            ...cardStyle,
            border: `1px solid ${isOverLimit ? '#dc2626' : 'var(--border)'}`,
            color: 'var(--foreground)',
            fontFamily: 'var(--font-sans)',
          }}
          onFocus={(event) => {
            if (!isOverLimit) {
              event.target.style.borderColor = 'var(--primary)';
            }
          }}
          onBlur={(event) => {
            event.target.style.borderColor = isOverLimit
              ? '#dc2626'
              : 'var(--border)';
          }}
        />
        <div className="flex items-center justify-between mt-1 flex-wrap gap-2">
          <span
            className="text-xs"
            style={{ color: isOverLimit ? '#dc2626' : 'var(--muted-foreground)' }}
          >
            {draft.length} / {MAX_LENGTH} символов
            {isOverLimit && ' — превышен лимит'}
          </span>
          <span className="flex items-center gap-3">
            {trimmedLength === 0 && !isOverLimit && (
              <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
                Черновик не может быть пустым
              </span>
            )}
            {draft.length > 0 && (
              <button
                type="button"
                onClick={() => setDraft('')}
                className="text-xs"
                style={{ color: 'var(--muted-foreground)' }}
              >
                Очистить
              </button>
            )}
          </span>
        </div>
      </div>

      <div>
        <FieldLabel>Примеры и инструменты</FieldLabel>
        <div className="space-y-2">
          <button
            type="button"
            onClick={handlePaste}
            className="w-full text-left px-3 py-2.5 text-xs font-semibold transition-all"
            style={{ ...cardStyle, color: 'var(--foreground)' }}
            onMouseEnter={(event) => {
              event.currentTarget.style.borderColor = 'var(--primary)';
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.borderColor = 'var(--border)';
            }}
          >
            ⧉ Вставить из буфера
          </button>

          {DEMO_DRAFTS.map((demo, index) => (
            <button
              key={demo.label}
              type="button"
              onClick={() => setDraft(demo.text)}
              className="w-full text-left px-3 py-2.5 text-xs transition-all"
              style={{ ...cardStyle, color: 'var(--muted-foreground)' }}
              onMouseEnter={(event) => {
                event.currentTarget.style.borderColor = 'var(--primary)';
                event.currentTarget.style.color = 'var(--foreground)';
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.borderColor = 'var(--border)';
                event.currentTarget.style.color = 'var(--muted-foreground)';
              }}
            >
              <span className="mr-1.5 inline-flex align-middle">
                <DocIcon id={DEMO_ICONS[index] ?? 'memo'} color="var(--primary)" />
              </span>
              <span className="font-medium" style={{ color: 'var(--foreground)' }}>
                {demo.label}
              </span>
              <span className="block mt-0.5 opacity-70" style={{ fontSize: '0.68rem' }}>
                {demo.text.substring(0, 60)}…
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}