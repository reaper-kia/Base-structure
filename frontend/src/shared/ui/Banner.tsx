import type { ReactNode } from 'react';

export type BannerLevel = 'info' | 'warning' | 'error';

const LEVEL_STYLES: Record<
  BannerLevel,
  { bg: string; border: string; color: string; icon: string }
> = {
  info: {
    bg: 'var(--banner-info-bg)',
    border: 'var(--banner-info-border)',
    color: 'var(--banner-info-text)',
    icon: 'ℹ',
  },
  warning: {
    bg: 'var(--banner-warn-bg)',
    border: 'var(--banner-warn-border)',
    color: 'var(--banner-warn-text)',
    icon: '⚠',
  },
  error: {
    bg: 'var(--banner-error-bg)',
    border: 'var(--banner-error-border)',
    color: 'var(--banner-error-text)',
    icon: '✕',
  },
};

interface BannerProps {
  level: BannerLevel;
  children: ReactNode;
}

export function Banner({ level, children }: BannerProps) {
  const style = LEVEL_STYLES[level];

  return (
    <div
      role={level === 'error' ? 'alert' : 'status'}
      className="px-4 py-3 text-sm flex items-start gap-2"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: 'var(--radius)',
        color: style.color,
      }}
    >
      <span aria-hidden="true" className="flex-shrink-0 font-bold">
        {style.icon}
      </span>
      <span>{children}</span>
    </div>
  );
}