import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { attendanceApi, attendanceKeys } from "./api";

export function useAttendanceWorkspace() {
  return useQuery({ queryKey: attendanceKeys.workspace(), queryFn: attendanceApi.list });
}
function useWorkspaceMutation<T, R>(mutationFn: (input: T) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({ mutationFn, onSuccess: () => client.invalidateQueries({ queryKey: attendanceKeys.all }) });
}
export function useMarkAttendance() { return useWorkspaceMutation(attendanceApi.mark); }
export function useAddStudent() { return useWorkspaceMutation(attendanceApi.addStudent); }
export function useArchiveStudent() { return useWorkspaceMutation(attendanceApi.archiveStudent); }
export function useAddWorkshop() { return useWorkspaceMutation(attendanceApi.addWorkshop); }
export function useSaveDraft() { return useWorkspaceMutation(attendanceApi.saveDraft); }
