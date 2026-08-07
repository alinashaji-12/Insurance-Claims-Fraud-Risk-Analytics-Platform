import Link from "next/link";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/upload", label: "Bulk Upload" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#e8f4f2_0%,_#f4f7f9_45%,_#eef1f4_100%)] text-slate-900">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link href="/" className="group">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              ClaimGuard AI
            </p>
            <p className="text-sm text-slate-500 group-hover:text-slate-700">
              Insurance fraud & risk analytics
            </p>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-teal-50 hover:text-teal-900"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
