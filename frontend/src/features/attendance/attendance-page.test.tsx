import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { AttendancePage } from "./attendance-page";
import { attendanceApi, resetMockData } from "./api";

beforeEach(() => resetMockData());
describe("attendance workspace", () => {
  it("marks and clears attendance with real Query invalidation and no HTTP", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup();
    renderWithProviders(<AttendancePage />);
    const present = await screen.findByRole("button", { name: "Mark Ishaan Rao present" });
    expect(present).toHaveAttribute("aria-pressed", "false");
    await user.click(present);
    await waitFor(() => expect(present).toHaveAttribute("aria-pressed", "true"));
    await user.click(present);
    await waitFor(() => expect(present).toHaveAttribute("aria-pressed", "false"));
    expect(fetch).not.toHaveBeenCalled();
  });

  it("adds students, rejects duplicate emails, archives and restores", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AttendancePage />);
    await screen.findByText("Aarav Mehta");
    const nav = screen.getByRole("navigation");
    await user.click(within(nav).getByRole("button", { name: "Add Student" }));
    await user.type(screen.getByLabelText("Full name"), "Mira Bose");
    await user.type(screen.getByLabelText("Email address"), "aarav@example.com");
    await user.click(screen.getByRole("button", { name: "Add Student", current: false }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
    await user.clear(screen.getByLabelText("Email address"));
    await user.type(screen.getByLabelText("Email address"), "mira@example.com");
    await user.click(screen.getByRole("button", { name: "Add Student", current: false }));
    await screen.findByText("Mira Bose");
    await user.click(screen.getByRole("button", { name: "Archive Mira Bose" }));
    await waitFor(() => expect(screen.queryByText("Mira Bose")).not.toBeInTheDocument());
    await user.click(within(nav).getByRole("button", { name: "Archive Students" }));
    await user.click(await screen.findByRole("button", { name: "Restore Mira Bose" }));
    await waitFor(() => expect(screen.queryByText("Mira Bose")).not.toBeInTheDocument());
    await user.click(within(nav).getByRole("button", { name: "Active Students" }));
    expect(await screen.findByText("Mira Bose")).toBeInTheDocument();
  });

  it("keeps attendance independent per workshop and snapshots mail recipients", async () => {
    const user = userEvent.setup();
    renderWithProviders(<AttendancePage />);
    await screen.findByText("Aarav Mehta");
    const nav = screen.getByRole("navigation");
    await user.click(within(nav).getByRole("button", { name: "Classes" }));
    await user.type(screen.getByLabelText("Workshop title"), "Prompting with AI");
    await user.click(screen.getByRole("button", { name: "Create workshop" }));
    await user.click((await screen.findAllByRole("button", { name: "Fill attendance →" }))[1]!);
    const present = await screen.findByRole("button", { name: "Mark Aarav Mehta present" });
    expect(present).toHaveAttribute("aria-pressed", "false");
    await user.click(present);
    await waitFor(() => expect(present).toHaveAttribute("aria-pressed", "true"));
    await user.click(within(nav).getByRole("button", { name: "Mails" }));
    await user.selectOptions(screen.getByLabelText("Recipients"), "present");
    await user.type(screen.getByLabelText("Subject"), "Thanks for joining");
    await user.type(screen.getByLabelText("Message"), "See you next time.");
    await user.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Thanks for joining")).toBeInTheDocument();
    expect(screen.getByText(/1 recipients/)).toBeInTheDocument();
    const data = await attendanceApi.list();
    expect(data.drafts[0]?.recipientIds).toEqual(["1"]);
    expect(data.records.filter((r) => r.workshopId === "1" && r.status === "present")).toHaveLength(2);
  });
});
