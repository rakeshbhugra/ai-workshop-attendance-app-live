export type AttendanceStatus = "present" | "absent" | "unmarked";
export interface Student { id: string; name: string; email: string; archived: boolean }
export interface Workshop { id: string; title: string; date: string }
export interface AttendanceRecord { workshopId: string; studentId: string; status: AttendanceStatus }
export type Audience = "all" | "present" | "absent";
export interface MailDraft { id: string; workshopId: string; audience: Audience; recipientIds: string[]; subject: string; body: string }
export interface Workspace { students: Student[]; workshops: Workshop[]; records: AttendanceRecord[]; drafts: MailDraft[] }
export type Page = "attendance" | "classes" | "add" | "active" | "archive" | "admin" | "reports" | "mails";
