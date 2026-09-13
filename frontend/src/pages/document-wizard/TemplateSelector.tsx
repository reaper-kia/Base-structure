import { useDocumentStore } from '../../shared/store/documentStore';
import type { Template } from '../../shared/api/types';

const TEMPLATE_META: Record<string, { font: string; accent: string }> = {
  classic: { font: 'Times New Roman', accent: 'var(--tpl-accent-ink)' },
  modern: { font: 'Calibri', accent: 'var(--tpl-accent-blue)' },
};

interface TemplateCardProps {
  template: Template;
  selected: boolean;
  onClick: () => void;
}

function TemplateCard({ template, selected, onClick }: TemplateCardProps) {
  const disabled = !template.available;
  const meta =
    TEMPLATE_META[template.id] ?? {
      font: 'Times New Roman',
      accent: 'var(--tpl-accent-ink)',
    };

  return (
    <button
      type="button"
      data-testid={`template-${template.id}`}
      onClick={() => !disabled && onClick()}
      disabled={disabled}
      aria-pressed={selected}
      aria-disabled={disabled}
      aria-label={
        disabled
          ? `Шаблон ${template.name} недоступен: ${template.description}`
          : `Выбрать шаблон оформления: ${template.name}`
      }
      className="text-left p-4 transition-all hover:shadow-md w-full"
      style={{
        background: selected ? 'var(--primary)' : 'var(--card)',
        border: selected ? '2px solid var(--accent)' : '2px solid var(--border)',
        borderRadius: 'var(--radius)',
        color: selected ? '#fff' : 'var(--foreground)',
        opacity: disabled ? 0.55 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
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
          {['Кому: ___________', 'От: ___________', 'Тема: ___________'].map(
            (line, i) => (
              <div
                key={line}
                className="h-1.5 rounded-sm"
                style={{
                  background: selected
                    ? 'rgba(255,255,255,0.25)'
                    : 'var(--tpl-preview-line)',
                  width: i === 2 ? '60%' : '80%',
                }}
              />
            )
          )}
          <div
            className="h-px mt-2"
            style={{
              background: selected
                ? 'rgba(255,255,255,0.15)'
                : 'var(--tpl-preview-line)',
            }}
          />
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-1 rounded-sm"
              style={{
                background: selected
                  ? 'rgba(255,255,255,0.18)'
                  : 'var(--tpl-preview-line-soft)',
                width: ['100%', '85%', '70%'][i],
              }}
            />
          ))}
        </div>
      </div>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div
            className="text-sm font-semibold"
            style={{
              fontFamily: 'var(--font-serif)',
              color: selected ? '#fff' : 'var(--foreground)',
            }}
          >
            {template.name}
          </div>
          <div
            className="text-xs mt-0.5"
            style={{
              color: selected ? 'rgba(255,255,255,0.65)' : 'var(--muted-foreground)',
            }}
          >
            {template.description}
          </div>
        </div>
        {selected && (
          <div
            className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs"
            style={{ background: 'var(--accent)', color: '#fff' }}
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
      <label
        className="block text-xs font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
      >
        Шаблон оформления
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {templates.map((template, index) => (
          <div
            key={template.id}
            className="anim-card"
            style={{ animationDelay: `${index * 80 + 120}ms` }}
          >
            <TemplateCard
              template={template}
              selected={templateId === template.id}
              onClick={() => setTemplateId(template.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}