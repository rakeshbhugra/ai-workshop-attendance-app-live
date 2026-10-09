import { useRef, useState } from "react";
import { Archive, BarChart3, BriefcaseBusiness, CheckSquare, ChevronDown, ChevronRight, Landmark, Mail, Menu, Plus, UserCheck, Users, X } from "lucide-react";
import { useAttendanceWorkspace } from "./hooks";
import { RosterPage } from "./roster-page";
import { StudentsPage } from "./students-page";
import { WorkshopsPage } from "./workshops-page";
import { MailsPage } from "./mails-page";
import { AdminPage } from "./admin-page";
import type { Page } from "./types";
import "./attendance.css";
const labels: Record<Page, string> = { attendance: "Fill Attendance", classes: "Classes", add: "Add Student", active: "Active Students", archive: "Archive Students", admin: "Admin View", reports: "My Class Reports", mails: "Mails" };
const icons = { attendance: CheckSquare, classes: BriefcaseBusiness, add: Plus, active: UserCheck, archive: Archive, admin: Landmark, reports: BarChart3, mails: Mail };
export function AttendancePage() {
  const query = useAttendanceWorkspace();
  const [page, setPage] = useState<Page>("attendance");
  const [selectedWorkshop, setSelectedWorkshop] = useState("");
  const [groupOpen, setGroupOpen] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const main = useRef<HTMLElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const workshopId = selectedWorkshop || query.data?.workshops[0]?.id || "";
  function navigate(next: Page) {
    setPage(next); setMenuOpen(false);
    if (["add", "active", "archive"].includes(next)) setGroupOpen(true);
    main.current?.focus();
  }
  function navItem(next: Page) {
    const Icon = icons[next];
    return <button key={next} className={`nav-item ${page === next ? "active" : ""}`} aria-current={page === next ? "page" : undefined} onClick={() => navigate(next)}><Icon size={20} /><span>{labels[next]}</span>{!["add", "active", "archive"].includes(next) && <ChevronRight size={16} />}</button>;
  }
  return <div className="attendance-app" onKeyDown={(e) => { if (e.key === "Escape" && menuOpen) { setMenuOpen(false); toggle.current?.focus(); } }}>
    <a className="skip-link" href="#attendance-main">Skip to content</a>
    <header className="topbar"><div className="top-left"><button ref={toggle} className="mobile-toggle" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} aria-controls="attendance-sidebar" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</button><img className="logo" src="/schoolnet/schoolnet-logo.png" alt="Schoolnet: Learning for Life" /><span className="divider" /><span className="top-title">Attendance Management</span></div><div className="profile"><span className="avatar">RB</span><div><strong>Rakesh Bhugra</strong><small>Workshop organizer</small></div></div></header>
    <div className="demo"><strong>Demo workspace</strong> · Sample data, temporary changes. Mails supports drafts only.</div>
    {menuOpen && <button className="overlay" aria-label="Close navigation overlay" onClick={() => { setMenuOpen(false); toggle.current?.focus(); }} />}
    <div className="layout"><aside id="attendance-sidebar" className={`sidebar ${menuOpen ? "open" : ""}`} aria-label="Main navigation"><div className="module-title">Attendance Management</div><nav>{navItem("attendance")}{navItem("classes")}<button className="nav-item group" aria-expanded={groupOpen} aria-controls="student-subnav" onClick={() => setGroupOpen(!groupOpen)}><Users size={20} /><span>Student Details</span>{groupOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</button><div className="subnav" id="student-subnav" hidden={!groupOpen}>{navItem("add")}{navItem("active")}{navItem("archive")}</div>{navItem("admin")}{navItem("reports")}{navItem("mails")}</nav><div className="sidebar-bottom">Workshop attendance<br />Learning for Life</div></aside>
      <main id="attendance-main" className="main" tabIndex={-1} ref={main}><div className="breadcrumb">Attendance Management / {["add", "active", "archive"].includes(page) && "Student Details / "}<span>{labels[page]}</span></div>
        {query.isPending && <p role="status">Loading workshop workspace…</p>}
        {query.isError && <div className="panel"><p role="alert">The workspace could not be loaded.</p><button className="btn" onClick={() => void query.refetch()}>Try again</button></div>}
        {query.data && <div key={page}>
          {(page === "attendance" || page === "reports") && (workshopId ? <RosterPage workshopId={workshopId} onWorkshopChange={setSelectedWorkshop} report={page === "reports"} /> : <div className="panel"><p>No workshops yet.</p><button className="btn primary" onClick={() => navigate("classes")}>Create a workshop</button></div>)}
          {page === "classes" && <WorkshopsPage openWorkshop={(id) => { setSelectedWorkshop(id); navigate("attendance"); }} />}
          {(page === "add" || page === "active" || page === "archive") && <StudentsPage mode={page} navigate={navigate} />}
          {page === "admin" && <AdminPage />}
          {page === "mails" && (workshopId ? <MailsPage workshopId={workshopId} onWorkshopChange={setSelectedWorkshop} /> : <p>Create a workshop before preparing a draft.</p>)}
        </div>}
        <div className="note">Demo only · Changes reset when you reload this page.</div>
      </main></div>
  </div>;
}
