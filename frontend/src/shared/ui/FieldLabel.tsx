import type { ReactNode } from 'react';

export function FieldLabel({ children }: { children: ReactNode }) {
  return (
    <label
      className="block text-xs font-semibold uppercase tracking-widest mb-2"
      style={{ color: 'var(--muted-foreground)', letterSpacing: '0.1em' }}
    >
      {children}
    </label>
  );
}