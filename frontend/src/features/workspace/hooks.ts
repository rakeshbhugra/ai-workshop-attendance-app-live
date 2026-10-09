import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workspaceApi, workspaceKeys } from "./api";
import { useUiStore } from "@/stores/ui-store";
import { ApiError } from "@/lib/api";
import type { Record } from "./types";
export const useWorkshops = () => useQuery({ queryKey: workspaceKeys.workshops(), queryFn: workspaceApi.workshops });
export const useStudents = () => useQuery({ queryKey: workspaceKeys.students(), queryFn: workspaceApi.students });
export const useSessions = () => useQuery({ queryKey: workspaceKeys.sessions(), queryFn: workspaceApi.sessions });
export const useRecords = (id: string) => useQuery({ queryKey: workspaceKeys.records(id), queryFn: () => workspaceApi.records(id), enabled: !!id });
export function errorMessage(error: Error) { return error instanceof ApiError && !error.isUserFixable ? "The request could not be completed. Please try again." : error.message; }
export function useMark(sessionId: string) {
  const client = useQueryClient(); const notify = useUiStore((s) => s.notify);
  return useMutation({ mutationFn: (records: Record[]) => workspaceApi.mark(sessionId, records),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: workspaceKeys.records(sessionId) }); notify("Attendance saved"); },
    onError: (e) => notify(errorMessage(e), "error") });
}
export function useAddStudent() {
  const client = useQueryClient();
  return useMutation({ mutationFn: workspaceApi.addStudent, onSuccess: () => client.invalidateQueries({ queryKey: workspaceKeys.all }) });
}
export function useArchiveStudent() {
  const client = useQueryClient(); const notify = useUiStore((s) => s.notify);
  return useMutation({ mutationFn: workspaceApi.archiveStudent,
    onSuccess: async () => { await client.invalidateQueries({ queryKey: workspaceKeys.all }); notify("Student archived. Attendance history retained."); },
    onError: (e) => notify(errorMessage(e), "error") });
}
