import seed from "./seed.json";
import type { StudentInput, Record, Status } from "./types";
const initial = () => structuredClone(seed);
let data = initial();
export function resetDemo() { data = initial(); }
export const mockApi = {
  async workshops() { return structuredClone(data.workshops); },
  async students() { return structuredClone(data.students); },
  async sessions() { return structuredClone(data.sessions); },
  async records(sessionId: string): Promise<Record[]> {
    const session = data.sessions.find((s) => s.id === sessionId);
    const workshop = data.workshops.find((w) => w.id === session?.workshopId);
    return (workshop?.studentIds ?? []).map((studentId) => {
      const record = data.attendance[`${sessionId}:${studentId}` as keyof typeof data.attendance];
      return { studentId, status: (record?.status ?? "unmarked") as Status, checkIn: record?.checkIn ?? "", checkOut: record?.checkOut ?? "" };
    });
  },
  async mark(sessionId: string, records: Record[]) {
    for (const record of records) {
      if ((record.checkIn || record.checkOut) && record.status !== "present") throw new Error("Only Present attendance can have participation times.");
      if (record.checkOut && !record.checkIn) throw new Error("Record check-in before check-out.");
      if (record.checkIn && record.checkOut && record.checkOut < record.checkIn) throw new Error("Check-out must be later than check-in.");
    }
    const attendance = data.attendance as { [key: string]: { status: string; checkIn: string; checkOut: string } };
    records.forEach(({ studentId, ...record }) => { attendance[`${sessionId}:${studentId}`] = record; });
  },
  async addStudent(input: StudentInput) {
    if (data.students.some((s) => s.email.toLowerCase() === input.email.toLowerCase())) throw new Error("A student with this email already exists.");
    const student = { id: crypto.randomUUID(), name: input.name.trim(), email: input.email.trim().toLowerCase(), college: input.college.trim(), active: true };
    data.students.push(student);
    data.workshops.find((w) => w.id === input.workshopId)?.studentIds.push(student.id);
    return student;
  },
  async archiveStudent(id: string) { const student = data.students.find((s) => s.id === id); if (student) student.active = false; },
};
