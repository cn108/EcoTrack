import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ dashboard: vi.fn(), monthlyEmissions: vi.fn() }));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) =>
    <a href={href as string} {...props}>{children}</a>,
}));

vi.mock("recharts", () => ({
  Area: () => null,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

import { DashboardView } from "./dashboard-view";

const emptyDashboard = {
  current_month_total_co2e: "0.000000",
  previous_month_total_co2e: "0.000000",
  percentage_change_percent: null,
  daily_average_co2e: "0.000000",
  activities_this_month: 0,
  highest_emission_category: null,
  highest_emission_activity_type: null,
  category_totals: [],
  recent_activities: [],
};

describe("dashboard data states", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders loading feedback while the dashboard request is pending", () => {
    mocks.dashboard.mockReturnValue(new Promise(() => undefined));
    mocks.monthlyEmissions.mockReturnValue(new Promise(() => undefined));
    render(<DashboardView />);
    expect(screen.getByRole("status", { name: "Loading dashboard" })).toBeInTheDocument();
  });

  it("renders the empty state when the backend has no activity", async () => {
    mocks.dashboard.mockResolvedValue(emptyDashboard);
    mocks.monthlyEmissions.mockResolvedValue([]);
    render(<DashboardView />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "A fresh start, measured." })).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /log your first activity/i })).toHaveAttribute("href", "/activities?new=1");
  });
});