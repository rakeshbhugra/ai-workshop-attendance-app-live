import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { useAddStudent, errorMessage, useWorkshops } from "./hooks";
import { useUiStore } from "@/stores/ui-store";
export function StudentDialog() {
  const open = useWorkspaceStore((s) => s.studentDialog); const set = useWorkspaceStore((s) => s.set);
  const selected = useWorkspaceStore((s) => s.workshopId); const workshops = useWorkshops();
  const mutation = useAddStudent(); const notify = useUiStore((s) => s.notify); const dialog = useRef<HTMLDialogElement>(null);
  const active = (workshops.data ?? []).filter((w) => w.active);
  useEffect(() => { if (open) { mutation.reset(); dialog.current?.querySelector("form")?.reset(); const select = dialog.current?.querySelector("select"); if (select) select.value = selected || active[0]?.id || ""; dialog.current?.showModal(); } else dialog.current?.close(); }, [open]);
  return <dialog ref={dialog} onCancel={() => set({ studentDialog: false })}><form onSubmit={(e) => {
    e.preventDefault(); const form = new FormData(e.currentTarget);
    mutation.mutate({ name: String(form.get("name")).trim(), email: String(form.get("email")).trim(), college: String(form.get("college")).trim(), workshopId: String(form.get("workshopId")) }, { onSuccess: () => { set({ studentDialog: false }); notify("Student added"); } });
  }}><div className="dialog-head"><h2>Add a student</h2><button type="button" className="icon-button" aria-label="Close dialog" onClick={() => set({ studentDialog: false })}>×</button></div><p>Add a student and enroll them in a workshop.</p>
    <label>Full name<input name="name" required maxLength={100} autoFocus /></label><label>Email address<input name="email" type="email" required /></label><label>College / Institution<input name="college" required maxLength={120} /></label><label>Workshop<select name="workshopId" required defaultValue={selected || active[0]?.id}>{active.map((w) => <option key={w.id} value={w.id}>{w.title}</option>)}</select></label>
    {mutation.isError && <p className="form-error" role="alert">{errorMessage(mutation.error)}</p>}<div className="dialog-actions"><button type="button" className="button secondary" onClick={() => set({ studentDialog: false })}>Cancel</button><button className="button primary" disabled={mutation.isPending || !active.length}>{mutation.isPending ? "Adding…" : "Add student"}</button></div></form></dialog>;
}
