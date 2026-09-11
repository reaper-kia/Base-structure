import { useDocumentStore } from '../../shared/store/documentStore';

export function TemplateSelector() {
  const templates = useDocumentStore((state) => state.templates);
  const templateId = useDocumentStore((state) => state.templateId);
  const setTemplateId = useDocumentStore((state) => state.setTemplateId);

  return (
    <section style={{ marginBottom: '32px' }}>
      <h2 style={{ margin: '0 0 4px 0', fontSize: '20px' }}>
        Как он должен выглядеть
      </h2>
      <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
        Выберите оформление — шрифты, поля, колонтитулы
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: '12px',
        }}
      >
        {templates.map((template) => {
          const isSelected = templateId === template.id;
          const isAvailable = template.available;

          return (
            <div
              key={template.id}
              role="button"
              tabIndex={isAvailable ? 0 : -1}
              aria-pressed={isSelected}
              aria-disabled={!isAvailable}
              onClick={() => isAvailable && setTemplateId(template.id)}
              onKeyDown={(e) => {
                if (isAvailable && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault();
                  setTemplateId(template.id);
                }
              }}
              style={{
                padding: '16px',
                border: isSelected ? '2px solid #007bff' : '1px solid #ddd',
                borderRadius: '8px',
                cursor: isAvailable ? 'pointer' : 'not-allowed',
                backgroundColor: isSelected
                  ? '#e7f3ff'
                  : isAvailable
                    ? 'white'
                    : '#f5f5f5',
                opacity: isAvailable ? 1 : 0.6,
                transition: 'border-color 0.15s, background-color 0.15s',
              }}
            >
              {/* Превью-картинка (заглушка, пока UI не даст реальные PNG) */}
              <div
                style={{
                  width: '100%',
                  height: '120px',
                  backgroundColor: '#e9ecef',
                  borderRadius: '4px',
                  marginBottom: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  color: '#999',
                  overflow: 'hidden',
                }}
              >
                {isAvailable ? (
                  <img
                    src={template.preview_url}
                    alt={`Превью: ${template.name}`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                ) : null}
                <span style={{ position: 'absolute' }}>
                  {isAvailable ? '' : 'Недоступен'}
                </span>
              </div>

              <h3 style={{ margin: '0 0 6px 0', fontSize: '16px' }}>
                {template.name}
              </h3>
              <p style={{ margin: 0, fontSize: '13px', color: '#666' }}>
                {template.description}
              </p>

              {!isAvailable && (
                <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#dc3545' }}>
                  Шаблон недоступен
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}