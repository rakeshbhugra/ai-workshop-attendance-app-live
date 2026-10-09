import { BriefcaseBusiness, CalendarDays, CheckSquare, ChartColumn, Users, Menu } from "lucide-react";
import { useWorkspaceStore, type View } from "@/stores/workspace-store";
import { useMe, useLogout } from "@/features/auth/queries";
import { Toaster } from "@/components/toaster";
import { useQueryClient } from "@tanstack/react-query";
import { useWorkshops, useStudents, useSessions } from "./hooks";
import { WorkshopsPage } from "./workshops-page";
import { AttendancePanel } from "./attendance-panel";
import { StudentsPage } from "./student-roster";
import { CalendarPage } from "./calendar-page";
import { ReportsPage } from "./reports-page";
import { StudentDialog } from "./student-dialog";
import { QueryError, initials } from "./ui";
import { isMock, workspaceKeys } from "./api";
import { resetDemo } from "./mock-api";
import "./workspace.css";
const icons = { Workshops: BriefcaseBusiness, Attendance: CheckSquare, Students: Users, Calendar: CalendarDays, Reports: ChartColumn };
export function WorkspacePage() {
  const workshops = useWorkshops(); const students = useStudents(); const sessions = useSessions();
  const view = useWorkspaceStore((s) => s.view); const selected = useWorkspaceStore((s) => s.workshopId); const menuOpen = useWorkspaceStore((s) => s.menuOpen);
  const navigate = useWorkspaceStore((s) => s.navigate); const set = useWorkspaceStore((s) => s.set);
  const client = useQueryClient(); const me = useMe(); const logout = useLogout();
  const workshopId = selected || workshops.data?.[0]?.id || "";
  const name = isMock ? "Demo organizer" : me.data?.name || "Organizer";
  const pending = workshops.isPending || students.isPending || sessions.isPending;
  const failed = workshops.isError || students.isError || sessions.isError;
  return <div className="schoolnet-workspace" onKeyDown={(e) => { if (e.key === "Escape") set({ menuOpen: false }); }}><a className="skip-link" href="#workspace-main">Skip to content</a>
    {menuOpen && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => set({ menuOpen: false })} />}
    <aside className={`sidebar ${menuOpen ? "open" : ""}`} id="workspace-sidebar"><a className="brand" href="/" aria-label="Schoolnet Workshop Hub"><img src="/schoolnet/schoolnet-logo.png" alt="Schoolnet, Learning for life" /></a><div className="workspace"><span className="workspace-icon">W</span><div><strong>Workshop Hub</strong><small>Attendance management</small></div></div><div className="nav-label">WORKSPACE</div><nav>{(Object.keys(icons) as View[]).map((item) => { const Icon = icons[item]; return <button key={item} className={`nav-button ${view === item ? "active" : ""}`} aria-current={view === item ? "page" : undefined} onClick={() => navigate(item)}><Icon size={20} /><span>{item}</span>{item === "Workshops" && <span className="nav-count">{workshops.data?.filter((w) => w.active).length ?? 0}</span>}</button>; })}</nav><div className="sidebar-bottom"><span className="demo-dot" />{isMock ? "Mock workspace" : "Connected workspace"}<p>{isMock ? "Fictional data. Changes reset on reload." : "Attendance saved to your database."}</p>{isMock ? <button className="reset" onClick={() => { resetDemo(); void client.invalidateQueries({ queryKey: workspaceKeys.all }); }}>Reset demo data ↺</button> : <button className="reset" disabled={logout.isPending} onClick={() => logout.mutate(undefined, { onSuccess: () => { window.location.href = "/login"; } })}>Sign out</button>}</div><div className="profile"><span className="avatar">{initials(name)}</span><div><strong>{name}</strong><small>Workshop organizer</small></div></div></aside>
    <div className="shell"><header className="topbar"><button className="icon-button mobile-toggle" aria-label="Toggle navigation" aria-expanded={menuOpen} aria-controls="workspace-sidebar" onClick={() => set({ menuOpen: !menuOpen })}><Menu size={20} /></button><div className="breadcrumb">Workspace <span>/</span><strong>{view}</strong></div><div className="top-right"><span className="demo-pill">{isMock ? "DEMO" : "LIVE"}</span><span className="today">{new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}</span><span className="avatar small">{initials(name)}</span></div></header><main id="workspace-main" tabIndex={-1}>{pending ? <p role="status">Loading workshop workspace…</p> : failed ? <QueryError retry={() => { void workshops.refetch(); void students.refetch(); void sessions.refetch(); }} /> : <>
      {view === "Workshops" && <WorkshopsPage workshopId={workshopId} />}{view === "Attendance" && <AttendancePanel workshopId={workshopId} standalone />}{view === "Students" && <StudentsPage />}{view === "Calendar" && <CalendarPage />}{view === "Reports" && <ReportsPage />}
    </>}</main><footer className="app-footer">Schoolnet Workshop Hub <span>{isMock ? "Mock data · Local preview" : "Workshop attendance · Staff workspace"}</span></footer></div><StudentDialog /><Toaster />
  </div>;
}
