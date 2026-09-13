import { useEffect, useRef, useState } from 'react';
import type { RequisiteState } from '../../shared/api/types';

interface RequisiteEditorProps {
  requisite: RequisiteState;
  onSave: (value: string | null) => void;
  onCancel: () => void;
}

export function RequisiteEditor({
  requisite,
  onSave,
  onCancel,
}: RequisiteEditorProps) {
  const [value, setValue] = useState(requisite.value ?? '');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      onSave(value.trim() || null);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onCancel();
    }
  };

  const handleBlur = () => {
    if (value !== (requisite.value ?? '')) {
      onSave(value.trim() || null);
    } else {
      onCancel();
    }
  };

  return (
    <div
      className="p-3 transition-all"
      style={{
        background: 'var(--chip-user-bg)',
        border: '2px solid var(--chip-user-border)',
        borderLeft: '4px solid var(--chip-user-border)',
        borderRadius: 'var(--radius)',
        color: 'var(--chip-user-text)',
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          aria-hidden="true"
          className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold flex-shrink-0"
          style={{ background: 'var(--chip-user-border)', color: '#fff' }}
        >
          ✎
        </span>
        <span
          className="text-xs font-semibold"
          style={{ color: 'var(--chip-user-text)' }}
        >
          Редактирование
        </span>
      </div>

      <div
        className="text-xs font-semibold uppercase tracking-wider mb-2"
        style={{
          color: 'var(--chip-user-text)',
          opacity: 0.8,
          letterSpacing: '0.1em',
        }}
      >
        {requisite.label}
        {requisite.required && <span className="ml-1 normal-case">*</span>}
      </div>

      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={`Введите значение или оставьте пустым для пометки [${requisite.label}]`}
        aria-label={`Значение реквизита: ${requisite.label}`}
        className="w-full text-sm outline-none py-2 px-3 mb-2 transition-all"
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          color: 'var(--foreground)',
          fontFamily: 'var(--font-sans)',
        }}
      />

      <div className="text-xs mb-2" style={{ color: 'var(--chip-user-text)' }}>
        Нажмите{' '}
        <kbd
          className="px-1 py-0.5 rounded"
          style={{ background: 'var(--chip-value-bg)' }}
        >
          Enter
        </kbd>{' '}
        для сохранения,{' '}
        <kbd
          className="px-1 py-0.5 rounded"
          style={{ background: 'var(--chip-value-bg)' }}
        >
          Esc
        </kbd>{' '}
        для отмены
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onSave(value.trim() || null)}
          className="text-xs px-3 py-1.5 font-medium transition-all"
          style={{
            background: 'var(--primary)',
            color: 'var(--primary-foreground)',
            borderRadius: 'var(--radius)',
            cursor: 'pointer',
          }}
        >
          Сохранить
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-xs px-3 py-1.5 font-medium transition-all"
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--foreground)',
            cursor: 'pointer',
          }}
        >
          Отмена
        </button>
      </div>
    </div>
  );
}