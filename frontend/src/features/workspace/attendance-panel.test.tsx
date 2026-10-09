import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/utils";
import { AttendancePanel } from "./attendance-panel";
describe("session attendance", () => {
  function setup() {
    let record = { studentId: "student-1", status: "present", checkIn: "10:00", checkOut: "11:00" };
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/attendance")) {
        if (init?.method === "PATCH") record = JSON.parse(String(init.body)).records[0];
        return Response.json([record]);
      }
      if (path.endsWith("/sessions")) return Response.json([{ id: "session-1", workshopId: "workshop-1", title: "Intro", date: "2026-10-09", start: "10:00", end: "12:00" }]);
      if (path.endsWith("/students")) return Response.json([{ id: "student-1", name: "Aarav Sharma", email: "aarav@example.com", college: "DU", active: true }]);
      if (path.endsWith("/workshops")) return Response.json([{ id: "workshop-1", title: "AI Essentials", studentIds: ["student-1"], active: true }]);
      throw new Error(`Unexpected request ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<AttendancePanel workshopId="workshop-1" standalone />);
    return fetchMock;
  }
  it("saves status, clears times for absence, and refetches session records", async () => {
    const requests = setup(); const user = userEvent.setup();
    const status = await screen.findByRole("combobox", { name: "Attendance for Aarav Sharma" });
    await user.selectOptions(status, "absent");
    await waitFor(() => expect(screen.getByLabelText("Check-in for Aarav Sharma")).toHaveValue(""));
    const write = requests.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(write?.[1]?.body))).toEqual({ records: [{ studentId: "student-1", status: "absent", checkIn: "", checkOut: "" }] });
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });
  it("saves participation time only after explicit save", async () => {
    const requests = setup(); const user = userEvent.setup();
    const input = await screen.findByLabelText("Check-out for Aarav Sharma");
    await user.clear(input); await user.type(input, "11:30");
    expect(requests.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);
    await user.click(screen.getByRole("button", { name: "Save times for Aarav Sharma" }));
    await waitFor(() => expect(screen.getByText("90 min")).toBeInTheDocument());
  });
});
