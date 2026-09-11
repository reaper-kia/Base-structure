import { useDocumentStore } from '../../shared/store/documentStore';

export function DocTypeSelector() {
  const docTypes = useDocumentStore((state) => state.docTypes);
  const docType = useDocumentStore((state) => state.docType);
  const setDocType = useDocumentStore((state) => state.setDocType);

  return (
    <section style={{ marginBottom: '32px' }}>
      <h2 style={{ margin: '0 0 4px 0', fontSize: '20px' }}>
        Что за документ
      </h2>
      <p style={{ margin: '0 0 12px 0', color: '#666', fontSize: '14px' }}>
        Выберите тип — он определяет структуру и обязательные поля
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: '12px',
        }}
      >
        {docTypes.map((type) => {
          const isSelected = docType === type.id;
          return (
            <div
              key={type.id}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              onClick={() => setDocType(type.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setDocType(type.id);
                }
              }}
              style={{
                padding: '16px',
                border: isSelected ? '2px solid #007bff' : '1px solid #ddd',
                borderRadius: '8px',
                cursor: 'pointer',
                backgroundColor: isSelected ? '#e7f3ff' : 'white',
                transition: 'border-color 0.15s, background-color 0.15s',
              }}
            >
              <h3 style={{ margin: '0 0 6px 0', fontSize: '16px' }}>
                {type.name}
              </h3>
              <p style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#666' }}>
                {type.description}
              </p>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#888' }}>
                {type.requisites
                  .filter((r) => r.required)
                  .map((r) => (
                    <li key={r.key}>{r.label}</li>
                  ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}