import type { ReactNode } from 'react';

interface PrimaryButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'accent' | 'ghost';
}

export function PrimaryButton({
  children,
  onClick,
  disabled,
  variant = 'primary',
}: PrimaryButtonProps) {
  const background = disabled
    ? 'var(--muted)'
    : variant === 'accent'
      ? 'var(--accent)'
      : variant === 'ghost'
        ? 'var(--card)'
        : 'var(--primary)';

  const color = disabled
    ? 'var(--muted-foreground)'
    : variant === 'ghost'
      ? 'var(--foreground)'
      : '#fff';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="px-7 py-3 text-sm font-semibold transition-all"
      style={{
        background,
        color,
        borderRadius: 'var(--radius)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        letterSpacing: '0.04em',
        border: variant === 'ghost' ? '1px solid var(--border)' : 'none',
      }}
    >
      {children}
    </button>
  );
}