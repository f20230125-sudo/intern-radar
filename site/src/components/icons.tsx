const base = { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true } as const;

export const Chevron = ({ className }: { className?: string }) => (
  <svg {...base} className={className}>
    <path d="M3.5 6l4.5 4.5L12.5 6" />
  </svg>
);
export const Search = () => (
  <svg {...base}>
    <circle cx="7" cy="7" r="4.5" />
    <path d="M10.5 10.5L14 14" />
  </svg>
);
export const Lock = () => (
  <svg {...base} width={13} height={13}>
    <rect x="3" y="7" width="10" height="7" rx="1.2" />
    <path d="M5.2 7V5a2.8 2.8 0 0 1 5.6 0v2" />
  </svg>
);
export const Out = () => (
  <svg {...base} width={14} height={14}>
    <path d="M6 3H3v10h10v-3M9 3h4v4M13 3L7.5 8.5" />
  </svg>
);
export const Star = ({ on }: { on: boolean }) => (
  <svg {...base} fill={on ? "currentColor" : "none"}>
    <path d="M8 1.8l1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z" />
  </svg>
);
export const Sliders = () => (
  <svg {...base}>
    <path d="M2 4.5h7M12 4.5h2M2 11.5h2M7 11.5h7" />
    <circle cx="10.5" cy="4.5" r="1.6" />
    <circle cx="5.5" cy="11.5" r="1.6" />
  </svg>
);
export const Link2 = () => (
  <svg {...base} width={14} height={14}>
    <path d="M6.5 9.5a3 3 0 0 0 4.2 0l2-2a3 3 0 0 0-4.2-4.2l-.8.8M9.5 6.5a3 3 0 0 0-4.2 0l-2 2a3 3 0 0 0 4.2 4.2l.8-.8" />
  </svg>
);
