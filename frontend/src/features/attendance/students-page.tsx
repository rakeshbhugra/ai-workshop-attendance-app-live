import { useState } from "react";
import { useAttendanceWorkspace, useAddStudent, useArchiveStudent } from "./hooks";
import { Heading, Person, MutationError } from "./ui";
import type { Page } from "./types";
export function StudentsPage({ mode, navigate }: { mode: "add" | "active" | "archive"; navigate: (page: Page) => void }) {
  const { data } = useAttendanceWorkspace();
  const add = useAddStudent();
  const archive = useArchiveStudent();
  const [search, setSearch] = useState("");
  if (!data) return null;
  if (mode === "add") return <>
    <Heading title={<>Add <em>Student</em></>} description="Add a student to the active roster for workshop attendance." />
    <form className="panel" onSubmit={(e) => { e.preventDefault(); const form = new FormData(e.currentTarget); add.mutate({ name: String(form.get("name")), email: String(form.get("email")) }, { onSuccess: () => navigate("active") }); }}>
      <h2>Student details</h2><div className="fields"><label>Full name<input name="name" required maxLength={100} placeholder="e.g. Aarav Mehta" /></label><label>Email address<input name="email" type="email" required maxLength={254} placeholder="e.g. aarav@example.com" /></label></div>
      <MutationError error={add.error} /><p>New students start as Unmarked. Email addresses must be unique across active and archived students.</p>
      <div className="form-actions"><button className="btn primary" disabled={add.isPending}>{add.isPending ? "Adding…" : "Add Student"}</button><button className="btn" type="button" onClick={() => navigate("active")}>View active students</button></div>
    </form>
  </>;
  const archived = mode === "archive";
  const visible = data.students.filter((s) => s.archived === archived && (s.name + " " + s.email).toLowerCase().includes(search.toLowerCase()));
  return <>
    <Heading title={archived ? <>Archive <em>Students</em></> : <>Active <em>Students</em></>} description={archived ? "Archived students are excluded from attendance. Restore them when needed." : "Manage the students available for workshop attendance."} action={<button className="btn primary" onClick={() => navigate("add")}>＋ Add Student</button>} />
    <div className="panel"><div className="toolbar"><input className="search" type="search" aria-label="Search students" placeholder="Search student name or email" value={search} onChange={(e) => setSearch(e.target.value)} /><span>{visible.length} students</span></div><MutationError error={archive.error} />
      <div className="table-wrap"><table><thead><tr><th>Student</th><th>Roster status</th><th>Action</th></tr></thead><tbody>{visible.map((s) => <tr key={s.id}><td><Person student={s} /></td><td><span className={`badge ${archived ? "" : "present"}`}>{archived ? "Archived" : "Active"}</span></td><td><button className="row-action" disabled={archive.isPending} aria-label={`${archived ? "Restore" : "Archive"} ${s.name}`} onClick={() => archive.mutate({ id: s.id, archived: !archived })}>{archived ? "Restore student" : "Archive student"}</button></td></tr>)}{visible.length === 0 && <tr><td colSpan={3} className="empty">No students found.</td></tr>}</tbody></table></div>
    </div>
  </>;
}
