import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section className="text-center py-16">
      <div
        className="text-5xl font-bold mb-3"
        style={{ color: 'var(--muted-foreground)' }}
      >
        404
      </div>
      <h1 className="text-xl font-semibold mb-2">Страница не найдена</h1>
      <p className="text-sm mb-6" style={{ color: 'var(--muted-foreground)' }}>
        Возможно, ссылка устарела или адрес введён с ошибкой.
      </p>
      <Link
        to="/"
        className="inline-block px-5 py-2.5 text-sm font-semibold"
        style={{
          background: 'var(--primary)',
          color: '#fff',
          borderRadius: 'var(--radius)',
        }}
      >
        Вернуться к созданию документа
      </Link>
    </section>
  );
}
