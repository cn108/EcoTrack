import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  createActivity: vi.fn(),
  updateActivity: vi.fn(),
  activityOptions: vi.fn(),
  activities: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ ApiError: class ApiError extends Error {}, api: mocks }));

import { ActivityEditor, ActivityManager } from "./activity-manager";

const options = {
  categories: [{ id: "category-1", name: "Transport" }],
  emission_factors: [{
    id: "factor-1",
    category: "Transport",
    activity_type: "car_petrol",
    activity_label: "Petrol burned",
    unit: "L",
    unit_label: "litres of fuel",
    factor_value: "2.2860000000",
    co2e_unit: "kg_co2e",
    source_name: "IPCC fuel-combustion default",
    source_url: "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
    source_year: 2006,
    region: "Fuel combustion default; tailpipe only",
  }],
};

const savedActivity = {
  id: "activity-1",
  category: options.categories[0],
  activity_type: "car_petrol",
  quantity: "2",
  unit: "L",
  activity_date: "2026-09-28",
  calculated_co2e: "2.000000",
  unit_cost_ngn: null,
  emission_factor: {
    id: "factor-1",
    factor_value: "2.2860000000",
    factor_unit: "kg_co2e_per_L",
    co2e_unit: "kg_co2e",
    source_name: "IPCC fuel-combustion default",
    source_url: "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
    source_year: 2006,
    region: "Fuel combustion default; tailpipe only",
  },
  notes: null,
  created_at: "2026-09-28T00:00:00Z",
  updated_at: "2026-09-28T00:00:00Z",
};

describe("activity entry", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows activity quantities and emissions rounded to at most two decimals", async () => {
    mocks.activityOptions.mockResolvedValue(options);
    mocks.activities.mockResolvedValue([{
      ...savedActivity,
      quantity: "10.123456",
      calculated_co2e: "25.199000",
    }]);
    render(<ActivityManager />);

    const row = await screen.findByRole("row", { name: /car petrol/i });
    expect(row).toHaveTextContent("10.12 L");
    expect(row).toHaveTextContent("25.2");
    expect(row).not.toHaveTextContent("10.123456");
    expect(row).not.toHaveTextContent("25.199000");
  });

  it("submits inputs to the API and displays only the returned CO2e", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    mocks.createActivity.mockResolvedValue(savedActivity);
    render(
      <ActivityEditor
        options={options}
        categories={options.categories}
        activity={null}
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );

    await waitFor(() => expect(screen.getByLabelText("Activity type")).toHaveValue("car_petrol"));
    expect(screen.getByLabelText("Unit")).toHaveValue("L");
    expect(screen.getByText(/2\.286 kg CO₂e per L/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Quantity (L)"), "2");
    await user.click(screen.getByRole("button", { name: "Save activity" }));

    await waitFor(() => expect(mocks.createActivity).toHaveBeenCalledWith(expect.objectContaining({
      category_id: "category-1",
      activity_type: "car_petrol",
      quantity: "2",
      unit: "L",
    })));
    expect(mocks.createActivity.mock.calls[0][0]).not.toHaveProperty("calculated_co2e");
    expect(onSaved).toHaveBeenCalledWith(savedActivity);
  });

  it("sends an entered fuel price when updating an activity", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    const updatedActivity = { ...savedActivity, unit_cost_ngn: "1750" };
    mocks.updateActivity.mockResolvedValue(updatedActivity);
    render(
      <ActivityEditor
        options={options}
        categories={options.categories}
        activity={savedActivity}
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );

    const priceInput = screen.getAllByRole("spinbutton")[1];
    await user.clear(priceInput);
    await user.type(priceInput, "1750");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(mocks.updateActivity).toHaveBeenCalledWith(
      "activity-1",
      expect.objectContaining({
        activity_type: "car_petrol",
        unit_cost_ngn: "1750",
      }),
    ));
    expect(onSaved).toHaveBeenCalledWith(updatedActivity);
  });
});