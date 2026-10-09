import { useState } from "react";
import { Download } from "lucide-react";
import { useAttendanceWorkspace, useMarkAttendance } from "./hooks";
import { statusOf } from "./api";
import { Heading, Person, Stats, WorkshopSelect, MutationError } from "./ui";
import type { AttendanceStatus, Workspace } from "./types";

function exportCsv(data: Workspace, workshopId: string) {
  const workshop = data.workshops.find((w) => w.id === workshopId);
  if (!workshop) return;
  // Neutralize spreadsheet formulas as well as quoting commas and newlines.
  const cell = (value: string) => '"' + (/^[=+@\-\t\r]/.test(value) ? "'" : "") + value.replaceAll('"', '""') + '"';
  const rows = [["Workshop", "Date", "Name", "Email", "Attendance"], ...data.students.filter((s) => !s.archived).map((s) => [workshop.title, workshop.date, s.name, s.email, statusOf(data, workshopId, s.id)])];
  const url = URL.createObjectURL(new Blob([rows.map((r) => r.map(cell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8;" }));
  const link = document.createElement("a");
  link.href = url; link.download = "workshop-attendance.csv"; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function RosterPage({ workshopId, onWorkshopChange, report = false }: { workshopId: string; onWorkshopChange: (id: string) => void; report?: boolean }) {
  const { data } = useAttendanceWorkspace();
  const mark = useMarkAttendance();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<AttendanceStatus | "all">("all");
  if (!data) return null;
  const active = data.students.filter((s) => !s.archived);
  const visible = active.filter((s) => (s.name + " " + s.email).toLowerCase().includes(search.toLowerCase()) && (filter === "all" || statusOf(data, workshopId, s.id) === filter));
  const workshop = data.workshops.find((w) => w.id === workshopId);
  return <>
    <Heading title={report ? <>My Class <em>Reports</em></> : <>Fill <em>Attendance</em></>} description={report ? "Review attendance totals and download the full active roster." : "A clear record of everyone in your workshop."} action={<button className="btn primary" onClick={() => exportCsv(data, workshopId)}><Download size={18} /> Export CSV</button>} />
    <div className="banner"><div><span className="tag">Workshop {report ? "report" : "attendance"}</span><h2>{workshop?.title}</h2><p>Mark students present or absent. Tap a selected status to clear it.</p></div><WorkshopSelect data={data} workshopId={workshopId} onChange={onWorkshopChange} /></div>
    <Stats data={data} workshopId={workshopId} />
    <div className="panel">
      <div className="panel-head"><h2>{report ? "Attendance report" : "Student roster"}</h2><span>{visible.length} students shown</span></div>
      <div className="toolbar"><input type="search" className="search" aria-label="Search students" placeholder="Search student name or email" value={search} onChange={(e) => setSearch(e.target.value)} /><div className="filters">{(["all", "present", "absent", "unmarked"] as const).map((f) => <button key={f} className={`filter ${filter === f ? "active" : ""}`} aria-pressed={filter === f} onClick={() => setFilter(f)}>{f}</button>)}</div></div>
      <MutationError error={mark.error} />
      <div className="table-wrap"><table><thead><tr><th>Student</th><th>Status</th>{!report && <th>Attendance</th>}</tr></thead><tbody>{visible.map((student) => {
        const status = statusOf(data, workshopId, student.id);
        return <tr key={student.id}><td><Person student={student} /></td><td><span className={`badge ${status}`}>{status}</span></td>{!report && <td className="actions">{(["present", "absent"] as const).map((value) => <button key={value} data-status={value} disabled={mark.isPending} className={`mark ${status === value ? "selected" : ""}`} aria-label={`Mark ${student.name} ${value}`} aria-pressed={status === value} onClick={() => mark.mutate({ workshopId, studentId: student.id, status: status === value ? "unmarked" : value })}>{value === "present" ? "✓ Present" : "× Absent"}</button>)}</td>}</tr>;
      })}{visible.length === 0 && <tr><td colSpan={report ? 2 : 3} className="empty">No students found.</td></tr>}</tbody></table></div>
    </div>
    {report && <p>{active.filter((s) => statusOf(data, workshopId, s.id) === "unmarked").length} students remain unmarked. CSV includes every active student, regardless of filters.</p>}
  </>;
}
