import type { ReactNode } from 'react';

interface PrimaryButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'accent' | 'ghost';
  'aria-label'?: string;
  type?: 'button' | 'submit' | 'reset';
}

export function PrimaryButton({
  children,
  onClick,
  disabled,
  variant = 'primary',
  'aria-label': ariaLabel,
  type = 'button',
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
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-disabled={disabled}
      className="px-7 py-3 text-sm font-semibold transition-all hover:brightness-110 active:brightness-95"
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