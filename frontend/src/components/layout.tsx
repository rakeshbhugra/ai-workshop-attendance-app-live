/** App shell: nav, outlet, toasts. */

import { FileUp, LogOut, StickyNote } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router";
import { useLogout, useMe } from "@/features/auth/queries";
import { Toaster } from "./toaster";

const navItems = [
  { to: "/examples", label: "Notes", icon: StickyNote },
  { to: "/examples/files", label: "Files", icon: FileUp },
];

export function Layout() {
  const me = useMe();
  const logout = useLogout();
  const navigate = useNavigate();
  return (
    <div className="min-h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-3xl items-center gap-6 px-6 py-4">
          <span className="font-semibold tracking-tight">Attendance</span>
          <nav className="flex gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                // Keep Notes inactive while viewing the nested Files route.
                end={to === "/examples"}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors ${
                    isActive
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                  }`
                }
              >
                <Icon size={15} />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-500">
            <span className="hidden sm:inline">{me.data?.email}</span>
            <button
              type="button"
              onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/login", { replace: true }) })}
              className="flex items-center gap-1.5 rounded-md px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              <LogOut size={15} />
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-8">
        <Outlet />
      </main>

      <Toaster />
    </div>
  );
}
