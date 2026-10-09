import { api } from "@/lib/api";
import { mockApi } from "./mock-api";
import type { Student, Workshop, Session, Record, StudentInput } from "./types";
export const isMock = import.meta.env.VITE_ATTENDANCE_DATA_MODE === "mock";
export const workspaceApi = {
  workshops: () => isMock ? mockApi.workshops() : api.get<Workshop[]>("/workshops"),
  students: () => isMock ? mockApi.students() : api.get<Student[]>("/students"),
  sessions: () => isMock ? mockApi.sessions() : api.get<Session[]>("/sessions"),
  records: (id: string) => isMock ? mockApi.records(id) : api.get<Record[]>(`/sessions/${encodeURIComponent(id)}/attendance`),
  mark: async (id: string, records: Record[]) => { await (isMock ? mockApi.mark(id, records) : api.patch<Record[]>(`/sessions/${encodeURIComponent(id)}/attendance`, { records })); },
  addStudent: (input: StudentInput) => isMock ? mockApi.addStudent(input) : api.post<Student>("/students", input),
  archiveStudent: async (id: string) => { await (isMock ? mockApi.archiveStudent(id) : api.patch<Student>(`/students/${encodeURIComponent(id)}`, { active: false })); },
};
export const workspaceKeys = {
  all: ["workspace"] as const,
  workshops: () => ["workspace", "workshops"] as const,
  students: () => ["workspace", "students"] as const,
  sessions: () => ["workspace", "sessions"] as const,
  records: (id: string) => ["workspace", "records", id] as const,
};
