import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ goals: vi.fn() }));

vi.mock("@/lib/api", () => ({ api: mocks }));

import { GoalManager } from "./goals-view";

const goal = {
  id: "goal-1",
  name: "Reduce household emissions",
  target_type: "Reduction goal",
  baseline_co2e: "135.670000",
  target_co2e: "20.000000",
  start_date: "2026-10-01",
  end_date: "2026-10-31",
  is_completed: false,
  current_co2e: "25.000000",
  progress_percent: "95.68",
  remaining_co2e: "0.000000",
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

describe("goal progress", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows ring progress and the amount emissions exceed the target", async () => {
    mocks.goals.mockResolvedValue([goal]);
    render(<GoalManager />);

    expect(await screen.findByRole("heading", { name: goal.name })).toBeInTheDocument();
    expect(screen.getByText("Over target")).toBeInTheDocument();
    expect(screen.getByText("5 kg CO₂e above your target.")).toBeInTheDocument();
    expect(screen.getByRole("img", {
      name: /95\.68 percent of planned reduction complete.*kilograms over target/i,
    })).toBeInTheDocument();
    const card = screen.getByRole("article");
    expect(card).toHaveTextContent("25 kg CO₂e");
    expect(card).toHaveTextContent("20 kg CO₂e");
    expect(card).toHaveTextContent("135.67 kg CO₂e");
  });

  it("marks a goal as met and reports how far below target it is", async () => {
    mocks.goals.mockResolvedValue([{
      ...goal,
      is_completed: true,
      current_co2e: "15.000000",
      progress_percent: "100.00",
      remaining_co2e: "5.000000",
    }]);
    render(<GoalManager />);

    await waitFor(() => expect(screen.getByText("Target met")).toBeInTheDocument());
    expect(screen.getByText("5 kg CO₂e below your target.")).toBeInTheDocument();
    expect(screen.getByRole("img", {
      name: /100 percent of planned reduction complete.*target met/i,
    })).toBeInTheDocument();
  });
});
