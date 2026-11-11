"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/", label: "Roles" },
  { href: "/employers", label: "Employers" },
  { href: "/market", label: "Market" },
  { href: "/method", label: "Method" },
];

export function Mark({ size = 22 }: { size?: number }) {
  // Three rows of a timetable; the newest one carries the signal.
  return (
    <svg width={size} height={size} viewBox="0 0 22 22" aria-hidden="true">
      <rect x="1" y="3" width="4" height="4" rx="2" fill="var(--signal)" />
      <rect x="8" y="3" width="13" height="4" rx="1" fill="currentColor" />
      <rect x="1" y="9" width="4" height="4" rx="1" fill="currentColor" opacity="0.45" />
      <rect x="8" y="9" width="10" height="4" rx="1" fill="currentColor" opacity="0.45" />
      <rect x="1" y="15" width="4" height="4" rx="1" fill="currentColor" opacity="0.22" />
      <rect x="8" y="15" width="12" height="4" rx="1" fill="currentColor" opacity="0.22" />
    </svg>
  );
}

export function Header() {
  const path = usePathname();
  const current = (href: string) => (href === "/" ? path === "/" || path.startsWith("/role/") : path.startsWith(href));
  return (
    <header className="top">
      <div className="wrap top-in">
        <Link href="/" className="brand" aria-label="Intern Radar, home">
          <Mark />
          Intern Radar
        </Link>
        <nav className="nav" aria-label="Sections">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} aria-current={current(l.href) ? "page" : undefined}>
              {l.label}
            </Link>
          ))}
        </nav>
        <ThemeToggle />
      </div>
    </header>
  );
}
