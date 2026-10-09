/** Renders the Zustand toast queue. Mounted once, in the layout. */

import { X } from "lucide-react";
import { useUiStore } from "@/stores/ui-store";

export function Toaster() {
  const toasts = useUiStore((s) => s.toasts);
  const dismiss = useUiStore((s) => s.dismissToast);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2" role="status">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-start gap-3 rounded-lg px-4 py-3 text-sm shadow-lg ring-1 ${
            toast.tone === "error"
              ? "bg-red-50 text-red-900 ring-red-200 dark:bg-red-950 dark:text-red-100 dark:ring-red-900"
              : "bg-slate-900 text-slate-50 ring-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:ring-slate-300"
          }`}
        >
          <span className="flex-1">{toast.message}</span>
          <button
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss notification"
            className="opacity-60 transition-opacity hover:opacity-100"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
