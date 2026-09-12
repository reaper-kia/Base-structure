import { useEffect, useState } from 'react';
import { useDocumentStore } from '../../shared/store/documentStore';

interface TextEditorProps {
  improvedText: string | null;
}

/**
 * Ручная правка улучшенного текста перед скачиванием (сценарий 7).
 *
 * Правка не запускает обработку заново: модель уже отработала, меняется
 * только то, что уйдёт в файл. Отменить правку можно, пока она не сохранена.
 */
export function TextEditor({ improvedText }: TextEditorProps) {
  const updateText = useDocumentStore((state) => state.updateText);
  const isSaving = useDocumentStore((state) => state.isSavingText);

  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(improvedText ?? '');

  // Текст мог измениться после повторной обработки — подхватываем новый,
  // пока пользователь не начал править.
  useEffect(() => {
    if (!isEditing) setValue(improvedText ?? '');
  }, [improvedText, isEditing]);

  if (improvedText === null) return null;

  const changed = value.trim() !== improvedText.trim();
  const canSave = changed && value.trim().length > 0 && !isSaving;

  if (!isEditing) {
    return (
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className="text-xs underline"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Править текст вручную
        </button>
      </div>
    );
  }

  return (
    <div
      className="p-4 space-y-3"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
      }}
    >
      <label
        htmlFor="improved-text-editor"
        className="block text-xs font-semibold uppercase tracking-widest"
        style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
      >
        Текст документа
      </label>

      <textarea
        id="improved-text-editor"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={12}
        className="w-full outline-none resize-none py-3 px-3 text-sm leading-relaxed"
        style={{
          background: 'var(--background)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          color: 'var(--foreground)',
          fontFamily: 'var(--font-sans)',
        }}
      />

      <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
        Правка попадёт в DOCX как есть. Реквизиты редактируются отдельно —
        в блоке ниже.
      </p>

      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={() => {
            setValue(improvedText);
            setIsEditing(false);
          }}
          disabled={isSaving}
          className="text-xs underline"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Отменить
        </button>
        <button
          type="button"
          disabled={!canSave}
          onClick={async () => {
            await updateText(value.trim());
            setIsEditing(false);
          }}
          aria-busy={isSaving}
          className="px-5 py-2 text-sm font-semibold"
          style={{
            background: canSave ? 'var(--primary)' : 'var(--muted)',
            color: canSave ? '#fff' : 'var(--muted-foreground)',
            borderRadius: 'var(--radius)',
            cursor: canSave ? 'pointer' : 'not-allowed',
          }}
        >
          {isSaving ? 'Сохраняю…' : 'Сохранить правку'}
        </button>
      </div>
    </div>
  );
}
