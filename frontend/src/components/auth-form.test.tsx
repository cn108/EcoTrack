import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  register: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace }),
  useSearchParams: () => ({ get: () => null }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) =>
    <a href={href as string} {...props}>{children}</a>,
}));

vi.mock("@/context/auth-context", () => ({
  useAuth: () => ({ login: mocks.login, register: mocks.register }),
}));

import { AuthForm } from "./auth-form";

describe("authentication forms", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits login credentials and navigates to the dashboard", async () => {
    mocks.login.mockResolvedValue(undefined);
    render(<AuthForm mode="login" />);
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "person@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/), {
      target: { value: "secret-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mocks.login).toHaveBeenCalledWith("person@example.com", "secret-password"));
    expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
  });

  it("submits registration details and sends the user to login", async () => {
    mocks.register.mockResolvedValue({ id: "user-1" });
    render(<AuthForm mode="register" />);
    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Ari" } });
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "Green" } });
    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "ari@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/), {
      target: { value: "strong-password-9" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mocks.register).toHaveBeenCalledWith({
      email: "ari@example.com",
      password: "strong-password-9",
      first_name: "Ari",
      last_name: "Green",
    }));
    expect(mocks.replace).toHaveBeenCalledWith("/login?registered=1");
  });
});