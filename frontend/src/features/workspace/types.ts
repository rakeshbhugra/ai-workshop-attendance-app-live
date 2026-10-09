export type Status = "unmarked" | "present" | "absent";
export interface Student { id: string; name: string; email: string; college: string; active: boolean }
export interface Workshop { id: string; title: string; description: string; category: string; facilitator: string; email: string; dates: string; days: string; location: string; active: boolean; studentIds: string[] }
export interface Session { id: string; workshopId: string; title: string; date: string; start: string; end: string; timezone?: string }
export interface Record { studentId: string; status: Status; checkIn: string; checkOut: string }
export interface StudentInput { name: string; email: string; college: string; workshopId: string }
