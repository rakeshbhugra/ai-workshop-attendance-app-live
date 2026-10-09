import { useAttendanceWorkspace, useSaveDraft } from "./hooks";
import { Heading, WorkshopSelect, MutationError } from "./ui";
import type { Audience } from "./types";
export function MailsPage({ workshopId, onWorkshopChange }: { workshopId: string; onWorkshopChange: (id: string) => void }) {
  const { data } = useAttendanceWorkspace();
  const save = useSaveDraft();
  if (!data) return null;
  return <>
    <Heading title={<em>Mails</em>} description="Prepare a workshop message. This demo saves drafts only." />
    <form className="panel" onSubmit={(e) => { e.preventDefault(); const form = e.currentTarget; const values = new FormData(form); save.mutate({ workshopId, audience: values.get("audience") as Audience, subject: String(values.get("subject")), body: String(values.get("body")) }, { onSuccess: () => form.reset() }); }}>
      <label className="field">Workshop<WorkshopSelect data={data} workshopId={workshopId} onChange={onWorkshopChange} /></label>
      <label className="field">Recipients<select name="audience"><option value="all">All active students</option><option value="present">Present students in selected workshop</option><option value="absent">Absent students in selected workshop</option></select></label>
      <label className="field">Subject<input name="subject" required maxLength={160} placeholder="Workshop follow-up" /></label><label className="field">Message<textarea name="body" required maxLength={5000} placeholder="Write your message…" /></label><MutationError error={save.error} /><p>No emails are sent.</p><button className="btn primary" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save draft"}</button>
    </form>
    <div className="panel draft-panel"><h2>Drafts ({data.drafts.length})</h2>{data.drafts.map((d) => <article className="draft" key={d.id}><strong>{d.subject}</strong><small>{data.workshops.find((w) => w.id === d.workshopId)?.title} · {d.recipientIds.length} recipients · {d.audience}</small><p>{d.body}</p></article>)}{data.drafts.length === 0 && <p>Your saved drafts will appear here.</p>}</div>
  </>;
}
