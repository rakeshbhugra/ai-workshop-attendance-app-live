import type { ReactNode } from "react";
import type { Record, Student } from "./types";
export const initials = (name: string) => name.split(" ").map((word) => word[0]).slice(0, 2).join("");
export const dateLabel = (date: string) => new Date(`${date}T12:00:00`).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
export function duration(record: Record) {
  if (!record.checkIn || !record.checkOut) return null;
  const toMinutes = (time: string) => { const [h = 0, m = 0] = time.split(":").map(Number); return h * 60 + m; };
  const minutes = toMinutes(record.checkOut) - toMinutes(record.checkIn);
  return minutes < 0 ? null : minutes;
}
export function summarize(records: Record[]) {
  const present = records.filter((r) => r.status === "present").length;
  const absent = records.filter((r) => r.status === "absent").length;
  return { present, absent, unmarked: records.length - present - absent, rate: present + absent ? `${Math.round(present / (present + absent) * 100)}%` : "No data", hours: records.reduce((n, r) => n + (duration(r) ?? 0), 0) / 60 };
}
export function Metric({ label, value, note }: { label: string; value: ReactNode; note: string }) {
  return <div className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}
export function PageHead({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="page-head"><div><div className="eyebrow">Learning together</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function Person({ student }: { student: Student }) {
  return <div className="student-cell"><span className="avatar">{initials(student.name)}</span><div><strong>{student.name}</strong><small>{student.email}</small></div></div>;
}
export function QueryError({ retry }: { retry: () => void }) { return <div className="notice" role="alert">We could not load this data. <button className="button secondary" onClick={retry}>Try again</button></div>; }
