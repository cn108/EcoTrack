import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AboutView } from "./about-view";

describe("about methodology and sources", () => {
  it("explains calculation methods and lists references without loading account data", () => {
    render(<AboutView />);

    expect(screen.getByRole("heading", { name: "Calculation sources" })).toBeInTheDocument();
    expect(screen.getByText("Activity CO₂e = quantity × factor")).toBeInTheDocument();
    expect(screen.getByText(/six decimal places using half-up rounding/)).toBeInTheDocument();
    expect(screen.getByText(/Estimated fuel \(L\) = distance/)).toBeInTheDocument();
    expect(screen.getByText(/does not request, read, or display any account’s activities/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("Petrol burned")).not.toBeInTheDocument();

    const references = screen.getByRole("region", { name: "Emissions calculation references" });
    expect(within(references).getByRole("link", { name: /2006 IPCC Guidelines for National Greenhouse Gas Inventories/ }))
      .toHaveAttribute("href", "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html");
    expect(within(references).getByRole("link", { name: /Stationary Combustion, Chapter 2/ }))
      .toHaveAttribute("href", "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf");
    expect(within(references).getByRole("link", { name: /Ember electricity data/ }))
      .toHaveAttribute("href", "https://ourworldindata.org/grapher/electricity-mix.csv?frequency=annual&metric=carbon_intensity&source=total");
    expect(within(references).getByRole("link", { name: /Poore & Nemecek food emissions data/ }))
      .toHaveAttribute("href", "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv");

    expect(screen.getAllByRole("link", { name: /OpenStreetMap contributors/ })[0])
      .toHaveAttribute("href", "https://www.openstreetmap.org/copyright");
    expect(screen.getByRole("link", { name: "Nominatim usage policy" }))
      .toHaveAttribute("href", "https://operations.osmfoundation.org/policies/nominatim/");
    expect(screen.getByRole("link", { name: "OSRM backend documentation" }))
      .toHaveAttribute("href", "https://github.com/Project-OSRM/osrm-backend");
  });
});
