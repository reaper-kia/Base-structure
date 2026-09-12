import { useState } from 'react';
import type { RequisiteState } from '../../shared/api/types';
import { Banner } from '../../shared/ui/Banner';
import { RequisiteChip } from './RequisiteChip';
import { RequisiteEditor } from './RequisiteEditor';

interface RequisitesPanelProps {
  requisites: RequisiteState[];
  onPatch: (values: Record<string, string | null>) => Promise<void>;
  isPatching: boolean;
}

export function RequisitesPanel({
  requisites,
  onPatch,
  isPatching,
}: RequisitesPanelProps) {
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [patchError, setPatchError] = useState<string | null>(null);

  const handleSave = async (key: string, value: string | null) => {
    setPatchError(null);
    try {
      await onPatch({ [key]: value });
      setEditingKey(null);
    } catch (error) {
      setPatchError(
        error instanceof Error
          ? error.message
          : 'Не удалось сохранить реквизиты'
      );
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setPatchError(null);
  };

  const handleLeaveBlank = async (key: string) => {
    setPatchError(null);
    try {
      await onPatch({ [key]: null });
    } catch (error) {
      setPatchError(
        error instanceof Error
          ? error.message
          : 'Не удалось сохранить реквизиты'
      );
    }
  };

  return (
    <section
      className="p-4 md:p-5"
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="mb-4">
        <div
          className="text-xs font-semibold uppercase tracking-wider mb-1"
          style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
        >
          Реквизиты документа
        </div>
        <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>
          Проверьте и уточните данные документа. Жёлтые поля требуют вашего
          решения. Значения реквизитов подставляются в итоговый DOCX при
          формировании файла.
        </p>
      </div>

      {patchError && (
        <div className="mb-3">
          <Banner level="error">
            {patchError} Значение осталось в поле — попробуйте сохранить ещё
            раз.
          </Banner>
        </div>
      )}

      <div className="space-y-3">
        {requisites.map((req) =>
          editingKey === req.key ? (
            <RequisiteEditor
              key={req.key}
              requisite={req}
              onSave={(value) => handleSave(req.key, value)}
              onCancel={handleCancel}
            />
          ) : (
            <RequisiteChip
              key={req.key}
              requisite={req}
              onEdit={() => setEditingKey(req.key)}
              onLeaveBlank={
                req.status === 'missing'
                  ? () => handleLeaveBlank(req.key)
                  : undefined
              }
            />
          )
        )}
      </div>

      {isPatching && (
        <div
          className="mt-3 text-xs text-center"
          style={{ color: 'var(--muted-foreground)' }}
        >
          Сохранение…
        </div>
      )}
    </section>
  );
}