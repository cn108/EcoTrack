import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  activityOptions: vi.fn(),
  createActivity: vi.fn(),
  routeDistance: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

import { TripPlanner } from "./trip-planner";

const options = {
  categories: [{ id: "transport-id", name: "Transport" }],
  emission_factors: [
    {
      id: "petrol-factor",
      category: "Transport",
      activity_type: "car_petrol",
      activity_label: "Petrol burned",
      unit: "L",
      unit_label: "Litres (L)",
      factor_value: "2.286000",
      co2e_unit: "kg_co2e",
      source_name: "IPCC fuel-combustion default",
      source_url: null,
      source_year: 2006,
      region: "Fuel combustion default; tailpipe only",
    },
    {
      id: "diesel-factor",
      category: "Transport",
      activity_type: "car_diesel",
      activity_label: "Diesel burned",
      unit: "L",
      unit_label: "Litres (L)",
      factor_value: "2.680000",
      co2e_unit: "kg_co2e",
      source_name: "IPCC fuel-combustion default",
      source_url: null,
      source_year: 2006,
      region: "Fuel combustion default; tailpipe only",
    },
  ],
};

describe("manual trip planner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("estimates and saves a multi-leg trip as fuel activity with route details", async () => {
    const user = userEvent.setup();
    mocks.activityOptions.mockResolvedValue(options);
    mocks.routeDistance
      .mockResolvedValueOnce({ distance_meters: 12500, distance_km: 12.5, duration_seconds: 900 })
      .mockResolvedValueOnce({ distance_meters: 5500, distance_km: 5.5, duration_seconds: 360 });
    mocks.createActivity.mockResolvedValue({ calculated_co2e: "3.497580" });
    render(<TripPlanner />);

    await screen.findByRole("heading", { name: "Trip route" });
    await user.type(screen.getAllByPlaceholderText("Full address, city")[0], "Home, Lagos");
    await user.type(screen.getAllByPlaceholderText("Full address, city")[1], "Office, Lagos");
    await user.click(screen.getByRole("button", { name: "Calculate route" }));
    await screen.findByDisplayValue("12.5");
    await user.click(screen.getByRole("button", { name: "Add another leg" }));

    const locations = screen.getAllByPlaceholderText("Full address, city");
    await user.type(locations[2], "Office, Lagos");
    await user.type(locations[3], "Lunch stop, Lagos");
    await user.click(screen.getAllByRole("button", { name: "Calculate route" })[1]);
    await screen.findByDisplayValue("5.5");
    await user.type(screen.getByPlaceholderText("e.g. 8.5"), "8.5");

    expect(screen.getByText("18", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Estimated fuel").parentElement).toHaveTextContent("1.53 L");
    expect(screen.getByText("Estimated emissions").parentElement).toHaveTextContent("3.5 kg CO₂e");

    await user.click(screen.getByRole("button", { name: "Save trip and emissions" }));
    await waitFor(() => expect(mocks.createActivity).toHaveBeenCalledWith(expect.objectContaining({
      category_id: "transport-id",
      activity_type: "car_petrol",
      quantity: "1.530000",
      unit: "L",
      notes: expect.stringContaining("Home, Lagos to Office, Lagos (12.5 km, about 15 min; OpenStreetMap route); Office, Lagos to Lunch stop, Lagos (5.5 km, about 6 min; OpenStreetMap route)"),
    })));
    expect(await screen.findByRole("status")).toHaveTextContent("18 km recorded");
    expect(window.localStorage.getItem("ecotrack:vehicle-fuel-economy")).toBe("8.5");
  });

  it("saves a manual distance after route lookup fails without duration", async () => {
    const user = userEvent.setup();
    mocks.activityOptions.mockResolvedValue(options);
    mocks.routeDistance.mockRejectedValue(new Error("The free route service is busy."));
    mocks.createActivity.mockResolvedValue({ calculated_co2e: "2.290572" });
    render(<TripPlanner />);

    await screen.findByRole("heading", { name: "Trip route" });
    await user.type(screen.getAllByPlaceholderText("Full address, city")[0], "Home, Lagos");
    await user.type(screen.getAllByPlaceholderText("Full address, city")[1], "Office, Lagos");
    await user.click(screen.getByRole("button", { name: "Calculate route" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The free route service is busy.");
    await user.type(screen.getByRole("spinbutton", { name: "Distance in kilometres for leg 1" }), "10");
    await user.type(screen.getByPlaceholderText("e.g. 8.5"), "8");

    expect(screen.getByText("Estimated driving time").parentElement).toHaveTextContent("Unavailable for manual legs");
    await user.click(screen.getByRole("button", { name: "Save trip and emissions" }));

    await waitFor(() => expect(mocks.createActivity).toHaveBeenCalledWith(expect.objectContaining({
      quantity: "0.800000",
      notes: expect.stringContaining("Home, Lagos to Office, Lagos (10 km; manual distance)"),
    })));
    expect(mocks.routeDistance).toHaveBeenCalledOnce();
  });
});
