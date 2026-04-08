"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/ThemeToggle";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/register", label: "Register" },
  { href: "/attendance", label: "Attendance" },
  { href: "/admin", label: "Admin" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-panel/85 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 md:px-6">
        <div className="text-lg font-bold tracking-tight">AttendAI</div>

        <nav className="flex items-center gap-2">
          {links.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-full px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted hover:bg-white/10 dark:hover:bg-black/20"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
