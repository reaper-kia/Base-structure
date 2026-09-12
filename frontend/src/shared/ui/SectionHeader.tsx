interface SectionHeaderProps {
  step: number;
  title: string;
  hint: string;
}

export function SectionHeader({ step, title, hint }: SectionHeaderProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
          style={{ background: 'var(--primary)', color: '#fff' }}
        >
          {step}
        </div>
        <h2
          className="text-lg font-bold"
          style={{ fontFamily: 'var(--font-serif)', color: 'var(--foreground)' }}
        >
          {title}
        </h2>
      </div>
      <p className="text-sm ml-8" style={{ color: 'var(--muted-foreground)' }}>
        {hint}
      </p>
      <div className="h-px w-20 ml-8 mt-2" style={{ background: 'var(--accent)' }} />
    </div>
  );
}