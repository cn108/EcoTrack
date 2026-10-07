"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, ArrowUpRight, BookOpenText, LayoutDashboard, LogOut, Leaf, Lightbulb, Route, Target } from "lucide-react";
import type { ReactNode } from "react";

import { useAuth } from "@/context/auth-context";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/activities", label: "Activities", icon: Activity },
  { href: "/trips", label: "Trips", icon: Route },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/about", label: "About", icon: BookOpenText },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="workspace-shell">
      <aside className="sidebar">
        <Link className="brand-lockup" href="/dashboard" aria-label="EcoTrack overview">
          <span className="brand-mark"><Leaf size={18} strokeWidth={2.4} /></span>
          <span className="brand-name">ecotrack<span>.</span></span>
        </Link>

        <div className="sidebar-label">Workspace</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`side-nav-link ${pathname === href ? "is-active" : ""}`}
              aria-current={pathname === href ? "page" : undefined}
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {pathname === href && <span className="nav-indicator" />}
            </Link>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <span className="sidebar-note-kicker">Your footprint</span>
            <p>Small changes, measured over time.</p>
            <ArrowUpRight size={17} aria-hidden="true" />
          </div>
          <div className="profile-row">
            <div className="avatar" aria-hidden="true">
              {user?.first_name?.[0]?.toUpperCase() ?? "E"}
            </div>
            <div className="profile-copy">
              <strong>{user?.first_name} {user?.last_name}</strong>
              <span>{user?.email}</span>
            </div>
            <button className="icon-button logout-button" onClick={handleLogout} aria-label="Log out" title="Log out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <div className="workspace-main">
        <header className="mobile-header">
          <Link className="brand-lockup" href="/dashboard">
            <span className="brand-mark"><Leaf size={17} /></span>
            <span className="brand-name">ecotrack<span>.</span></span>
          </Link>
          <nav aria-label="Mobile navigation">
            {navigation.map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href} aria-label={label} className={pathname === href ? "is-active" : ""}>
                <Icon size={19} />
              </Link>
            ))}
          </nav>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}