/**
 * Zustand — this app's **client state**.
 *
 * Everything in here is true only for this browser tab: a filter toggle and a
 * transient toast queue. None of it is fetched, none of it is persisted, and
 * none of it duplicates something the server knows (see the note at the top of
 * `features/notes/hooks.ts`).
 *
 * Store style used throughout: state and the actions that change it live
 * together, and components select the narrowest slice they need
 * (`useUiStore((s) => s.showArchived)`) rather than the whole store — selecting
 * the whole store re-renders the component on every unrelated change.
 */

import { create } from "zustand";

export interface Toast {
  id: number;
  message: string;
  tone: "success" | "error";
}

interface UiState {
  showArchived: boolean;
  toggleShowArchived: () => void;

  toasts: Toast[];
  notify: (message: string, tone?: Toast["tone"]) => void;
  dismissToast: (id: number) => void;
}

let nextToastId = 0;

export const useUiStore = create<UiState>((set) => ({
  showArchived: false,
  toggleShowArchived: () => set((state) => ({ showArchived: !state.showArchived })),

  toasts: [],
  notify: (message, tone = "success") => {
    const id = nextToastId++;
    set((state) => ({ toasts: [...state.toasts, { id, message, tone }] }));
    // Auto-dismiss. Kept in the store rather than in a component so a toast
    // raised during navigation still disappears after the component that
    // triggered it has unmounted.
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 4000);
  },
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
