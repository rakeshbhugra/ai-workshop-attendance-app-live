import { useState } from "react";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { useArchiveStudent, useStudents } from "./hooks";
import { Person, PageHead, QueryError } from "./ui";
import type { Student } from "./types";
export function StudentTable({ students, manage = false }: { students: Student[]; manage?: boolean }) {
  const archive = useArchiveStudent(); const [target, setTarget] = useState<Student | null>(null);
  return <><div className="table-scroll"><table><thead><tr><th>Student</th><th>Student ID</th><th>Institution</th><th>{manage ? "Manage" : "Status"}</th></tr></thead><tbody>{students.map((s) => <tr key={s.id}><td><Person student={s} /></td><td>{s.id}</td><td>{s.college}</td><td>{manage ? <button className="link-button danger-button" onClick={() => setTarget(s)}>Archive {s.name}</button> : <span className="badge green">Enrolled</span>}</td></tr>)}{!students.length && <tr><td colSpan={4} className="empty">No students found.</td></tr>}</tbody></table></div>
    {target && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="archive-title"><h2 id="archive-title">Archive {target.name}?</h2><p>This removes the student from active rosters and keeps historical attendance.</p><div className="dialog-actions"><button autoFocus className="button secondary" onClick={() => setTarget(null)}>Cancel</button><button className="button primary" disabled={archive.isPending} onClick={() => archive.mutate(target.id, { onSuccess: () => setTarget(null) })}>{archive.isPending ? "Archiving…" : "Confirm archive"}</button></div></section></div>}
  </>;
}
export function StudentSearch() {
  const search = useWorkspaceStore((s) => s.search); const set = useWorkspaceStore((s) => s.set);
  return <div className="search"><span aria-hidden="true">⌕</span><input value={search} onChange={(e) => set({ search: e.target.value })} placeholder="Search students or institutions" aria-label="Search students" /></div>;
}
export function StudentsPage() {
  const query = useStudents(); const search = useWorkspaceStore((s) => s.search); const set = useWorkspaceStore((s) => s.set);
  const students = (query.data ?? []).filter((s) => s.active && `${s.name} ${s.id} ${s.college}`.toLowerCase().includes(search.toLowerCase()));
  return <><PageHead title="Students" description="A shared roster for all your learning experiences." action={<button className="button primary" onClick={() => set({ studentDialog: true })}>+ Add student</button>} /><section className="panel"><div className="toolbar"><StudentSearch /><span className="badge">{students.length} active students</span></div>{query.isPending ? <p role="status">Loading students…</p> : query.isError ? <QueryError retry={() => void query.refetch()} /> : <StudentTable students={students} manage />}</section></>;
}
