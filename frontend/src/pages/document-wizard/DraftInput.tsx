import { useEffect, useRef, useState } from 'react';
import { useDocumentStore } from '../../shared/store/documentStore';
import { PrimaryButton } from '../../shared/ui/PrimaryButton';
import { SpeechInput } from '../../features/speech/SpeechInput';
import { DEMO_DRAFTS, type DemoDraft } from '../../shared/api/demoDrafts';

const MAX_LENGTH = 20_000;

interface DraftInputProps {
  onNext: () => void;
}

export function DraftInput({ onNext }: DraftInputProps) {
  const draft = useDocumentStore((state) => state.draft);
  const setDraft = useDocumentStore((state) => state.setDraft);
  const setDocType = useDocumentStore((state) => state.setDocType);
  const docType = useDocumentStore((state) => state.docType);
  const [pasteError, setPasteError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!docType) {
      setDocType('memo');
    }
  }, [docType, setDocType]);

  const handlePaste = async () => {
    setPasteError(null);
    try {
      const text = await navigator.clipboard.readText();
      setDraft(text.slice(0, MAX_LENGTH));
    } catch {
      setPasteError(
        'Буфер обмена недоступен. Вставьте текст сочетанием Ctrl+V (Cmd+V на Mac) в поле ниже.'
      );
      textareaRef.current?.focus();
    }
  };

  const loadDemo = (demo: DemoDraft) => {
    setDraft(demo.text);
    // Черновик организаторов уже знает, какой это тип документа —
    // не заставляем пользователя угадывать его на следующем шаге.
    setDocType(demo.docType);
    setPasteError(null);
  };

  const appendTranscript = (text: string) => {
    const separator = draft.trim() ? '\n' : '';
    setDraft((draft + separator + text).slice(0, MAX_LENGTH));
  };

  const canContinue = draft.trim().length >= 10 && draft.length <= MAX_LENGTH;

  return (
    <div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-2">
          <label
            htmlFor="draft-textarea"
            className="block text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Текст черновика
          </label>
          <textarea
            ref={textareaRef}
            id="draft-textarea"
            value={draft}
            onChange={(event) => setDraft(event.target.value.slice(0, MAX_LENGTH))}
            placeholder="Введите или вставьте текст документа... Можно вводить неаккуратно — ИИ исправит орфографию, стиль и структуру."
            rows={12}
            aria-describedby="draft-hint"
            className="w-full outline-none resize-none transition-all py-4 px-4 text-sm leading-relaxed"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--foreground)',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <div
            id="draft-hint"
            className="flex items-center justify-between mt-1 flex-wrap gap-2"
          >
            <span className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
              {draft.length} / {MAX_LENGTH} символов
            </span>
            {draft.length > 0 && (
              <button
                type="button"
                onClick={() => setDraft('')}
                aria-label="Очистить поле черновика"
                className="text-xs hover:underline"
                style={{ color: 'var(--muted-foreground)' }}
              >
                Очистить
              </button>
            )}
          </div>

          {pasteError && (
            <div
              role="status"
              className="mt-2 px-3 py-2 text-xs"
              style={{
                background: 'var(--banner-warn-bg)',
                border: '1px solid var(--banner-warn-border)',
                color: 'var(--banner-warn-text)',
                borderRadius: 'var(--radius)',
              }}
            >
              {pasteError}
            </div>
          )}
        </div>

        <div>
          <div
            className="block text-xs font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            Черновики организаторов
          </div>
          <div className="space-y-2">
            <button
              type="button"
              onClick={handlePaste}
              aria-label="Вставить текст из буфера обмена"
              className="w-full text-left px-3 py-2.5 text-xs font-semibold transition-all"
              style={{
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: 'var(--foreground)',
              }}
            >
              Вставить из буфера
            </button>
            <SpeechInput onTranscript={appendTranscript} />
            {DEMO_DRAFTS.map((demo) => (
              <button
                key={demo.id}
                type="button"
                onClick={() => loadDemo(demo)}
                aria-label={`Загрузить пример: ${demo.label}`}
                title={demo.hint}
                className="w-full text-left px-3 py-2.5 text-xs transition-all"
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  color: 'var(--muted-foreground)',
                }}
              >
                <span className="font-medium">{demo.label}</span>
                <span
                  className="block mt-0.5 opacity-70"
                  style={{ fontSize: '0.68rem' }}
                >
                  {demo.hint}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end">
        <PrimaryButton
          disabled={!canContinue}
          onClick={onNext}
          aria-label={
            !canContinue
              ? 'Введите минимум 10 символов, чтобы продолжить'
              : 'Перейти к выбору типа и шаблона'
          }
        >
          Далее: выбор типа и шаблона →
        </PrimaryButton>
      </div>
    </div>
  );
}