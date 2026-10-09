import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { useUiStore } from "@/stores/ui-store";

import { useWorkspaceStore } from "@/stores/workspace-store";
const initialWorkspaceState = useWorkspaceStore.getInitialState();

const initialUiState = useUiStore.getInitialState();

afterEach(() => {
  // Unmount between tests. Without it, a query from the previous test can still
  // be mounted and its refetch lands in the next one — the classic "passes
  // alone, fails in the suite" frontend flake.
  cleanup();

  // Zustand stores are module-level singletons, so state set by one test is
  // still there for the next. Reset every store you add here.
  useUiStore.setState(initialUiState, true);
  useWorkspaceStore.setState(initialWorkspaceState, true);

  // Drop any `vi.stubGlobal("fetch", ...)` so a test that forgets to stub fetch
  // fails loudly instead of quietly reusing the previous test's stub.
  vi.unstubAllGlobals();
});
