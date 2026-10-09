/**
 * Test helpers.
 *
 * `renderWithProviders` wraps a component in the same providers `main.tsx` does,
 * so a test exercises the component the way the app actually mounts it.
 *
 * The QueryClient is built fresh per render with retries off. Both matter: a
 * shared client leaks cached data between tests, and retries turn an expected
 * error into a multi-second timeout.
 */

import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { render } from "@testing-library/react";
import { Toaster } from "@/components/toaster";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(ui: ReactElement, { route = "/" } = {}) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>
          {children}
          {/* The Toaster lives in Layout, so it is mounted for every page in the
              real app. Including it here means a test can assert on the error
              message a page raises, rather than on the store behind it. */}
          <Toaster />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper }) };
}

/** Stub `fetch` with a queue of responses, in call order. */
export function mockFetchSequence(responses: Array<{ status?: number; body: unknown }>) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let index = 0;

  const fetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), ...(init ? { init } : {}) });
    const next = responses[Math.min(index++, responses.length - 1)];
    const status = next?.status ?? 200;
    return new Response(JSON.stringify(next?.body ?? null), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };

  vi.stubGlobal("fetch", fetchMock);
  return { calls };
}
