import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { RouterProvider, createBrowserRouter } from "react-router";
import { Layout } from "@/components/layout";
import { LoginPage } from "@/features/auth/login-page";
import { RequireAuth } from "@/features/auth/require-auth";
import { FilesPage } from "@/features/files/files-page";
import { NotesPage } from "@/features/notes/notes-page";
import { WorkspacePage } from "@/features/workspace/workspace-page";
import { isMock } from "@/features/workspace/api";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30s, so navigating back to a page you just
      // left doesn't refetch. Tune per-query where a screen needs it fresher.
      staleTime: 30_000,
      // Off because it surprises people: with it on, alt-tabbing back to the
      // browser silently refires every visible query.
      refetchOnWindowFocus: false,
      // Retrying a 404 or a 422 is pointless — the answer will not change. Only
      // retry what might be transient.
      retry: (failureCount, error) => {
        const status = (error as { status?: number }).status;
        if (status !== undefined && status < 500) return false;
        return failureCount < 2;
      },
    },
  },
});

// createBrowserRouter (not HashRouter): the backend's SPA catch-all returns
// index.html for unknown paths, so real URLs work on refresh and when shared.
const router = createBrowserRouter([
  ...(isMock ? [{ path: "/", element: <WorkspacePage /> }] : [{ element: <RequireAuth />, children: [{ path: "/", element: <WorkspacePage /> }] }]),
  { path: "/login", element: <LoginPage /> },
  {
    // Every page below needs a signed-in user.
    element: <RequireAuth />,
    children: [
      {
        path: "/examples",
        element: <Layout />,
        children: [
          { index: true, element: <NotesPage /> },
          { path: "files", element: <FilesPage /> },
        ],
      },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      {/* Query Devtools: the flower icon in the corner shows every query, its
          cache state and its data. When a screen shows stale or missing data,
          open this before adding a console.log — it usually says exactly which
          query is stale and why. `import.meta.env.DEV` is statically replaced at
          build time, so Rollup drops this and the whole devtools package from
          the production bundle. */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  </StrictMode>,
);
