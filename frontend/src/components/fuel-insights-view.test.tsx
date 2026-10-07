import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ fuelInsights: vi.fn() }));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) =>
    <a href={href as string} {...props}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

import { FuelInsightsView } from "./fuel-insights-view";

describe("fuel insights", () => {
  beforeEach(() => vi.clearAllMocks());

  it("presents fuel totals, scenario, and alternatives with clear labels", async () => {
    mocks.fuelInsights.mockResolvedValue({
      fuels: [{
        activity_type: "car_diesel",
        unit: "L",
        activity_count: 1,
        total_quantity: "2.000000",
        total_cost_ngn: "3500.000000",
        total_co2e: "5.280000",
      }],
    });

    render(<FuelInsightsView />);

    expect(await screen.findByRole("heading", { name: "Vehicle diesel" })).toBeInTheDocument();
    expect(screen.getByText("Recorded spend")).toBeInTheDocument();
    expect(screen.getByText("Fuel logged")).toBeInTheDocument();
    expect(screen.getByText("Direct fuel emissions")).toBeInTheDocument();
    expect(screen.getByText("What if you used 10% less?")).toBeInTheDocument();
    expect(screen.getByText(/about ₦350\.00 less spend/)).toBeInTheDocument();
    expect(screen.getByText("How to read these estimates")).toBeInTheDocument();
    expect(screen.getByText("Lower-cost travel option to investigate")).toBeInTheDocument();
  });
});
