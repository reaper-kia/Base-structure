import type { RequisiteState } from '../../shared/api/types';

interface RequisiteChipProps {
  requisite: RequisiteState;
  onEdit: () => void;
  onLeaveBlank?: () => void;
}

const STATUS_STYLES = {
  found_in_draft: {
    borderColor: 'var(--chip-found-border)',
    bgColor: 'var(--chip-found-bg)',
    textColor: 'var(--chip-found-text)',
    label: 'Найдено в черновике',
    icon: '✓',
  },
  user_provided: {
    borderColor: 'var(--chip-user-border)',
    bgColor: 'var(--chip-user-bg)',
    textColor: 'var(--chip-user-text)',
    label: 'Уточнено вами',
    icon: '✎',
  },
  from_registry: {
    borderColor: 'var(--chip-auto-border)',
    bgColor: 'var(--chip-auto-bg)',
    textColor: 'var(--chip-auto-text)',
    label: 'Подтверждено по справочнику',
    icon: '✓',
  },
  auto_filled: {
    borderColor: 'var(--chip-auto-border)',
    bgColor: 'var(--chip-auto-bg)',
    textColor: 'var(--chip-auto-text)',
    label: 'Подставлено системой',
    icon: '⚙',
  },
  missing: {
    borderColor: 'var(--chip-missing-border)',
    bgColor: 'var(--chip-missing-bg)',
    textColor: 'var(--chip-missing-text)',
    label: 'Не заполнено',
    icon: '!',
  },
  left_blank: {
    borderColor: 'var(--chip-blank-border)',
    bgColor: 'var(--chip-blank-bg)',
    textColor: 'var(--chip-blank-text)',
    label: 'Будет помечено в документе',
    icon: '—',
  },
} as const;

export function RequisiteChip({
  requisite,
  onEdit,
  onLeaveBlank,
}: RequisiteChipProps) {
  const style = STATUS_STYLES[requisite.status];

  return (
    <div
      className="p-3 transition-all"
      style={{
        background: style.bgColor,
        border: `1px solid ${style.borderColor}`,
        borderLeft: `4px solid ${style.borderColor}`,
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold flex-shrink-0"
              style={{
                background: style.borderColor,
                color: '#fff',
              }}
            >
              {style.icon}
            </span>
            <span
              className="text-xs font-semibold"
              style={{ color: style.textColor }}
            >
              {style.label}
            </span>
          </div>
          <div
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
          >
            {requisite.label}
            {requisite.required && (
              <span className="ml-1 normal-case text-red-600">*</span>
            )}
          </div>
        </div>
      </div>

      {/* Значение */}
      {requisite.value && (
        <div
          className="text-sm mb-2 p-2 rounded"
          style={{
            background: 'var(--chip-value-bg)',
            color: 'var(--foreground)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
          }}
        >
          {requisite.value}
        </div>
      )}

      {/* Подсказки */}
      {requisite.status === 'auto_filled' && (
        <div
          className="text-xs mb-2"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Подставлено системой: текущая дата
        </div>
      )}

      {requisite.status === 'left_blank' && (
        <div
          className="text-xs mb-2"
          style={{ color: 'var(--muted-foreground)' }}
        >
          В документе останется пометка{' '}
          <code
            className="px-1 py-0.5 rounded"
            style={{
              background: 'var(--border)',
              fontSize: '0.75rem',
            }}
          >
            [{requisite.label}]
          </code>
        </div>
      )}

      {requisite.status === 'missing' && requisite.required && (
        <div
          className="text-xs mb-2"
          style={{ color: '#92400e' }}
        >
          В документе останется пометка{' '}
          <code
            className="px-1 py-0.5 rounded"
            style={{
              background: '#fde68a',
              fontSize: '0.75rem',
            }}
          >
            [{requisite.label}]
          </code>
        </div>
      )}

      {/* Кнопки действий */}
      <div className="flex gap-2 flex-wrap">
        <button
          type="button"
          onClick={onEdit}
          className="text-xs px-3 py-1.5 font-medium transition-all"
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            color: 'var(--foreground)',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border)';
          }}
        >
          {requisite.status === 'missing' ? 'Указать' : 'Изменить'}
        </button>

        {requisite.status === 'missing' && onLeaveBlank && (
          <button
            type="button"
            onClick={onLeaveBlank}
            className="text-xs px-3 py-1.5 font-medium transition-all"
            style={{
              background: 'var(--card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--muted-foreground)',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--muted-foreground)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)';
            }}
          >
            Оставить пустым
          </button>
        )}
      </div>
    </div>
  );
}
