import { ReactNode } from 'react';

const P = (d: string) => <path d={d} />;

const ICONS: Record<string, ReactNode> = {
  grid: (<><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></>),
  book: (<>{P('M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z')}{P('M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z')}</>),
  calendar: (<><rect x="3" y="4" width="18" height="18" rx="2" />{P('M16 2v4M8 2v4M3 10h18')}</>),
  file: (<>{P('M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z')}{P('M14 2v6h6M16 13H8M16 17H8M10 9H8')}</>),
  bookmark: P('m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z'),
  message: P('M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'),
  award: (<><circle cx="12" cy="8" r="6" />{P('M15.477 12.89 17 22l-5-3-5 3 1.523-9.11')}</>),
  users: (<>{P('M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2')}<circle cx="9" cy="7" r="4" />{P('M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75')}</>),
  user: (<>{P('M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2')}<circle cx="12" cy="7" r="4" /></>),
  edit: (<>{P('M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7')}{P('M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4z')}</>),
  alert: (<>{P('M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z')}{P('M12 9v4M12 17h.01')}</>),
  clock: (<><circle cx="12" cy="12" r="10" />{P('M12 6v6l4 2')}</>),
  bell: (<>{P('M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9')}{P('M10.3 21a1.94 1.94 0 0 0 3.4 0')}</>),
  logout: (<>{P('M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4')}{P('m16 17 5-5-5-5M21 12H9')}</>),
  eye: (<>{P('M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z')}<circle cx="12" cy="12" r="3" /></>),
  eyeOff: (<>{P('M9.88 9.88a3 3 0 1 0 4.24 4.24')}{P('M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68')}{P('M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61')}{P('m2 2 20 20')}</>),
  lock: (<><rect x="3" y="11" width="18" height="11" rx="2" />{P('M7 11V7a5 5 0 0 1 10 0v4')}</>),
  cap: (<>{P('M22 10 12 5 2 10l10 5z')}{P('M6 12v5c3 3 9 3 12 0v-5')}</>),
  down: P('m6 9 6 6 6-6'),
  info: (<><circle cx="12" cy="12" r="10" />{P('M12 16v-4M12 8h.01')}</>),
  check: P('M20 6 9 17l-5-5'),
  checkCircle: (<>{P('M22 11.08V12a10 10 0 1 1-5.93-9.14')}{P('m22 4-10 10.01-3-3')}</>),
  card: (<><rect x="2" y="5" width="20" height="14" rx="2" />{P('M2 10h20')}</>),
  plus: P('M12 5v14M5 12h14'),
  trash: (<>{P('M3 6h18')}{P('M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6')}{P('M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2')}</>),
  search: (<><circle cx="11" cy="11" r="8" />{P('m21 21-4.3-4.3')}</>),
  x: P('M18 6 6 18M6 6l12 12'),
  more: (<><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></>),
  chart: (<>{P('M3 3v18h18')}{P('M7 15l4-4 3 3 5-6')}</>),
  moon: P('M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'),
  sun: (<><circle cx="12" cy="12" r="4" />{P('M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41')}</>),
  hourglass: (<>{P('M5 22h14M5 2h14')}{P('M17 22v-4.17a2 2 0 0 0-.59-1.42L12 12l-4.41 4.41A2 2 0 0 0 7 17.83V22M7 2v4.17a2 2 0 0 0 .59 1.42L12 12l4.41-4.41A2 2 0 0 0 17 6.17V2')}</>),
};

export type IconName = keyof typeof ICONS;

export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {ICONS[name]}
    </svg>
  );
}
