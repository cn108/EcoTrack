import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ replace: vi.fn(), auth: { user: null as unknown, loading: false } }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ replace: mocks.replace }),
}));

vi.mock("@/context/auth-context", () => ({ useAuth: () => mocks.auth }));

import { AuthGate } from "./auth-gate";

describe("protected routes", () => {
  beforeEach(() => {
    mocks.replace.mockReset();
    mocks.auth = { user: null, loading: false };
  });

  it("redirects unauthenticated users to login without rendering protected content", async () => {
    render(<AuthGate><div>Sensitive dashboard</div></AuthGate>);
    expect(screen.queryByText("Sensitive dashboard")).not.toBeInTheDocument();
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/login?next=%2Fdashboard"));
  });

  it("holds the protected page while restoring the session", () => {
    mocks.auth = { user: null, loading: true };
    render(<AuthGate><div>Sensitive dashboard</div></AuthGate>);
    expect(screen.getByRole("status", { name: "Checking session" })).toBeInTheDocument();
    expect(mocks.replace).not.toHaveBeenCalled();
  });
});