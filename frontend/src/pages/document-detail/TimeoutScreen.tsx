interface TimeoutScreenProps {
  onRetry: () => void;
}

export function TimeoutScreen({ onRetry }: TimeoutScreenProps) {
  return (
    <section style={{ padding: '24px 0', textAlign: 'center' }}>
      <h2 style={{ fontSize: '22px', marginBottom: '12px' }}>
        Обработка заняла слишком много времени
      </h2>
      <p style={{ color: '#666', marginBottom: '24px' }}>
        Мы ждали две минуты, но документ ещё не готов. Попробуйте повторить
        обработку.
      </p>
      <button
        type="button"
        onClick={onRetry}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
        }}
      >
        Повторить
      </button>
    </section>
  );
}