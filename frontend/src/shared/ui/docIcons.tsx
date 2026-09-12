export type DocIconId = 'memo' | 'report' | 'reference' | 'letter';

interface DocIconProps {
  id: DocIconId;
  color: string;
}

export function DocIcon({ id, color }: DocIconProps) {
  if (id === 'memo') {
    return (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="4" y="2" width="16" height="20" rx="2" stroke={color} strokeWidth="1.6" fill="none" />
        <rect x="8" y="2" width="8" height="4" rx="1" fill={color} fillOpacity="0.15" stroke={color} strokeWidth="1.4" />
        <line x1="8" y1="11" x2="16" y2="11" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="8" y1="14.5" x2="16" y2="14.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="8" y1="18" x2="13" y2="18" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="21" cy="21" r="5" fill={color} />
        <path d="M19 21l1.5 1.5L23 19.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (id === 'report') {
    return (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="4" y="2" width="16" height="20" rx="2" stroke={color} strokeWidth="1.6" fill="none" />
        <line x1="8" y1="8" x2="16" y2="8" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="8" y1="11.5" x2="16" y2="11.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="8" y1="15" x2="16" y2="15" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="8" y1="18.5" x2="12" y2="18.5" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <path d="M17 20l2-2 2 1 2-3" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (id === 'reference') {
    return (
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <rect x="4" y="2" width="16" height="20" rx="2" stroke={color} strokeWidth="1.6" fill="none" />
        <circle cx="12" cy="9" r="2.5" stroke={color} strokeWidth="1.4" fill="none" />
        <path d="M7 18c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke={color} strokeWidth="1.4" strokeLinecap="round" fill="none" />
        <line x1="21" y1="6" x2="25" y2="6" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="22" y1="9" x2="25" y2="9" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
        <line x1="23" y1="12" x2="25" y2="12" stroke={color} strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <rect x="3" y="6" width="22" height="16" rx="2" stroke={color} strokeWidth="1.6" fill="none" />
      <path d="M3 8l11 8 11-8" stroke={color} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <line x1="3" y1="19" x2="9" y2="14" stroke={color} strokeWidth="1.2" strokeLinecap="round" />
      <line x1="25" y1="19" x2="19" y2="14" stroke={color} strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}