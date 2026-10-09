import students from "./mocks/students.json";
import workshops from "./mocks/workshops.json";
import records from "./mocks/records.json";
import drafts from "./mocks/drafts.json";
import type { Workspace, Student, Workshop, AttendanceRecord, MailDraft, AttendanceStatus } from "./types";

// In-memory transport replaces HTTP until an attendance backend exists. JSON is
// the seed, never a writable browser store. Reloading starts a fresh demo.
const seed: Workspace = { students, workshops, records: records as AttendanceRecord[], drafts };
let workspace: Workspace = structuredClone(seed);
export function resetMockData() { workspace = structuredClone(seed); }
export function statusOf(data: Workspace, workshopId: string, studentId: string): AttendanceStatus {
  return data.records.find((r) => r.workshopId === workshopId && r.studentId === studentId)?.status ?? "unmarked";
}
function requireWorkshop(id: string) {
  if (!workspace.workshops.some((w) => w.id === id)) throw new Error("Choose an existing workshop.");
}
export const attendanceApi = {
  async list(): Promise<Workspace> { return structuredClone(workspace); },
  async mark(record: AttendanceRecord) {
    requireWorkshop(record.workshopId);
    if (!workspace.students.some((s) => s.id === record.studentId && !s.archived)) throw new Error("Choose an active student.");
    workspace.records = workspace.records.filter((r) => r.workshopId !== record.workshopId || r.studentId !== record.studentId);
    workspace.records.push({ ...record });
  },
  async addStudent(input: Pick<Student, "name" | "email">) {
    const name = input.name.trim(), email = input.email.trim().toLowerCase();
    if (!name || !email) throw new Error("Enter a name and email address.");
    if (workspace.students.some((s) => s.email.toLowerCase() === email)) throw new Error("This email already exists in the active or archived roster.");
    workspace.students.push({ id: crypto.randomUUID(), name, email, archived: false });
  },
  async archiveStudent({ id, archived }: { id: string; archived: boolean }) {
    const student = workspace.students.find((s) => s.id === id);
    if (!student) throw new Error("Student not found.");
    student.archived = archived;
  },
  async addWorkshop(input: Pick<Workshop, "title" | "date">) {
    const title = input.title.trim();
    if (!title || !input.date) throw new Error("Enter a title and workshop date.");
    const workshop = { ...input, title, id: crypto.randomUUID() };
    workspace.workshops.push(workshop);
    return workshop;
  },
  async saveDraft(input: Omit<MailDraft, "id" | "recipientIds">) {
    requireWorkshop(input.workshopId);
    const subject = input.subject.trim(), body = input.body.trim();
    if (!subject || !body) throw new Error("Enter a subject and message.");
    const recipientIds = workspace.students.filter((s) => !s.archived && (input.audience === "all" || statusOf(workspace, input.workshopId, s.id) === input.audience)).map((s) => s.id);
    workspace.drafts.unshift({ ...input, subject, body, recipientIds, id: crypto.randomUUID() });
  },
};
export const attendanceKeys = {
  all: ["attendance"] as const,
  workspace: () => [...attendanceKeys.all, "workspace"] as const,
};
