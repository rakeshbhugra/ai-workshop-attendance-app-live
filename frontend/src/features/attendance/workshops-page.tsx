import { useAttendanceWorkspace, useAddWorkshop } from "./hooks";
import { Heading, MutationError } from "./ui";
export function WorkshopsPage({ openWorkshop }: { openWorkshop: (id: string) => void }) {
  const { data } = useAttendanceWorkspace();
  const add = useAddWorkshop();
  if (!data) return null;
  return <>
    <Heading title={<em>Classes</em>} description="Each workshop has its own date and attendance record." />
    <form className="panel" onSubmit={(e) => { e.preventDefault(); const form = e.currentTarget; const values = new FormData(form); add.mutate({ title: String(values.get("title")), date: String(values.get("date")) }, { onSuccess: () => form.reset() }); }}>
      <h2>Create a workshop</h2><div className="fields"><label>Workshop title<input name="title" required maxLength={100} placeholder="e.g. Prompting with AI" /></label><label>Workshop date<input name="date" type="date" required defaultValue="2026-10-09" /></label></div><MutationError error={add.error} /><button className="btn primary" disabled={add.isPending}>{add.isPending ? "Creating…" : "Create workshop"}</button>
    </form>
    <div className="class-grid">{data.workshops.map((w) => <article className="class-card" key={w.id}><span className="tag">Workshop · {w.date}</span><h2>{w.title}</h2><p>{data.students.filter((s) => !s.archived).length} active students</p><button className="btn" onClick={() => openWorkshop(w.id)}>Fill attendance →</button></article>)}</div>
    {data.workshops.length === 0 && <p>No workshops yet. Create your first workshop above.</p>}
  </>;
}
