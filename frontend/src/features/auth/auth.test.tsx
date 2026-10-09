import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { LoginPage } from "./login-page";
import { RequireAuth } from "./require-auth";
import { mockFetchSequence, renderWithProviders } from "@/test/utils";

function app() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<p>secret page</p>} />
      </Route>
    </Routes>
  );
}

describe("auth", () => {
  it("sends a signed-out visitor to the login page with one link per provider", async () => {
    mockFetchSequence([
      { status: 401, body: { detail: "not signed in" } },
      { status: 401, body: { detail: "not signed in" } },
      { body: ["google", "dev"] },
    ]);
    renderWithProviders(app());

    const google = await screen.findByRole("link", { name: "Continue with Google" });
    expect(google).toHaveAttribute("href", "/api/v1/auth/google/login");
    expect(screen.queryByText("secret page")).not.toBeInTheDocument();
  });

  it("shows the page to a signed-in user", async () => {
    mockFetchSequence([{ body: { id: "1", email: "a@b.c", name: "A", created_at: "2026-01-01T00:00:00Z" } }]);
    renderWithProviders(app());

    expect(await screen.findByText("secret page")).toBeInTheDocument();
  });
});
