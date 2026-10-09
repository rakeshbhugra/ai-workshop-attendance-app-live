/** Who is signed in, and how one can sign in. Sign-in itself is a full-page
 *  navigation to the API (a fetch cannot follow a redirect to Google), so the
 *  only mutation here is logout. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Me {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export const ME_KEY = ["me"];

export function useMe() {
  return useQuery({ queryKey: ME_KEY, queryFn: () => api.get<Me>("/auth/me"), retry: false, staleTime: Infinity });
}

export function useProviders() {
  return useQuery({ queryKey: ["auth-providers"], queryFn: () => api.get<string[]>("/auth/providers") });
}

export const loginUrl = (provider: string) => `/api/v1/auth/${provider}/login`;

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    // Drop every cached query, so the next user never sees this one's data.
    onSuccess: () => qc.clear(),
  });
}
