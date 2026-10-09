import { create } from "zustand";
export type View = "Workshops" | "Attendance" | "Students" | "Calendar" | "Reports";
export type Tab = "Overview" | "Students" | "Sessions" | "Attendance";
interface State {
  view: View; tab: Tab; workshopId: string; sessionId: string; search: string; workshopSearch: string;
  status: string; menuOpen: boolean; studentDialog: boolean; month: number; year: number; reportWorkshop: string;
  set: (patch: Partial<Omit<State, "set" | "navigate" | "selectWorkshop" | "openSession">>) => void;
  navigate: (view: View) => void; selectWorkshop: (id: string) => void; openSession: (workshopId: string, sessionId: string) => void;
}
export const useWorkspaceStore = create<State>((set) => ({
  view: "Workshops", tab: "Overview", workshopId: "", sessionId: "", search: "", workshopSearch: "",
  status: "all", menuOpen: false, studentDialog: false, month: new Date().getMonth(), year: new Date().getFullYear(), reportWorkshop: "all",
  set, navigate: (view) => set({ view, search: "", status: "all", menuOpen: false }),
  selectWorkshop: (workshopId) => set({ workshopId, sessionId: "", tab: "Overview", search: "", status: "all" }),
  openSession: (workshopId, sessionId) => set({ workshopId, sessionId, view: "Attendance", search: "", status: "all", menuOpen: false }),
}));
