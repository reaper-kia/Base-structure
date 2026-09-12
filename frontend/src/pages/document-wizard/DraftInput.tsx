import { useCallback } from 'react';
import { useDocumentStore } from '../../shared/store/documentStore';
import { DEMO_DRAFTS } from '../../shared/api/demoDrafts';
import { SpeechInput } from '../../features/speech/SpeechInput';

const MAX_LENGTH = 20000;

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
      // Если браузер не дал доступ к буферу — игнорируем
    }
  }, [setDraft]);

  const handleDemoClick = useCallback(
    (text: string) => {
      setDraft(text);
    },
    [setDraft]
  );

  const handleTranscript = useCallback(
    (text: string) => {
      const currentDraft = useDocumentStore.getState().draft.trimEnd();
      setDraft(currentDraft ? `${currentDraft}\n${text}` : text);
    },
    [setDraft],
  );

  return (
    <section style={{ marginBottom: '32px' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: '20px' }}>Шаг 1. Введите текст</h2>
      <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
        Вставьте или напишите черновик документа. Система исправит ошибки и оформит его.
      </p>

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Вставьте черновик документа сюда..."
        aria-label="Черновик документа"
        style={{
          width: '100%',
          minHeight: '240px',
          padding: '12px',
          fontSize: '16px',
          fontFamily: 'inherit',
          lineHeight: '1.5',
          border: isOverLimit ? '2px solid #dc3545' : '1px solid #ccc',
          borderRadius: '8px',
          resize: 'vertical',
          boxSizing: 'border-box',
          overflowWrap: 'anywhere',
          wordBreak: 'break-word',
        }}
      />

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '8px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <span
          style={{
            fontSize: '14px',
            color: isOverLimit ? '#dc3545' : trimmedLength === 0 ? '#999' : '#666',
          }}
        >
          {isOverLimit
            ? `Превышен лимит: ${draft.length} / ${MAX_LENGTH} символов`
            : `${draft.length} / ${MAX_LENGTH} символов`}
        </span>

        {trimmedLength === 0 && !isOverLimit && (
          <span style={{ fontSize: '13px', color: '#999' }}>
            Черновик не может быть пустым
          </span>
        )}
      </div>

      {/* Кнопки действий */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
          marginTop: '12px',
        }}
      >
        <button
          type="button"
          onClick={handlePaste}
          style={{
            padding: '8px 16px',
            fontSize: '14px',
            backgroundColor: '#f0f0f0',
            border: '1px solid #ccc',
            borderRadius: '6px',
            cursor: 'pointer',
          }}
        >
          Вставить из буфера
        </button>

        <SpeechInput onTranscript={handleTranscript} />

        {DEMO_DRAFTS.map((demo) => (
          <button
            key={demo.label}
            type="button"
            onClick={() => handleDemoClick(demo.text)}
            title={demo.text.slice(0, 100) + '...'}
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              backgroundColor: '#e7f3ff',
              border: '1px solid #b3d7ff',
              borderRadius: '6px',
              cursor: 'pointer',
              color: '#0056b3',
            }}
          >
            {demo.label}
          </button>
        ))}
      </div>
    </section>
  );
}