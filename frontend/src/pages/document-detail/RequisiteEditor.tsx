import { useState, useEffect, useRef } from 'react';
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSave(value.trim() || null);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
  };

  const handleBlur = () => {
    // Сохраняем при потере фокуса, если значение изменилось
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
        border: '2px solid var(--primary)',
        borderLeft: '4px solid var(--primary)',
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold flex-shrink-0"
          style={{
            background: 'var(--primary)',
            color: '#fff',
          }}
        >
          ✎
        </span>
        <span
          className="text-xs font-semibold"
          style={{ color: 'var(--primary)' }}
        >
          Редактирование
        </span>
      </div>

      <div
        className="text-xs font-semibold uppercase tracking-wider mb-2"
        style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
      >
        {requisite.label}
        {requisite.required && (
          <span className="ml-1 normal-case text-red-600">*</span>
        )}
      </div>

      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={`Введите значение или оставьте пустым для пометки [${requisite.label}]`}
        className="w-full text-sm outline-none py-2 px-3 mb-2 transition-all"
        style={{
          background: '#fff',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          color: 'var(--foreground)',
          fontFamily: 'var(--font-sans)',
        }}
      />

      <div
        className="text-xs mb-2"
        style={{ color: 'var(--muted-foreground)' }}
      >
        Нажмите <kbd className="px-1 py-0.5 rounded" style={{ background: 'var(--border)' }}>Enter</kbd> для сохранения,{' '}
        <kbd className="px-1 py-0.5 rounded" style={{ background: 'var(--border)' }}>Esc</kbd> для отмены
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onSave(value.trim() || null)}
          className="text-xs px-3 py-1.5 font-medium transition-all"
          style={{
            background: 'var(--primary)',
            color: '#fff',
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