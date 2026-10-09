import type { ReactNode } from "react";
import type { Workspace, Student } from "./types";
import { statusOf } from "./api";
export function Heading({ title, description, action }: { title: ReactNode; description: string; action?: ReactNode }) {
  return <div className="heading"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function Person({ student }: { student: Student }) {
  return <div className="person"><span className="avatar">{student.name.split(/\s+/).slice(0, 2).map((n) => n[0]).join("")}</span><div><strong>{student.name}</strong><small>{student.email}</small></div></div>;
}
export function WorkshopSelect({ data, workshopId, onChange }: { data: Workspace; workshopId: string; onChange: (id: string) => void }) {
  return <select aria-label="Select workshop" value={workshopId} onChange={(e) => onChange(e.target.value)}>{data.workshops.map((w) => <option key={w.id} value={w.id}>{w.title} · {w.date}</option>)}</select>;
}
export function Stats({ data, workshopId }: { data: Workspace; workshopId: string }) {
  const active = data.students.filter((s) => !s.archived);
  return <div className="stats">{[ ["Registered", active.length], ...["present", "absent", "unmarked"].map((status) => [status, active.filter((s) => statusOf(data, workshopId, s.id) === status).length]) ].map(([label, value]) => <div className="stat" key={label}><b>{value}</b><span>{label}</span></div>)}</div>;
}
export function MutationError({ error }: { error: Error | null }) { return error ? <p className="error" role="alert">{error.message}</p> : null; }
