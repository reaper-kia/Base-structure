import { useDocumentStore } from '../../shared/store/documentStore';
import { DocTypeIcon } from '../../shared/ui/DocTypeIcon';

export function DocTypeSelector() {
  const docTypes = useDocumentStore((state) => state.docTypes);
  const docType = useDocumentStore((state) => state.docType);
  const setDocType = useDocumentStore((state) => state.setDocType);

  return (
    <div className="mb-6">
      <label
        className="block text-xs font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
      >
        Тип документа
      </label>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {docTypes.map((type, index) => {
          const selected = docType === type.id;
          return (
            <button
              key={type.id}
              type="button"
              data-testid={`doc-type-${type.id}`}
              onClick={() => setDocType(type.id)}
              aria-pressed={selected}
              aria-label={`Выбрать тип документа: ${type.name}`}
              className="anim-card text-left p-3 transition-all hover:shadow-md"
              style={{
                animationDelay: `${index * 60}ms`,
                background: selected ? 'var(--primary)' : 'var(--card)',
                border: selected ? '2px solid var(--primary)' : '2px solid var(--border)',
                borderRadius: 'var(--radius)',
                color: selected ? '#fff' : 'var(--foreground)',
              }}
            >
              <div
                className="mb-3 flex items-center justify-center w-11 h-11 rounded-xl"
                style={{
                  background: selected ? 'rgba(255,255,255,0.15)' : 'var(--muted)',
                  border: selected
                    ? '1.5px solid rgba(255,255,255,0.25)'
                    : '1.5px solid var(--border)',
                }}
              >
                <DocTypeIcon typeId={type.id} color={selected ? '#fff' : 'var(--primary)'} />
              </div>
              <div className="text-sm font-semibold leading-tight mb-1">{type.name}</div>
              <div
                className="text-xs leading-tight"
                style={{ color: selected ? 'rgba(255,255,255,0.6)' : 'var(--muted-foreground)' }}
              >
                {type.description}
              </div>
              {selected && (
                <div
                  className="mt-2 flex items-center gap-1 text-xs font-semibold"
                  style={{ color: '#0DC268' }}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                    <circle cx="6" cy="6" r="6" fill="#0DC268" />
                    <path
                      d="M3.5 6l1.8 1.8L8.5 4.5"
                      stroke="white"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  Выбрано
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}