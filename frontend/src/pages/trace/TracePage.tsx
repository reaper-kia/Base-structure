import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../../shared/api';
import type { TraceEntry } from '../../shared/api/types';

export function TracePage() {
  const { id } = useParams<{ id: string }>();
  const [entries, setEntries] = useState<TraceEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    (async () => {
      try {
        const result = await api.getTrace(id);
        if (!cancelled) {
          setEntries(result);
          setExpanded(new Set(result.map((entry: TraceEntry) => entry.stage)));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Не удалось загрузить trace');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  const toggle = (stage: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(stage)) {
        next.delete(stage);
      } else {
        next.add(stage);
      }
      return next;
    });
  };

  if (!id) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <p style={{ color: 'var(--muted-foreground)' }}>Документ не указан.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
        <h1
          className="text-xl font-bold"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          Технический trace
        </h1>
        <Link
          to={`/documents/${id}`}
          className="text-xs underline"
          style={{ color: 'var(--muted-foreground)' }}
        >
          ← Вернуться к документу
        </Link>
      </div>

      <p className="text-xs mb-6" style={{ color: 'var(--muted-foreground)' }}>
        Документ: <code style={{ fontFamily: 'var(--font-mono)' }}>{id}</code>
      </p>

      {error && (
        <div
          className="p-3 mb-4 text-sm"
          style={{
            background: 'var(--banner-error-bg)',
            border: '1px solid var(--banner-error-border)',
            color: 'var(--banner-error-text)',
            borderRadius: 'var(--radius)',
          }}
        >
          {error}
        </div>
      )}

      {!entries && !error && (
        <p style={{ color: 'var(--muted-foreground)' }}>Загрузка…</p>
      )}

      {entries && (
        <ol className="space-y-2">
          {entries.map((entry: TraceEntry) => {
            const isOpen = expanded.has(entry.stage);
            return (
              <li
                key={entry.stage}
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  overflow: 'hidden',
                }}
              >
                <button
                  type="button"
                  onClick={() => toggle(entry.stage)}
                  className="w-full text-left px-4 py-3 flex items-center justify-between gap-3"
                  style={{ background: 'var(--card)' }}
                >
                  <span
                    className="text-sm font-semibold"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--foreground)',
                    }}
                  >
                    {entry.stage}
                  </span>
                  <span
                    aria-hidden="true"
                    style={{
                      transform: isOpen ? 'rotate(90deg)' : 'rotate(0)',
                      transition: 'transform 0.15s',
                      color: 'var(--muted-foreground)',
                    }}
                  >
                    ▶
                  </span>
                </button>

                {isOpen && (
                  <pre
                    className="px-4 pb-4 text-xs leading-relaxed overflow-auto"
                    style={{
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--foreground)',
                      maxHeight: 400,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {JSON.stringify(entry.payload, null, 2)}
                  </pre>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}