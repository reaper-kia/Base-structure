import { useDocumentStore } from '../../shared/store/documentStore';
import { FieldLabel } from '../../shared/ui/FieldLabel';
import type { Template } from '../../shared/api/types';

const TEMPLATE_META: Record<string, { font: string; accent: string }> = {
  classic: { font: 'Times New Roman', accent: '#1a1a1a' },
  modern: { font: 'Calibri', accent: '#0B4FCA' },
};

interface TemplateCardProps {
  template: Template;
  selected: boolean;
  onClick: () => void;
}

function TemplateCard({ template, selected, onClick }: TemplateCardProps) {
  const meta = TEMPLATE_META[template.id] ?? {
    font: 'Times New Roman',
    accent: '#1a1a1a',
  };
  const disabled = !template.available;

  return (
    <button
      type="button"
      data-testid={`template-${template.id}`}
      onClick={() => !disabled && onClick()}
      disabled={disabled}
      aria-pressed={selected}
      aria-disabled={disabled}
      className="text-left p-4 transition-all"
      style={{
        background: selected ? 'var(--primary)' : 'var(--card)',
        border: selected ? '2px solid var(--accent)' : '2px solid var(--border)',
        borderRadius: 'var(--radius)',
        color: selected ? '#fff' : 'var(--foreground)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.55 : 1,
      }}
    >
      <div
        className="mb-3 p-3 rounded"
        style={{
          background: selected ? 'rgba(255,255,255,0.12)' : 'var(--muted)',
          minHeight: 80,
        }}
      >
        <div
          className="mb-1.5"
          style={{ borderBottom: `2px solid ${meta.accent}`, paddingBottom: 4 }}
        >
          <span
            className="text-xs font-bold"
            style={{
              color: meta.accent,
              fontFamily: meta.font,
              opacity: selected ? 1 : 0.9,
            }}
          >
            ДОКУМЕНТ
          </span>
        </div>
        <div className="space-y-1">
          {['80%', '80%', '60%'].map((width, index) => (
            <div
              key={index}
              className="h-1.5 rounded-sm"
              style={{
                background: selected
                  ? 'rgba(255,255,255,0.25)'
                  : 'var(--border)',
                width,
              }}
            />
          ))}
          <div
            className="h-px mt-2"
            style={{
              background: selected
                ? 'rgba(255,255,255,0.15)'
                : 'var(--border)',
            }}
          />
          {['100%', '85%', '70%'].map((width, index) => (
            <div
              key={index}
              className="h-1 rounded-sm"
              style={{
                background: selected
                  ? 'rgba(255,255,255,0.18)'
                  : 'var(--secondary)',
                width,
              }}
            />
          ))}
        </div>
      </div>

      <div className="flex items-start justify-between gap-2">
        <div>
          <div
            className="text-sm font-semibold"
            style={{ fontFamily: 'var(--font-serif)' }}
          >
            {template.name}
          </div>
          <div
            className="text-xs mt-0.5"
            style={{
              color: selected
                ? 'rgba(255,255,255,0.65)'
                : 'var(--muted-foreground)',
            }}
          >
            {template.description}
          </div>
          {disabled && (
            <div
              className="text-xs mt-1 font-semibold"
              style={{ color: '#dc2626' }}
            >
              Шаблон недоступен: папка повреждена
            </div>
          )}
        </div>
        {selected && (
          <div
            className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs"
            style={{ background: 'var(--accent)' }}
          >
            ✓
          </div>
        )}
      </div>
    </button>
  );
}

export function TemplateSelector() {
  const templates = useDocumentStore((state) => state.templates);
  const templateId = useDocumentStore((state) => state.templateId);
  const setTemplateId = useDocumentStore((state) => state.setTemplateId);

  return (
    <div className="mb-6">
      <FieldLabel>Как он должен выглядеть — шрифты, поля, колонтитулы</FieldLabel>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {templates.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            selected={templateId === template.id}
            onClick={() => setTemplateId(template.id)}
          />
        ))}
      </div>
    </div>
  );
}