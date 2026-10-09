import { useWorkspaceStore } from "@/stores/workspace-store";
import { useSessions, useWorkshops } from "./hooks";
import { PageHead, dateLabel } from "./ui";
export function CalendarPage() {
  const month = useWorkspaceStore((s) => s.month); const year = useWorkspaceStore((s) => s.year); const set = useWorkspaceStore((s) => s.set); const open = useWorkspaceStore((s) => s.openSession);
  const sessions = useSessions().data ?? []; const workshops = useWorkshops().data ?? [];
  const first = new Date(year, month, 1); const padding = (first.getDay() + 6) % 7; const days = new Date(year, month + 1, 0).getDate();
  function move(delta: number) { const date = new Date(year, month + delta, 1); set({ year: date.getFullYear(), month: date.getMonth() }); }
  const today = new Date(); const todayString = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return <><PageHead title="Calendar" description="Your workshop schedule, all in one place." /><section className="panel calendar-panel"><div className="calendar-head"><h2>{first.toLocaleDateString("en-IN", { month: "long", year: "numeric" })}</h2><div><button className="button secondary" aria-label="Previous month" onClick={() => move(-1)}>←</button> <button className="button secondary" onClick={() => set({ month: today.getMonth(), year: today.getFullYear() })}>Today</button> <button className="button secondary" aria-label="Next month" onClick={() => move(1)}>→</button></div></div><div className="calendar-grid">{["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => <div className="day-name" key={day}>{day}</div>)}{Array.from({ length: padding }, (_, i) => <div className="day" key={`blank-${i}`} aria-hidden="true" />)}{Array.from({ length: days }, (_, i) => {
    const date = `${year}-${String(month + 1).padStart(2, "0")}-${String(i + 1).padStart(2, "0")}`;
    return <div className={`day ${date === todayString ? "today" : ""}`} key={date}><span className="day-number">{i + 1}</span>{sessions.filter((s) => s.date === date).map((s) => <button key={s.id} className="event" aria-label={`${workshops.find((w) => w.id === s.workshopId)?.title} on ${dateLabel(date)}`} onClick={() => open(s.workshopId, s.id)}><strong>{workshops.find((w) => w.id === s.workshopId)?.title}</strong><small>{s.start} · {s.title}</small></button>)}</div>;
  })}</div></section></>;
}
