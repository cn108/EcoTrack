"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Calculator, CarFront, Plus, Route, Trash2 } from "lucide-react";

import { api, type ActivityOptions, type EmissionFactorOption } from "@/lib/api";

interface TripLeg {
  id: number;
  origin: string;
  destination: string;
  distanceKm: string;
  durationSeconds: number | null;
  distanceSource: "openstreetmap" | "manual" | null;
  routePending: boolean;
  routeError: string | null;
}

const ECONOMY_STORAGE_KEY = "ecotrack:vehicle-fuel-economy";
const FUEL_PRICE_STORAGE_KEY = "ecotrack:vehicle-fuel-price";

function localDateInputValue(date: Date) {
  const year = date.getFullYear().toString().padStart(4, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatNumber(value: number, maximumFractionDigits = 2) {
  return new Intl.NumberFormat("en-NG", { maximumFractionDigits }).format(value);
}

function formatNaira(value: number) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 2,
  }).format(value);
}

function initialLeg(): TripLeg {
  return {
    id: 1,
    origin: "",
    destination: "",
    distanceKm: "",
    durationSeconds: null,
    distanceSource: null,
    routePending: false,
    routeError: null,
  };
}

function tripNotes(legs: TripLeg[], totalDistanceKm: number, efficiency: number) {
  const route = legs
    .map((leg) => {
      const timing = leg.durationSeconds === null ? "" : `, ${formatDuration(leg.durationSeconds)}`;
      const source = leg.distanceSource === "manual" ? "manual distance" : "OpenStreetMap route";
      return `${leg.origin.trim()} to ${leg.destination.trim()} (${formatNumber(Number(leg.distanceKm))} km${timing}; ${source})`;
    })
    .join("; ");
  return `Driving trip (${formatNumber(totalDistanceKm)} km total; ${formatNumber(efficiency)} L/100 km): ${route}`;
}

function formatDuration(seconds: number) {
  if (seconds <= 0) return "—";
  const minutes = Math.max(1, Math.round(seconds / 60));
  if (minutes < 60) return `about ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes ? `about ${hours} hr ${remainingMinutes} min` : `about ${hours} hr`;
}

export function TripPlanner() {
  const [options, setOptions] = useState<ActivityOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [legs, setLegs] = useState<TripLeg[]>([initialLeg()]);
  const [nextLegId, setNextLegId] = useState(2);
  const [activityType, setActivityType] = useState("");
  const [fuelEconomy, setFuelEconomy] = useState("");
  const [unitCostNgn, setUnitCostNgn] = useState("");
  const [tripDate, setTripDate] = useState(() => localDateInputValue(new Date()));
  const [pending, setPending] = useState(false);
  const [savedSummary, setSavedSummary] = useState<string | null>(null);
  const routeRequestIds = useRef(new Map<number, number>());

  useEffect(() => {
    let mounted = true;
    api.activityOptions()
      .then((result) => {
        if (!mounted) return;
        setOptions(result);
        const carFactors = result.emission_factors.filter((factor) =>
          ["car_petrol", "car_diesel"].includes(factor.activity_type),
        );
        setActivityType((current) => current || carFactors[0]?.activity_type || "");
      })
      .catch((cause: unknown) => {
        if (mounted) setError(cause instanceof Error ? cause.message : "Vehicle options could not be loaded.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    try {
      const savedEconomy = window.localStorage.getItem(ECONOMY_STORAGE_KEY);
      const savedPrice = window.localStorage.getItem(FUEL_PRICE_STORAGE_KEY);
      void Promise.resolve().then(() => {
        if (!mounted) return;
        if (savedEconomy) setFuelEconomy(savedEconomy);
        if (savedPrice) setUnitCostNgn(savedPrice);
      });
    } catch {
      // The planner remains usable when browser storage is unavailable.
    }

    return () => {
      mounted = false;
    };
  }, []);

  const carFactors = options?.emission_factors.filter((factor) =>
    ["car_petrol", "car_diesel"].includes(factor.activity_type),
  ) ?? [];
  const selectedFactor: EmissionFactorOption | undefined = carFactors.find(
    (factor) => factor.activity_type === activityType,
  );
  const transportCategory = options?.categories.find((category) => category.name === "Transport");

  const totalDistanceKm = legs.reduce((total, leg) => {
    const distance = Number(leg.distanceKm);
    return Number.isFinite(distance) && distance > 0 ? total + distance : total;
  }, 0);
  const economy = Number(fuelEconomy);
  const estimatedFuelLitres = totalDistanceKm > 0 && economy > 0
    ? totalDistanceKm * economy / 100
    : 0;
  const estimatedCo2e = selectedFactor
    ? estimatedFuelLitres * Number(selectedFactor.factor_value)
    : 0;
  const estimatedSpend = unitCostNgn !== "" && Number(unitCostNgn) >= 0
    ? estimatedFuelLitres * Number(unitCostNgn)
    : null;
  const isLegsValid = legs.length > 0 && legs.every((leg) =>
    leg.origin.trim() && leg.destination.trim() &&
    Number.isFinite(Number(leg.distanceKm)) && Number(leg.distanceKm) > 0,
  );
  const canSave = Boolean(
    !loading && selectedFactor && transportCategory && isLegsValid &&
    Number.isFinite(economy) && economy > 0 && totalDistanceKm > 0 &&
    !legs.some((leg) => leg.routePending) && !pending,
  );

  function updateLeg(id: number, field: "origin" | "destination", value: string) {
    routeRequestIds.current.set(id, (routeRequestIds.current.get(id) ?? 0) + 1);
    setLegs((current) => current.map((leg) => leg.id === id
      ? {
          ...leg,
          [field]: value,
          ...(field === "origin" || field === "destination"
            ? { distanceKm: "", durationSeconds: null, distanceSource: null, routePending: false, routeError: null }
            : {}),
        }
      : leg));
  }

  function addLeg() {
    setLegs((current) => [...current, { ...initialLeg(), id: nextLegId }]);
    setNextLegId((current) => current + 1);
  }

  async function calculateRoute(leg: TripLeg) {
    const origin = leg.origin.trim();
    const destination = leg.destination.trim();
    if (origin.length < 2 || destination.length < 2) {
      setLegs((current) => current.map((item) => item.id === leg.id
        ? { ...item, routeError: "Enter both locations before calculating the route." }
        : item));
      return;
    }

    const requestId = (routeRequestIds.current.get(leg.id) ?? 0) + 1;
    routeRequestIds.current.set(leg.id, requestId);
    setLegs((current) => current.map((item) => item.id === leg.id
      ? { ...item, routePending: true, routeError: null }
      : item));

    try {
      const result = await api.routeDistance({ origin, destination });
      if (routeRequestIds.current.get(leg.id) !== requestId) return;
      setLegs((current) => current.map((item) => item.id === leg.id
        ? {
            ...item,
            distanceKm: String(result.distance_km),
            durationSeconds: result.duration_seconds,
            distanceSource: "openstreetmap",
            routePending: false,
            routeError: null,
          }
        : item));
    } catch (cause) {
      if (routeRequestIds.current.get(leg.id) !== requestId) return;
      setLegs((current) => current.map((item) => item.id === leg.id
        ? {
            ...item,
            routePending: false,
            routeError: cause instanceof Error ? cause.message : "OpenStreetMap could not calculate this route.",
          }
        : item));
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave || !selectedFactor || !transportCategory) return;
    setPending(true);
    setError(null);
    setSavedSummary(null);

    try {
      try {
        window.localStorage.setItem(ECONOMY_STORAGE_KEY, fuelEconomy);
        if (unitCostNgn) window.localStorage.setItem(FUEL_PRICE_STORAGE_KEY, unitCostNgn);
        else window.localStorage.removeItem(FUEL_PRICE_STORAGE_KEY);
      } catch {
        // Saving the trip does not depend on local browser preferences.
      }

      const quantity = estimatedFuelLitres.toFixed(6);
      const saved = await api.createActivity({
        category_id: transportCategory.id,
        activity_type: selectedFactor.activity_type,
        quantity,
        unit: selectedFactor.unit,
        activity_date: tripDate,
        unit_cost_ngn: unitCostNgn || null,
        notes: tripNotes(legs, totalDistanceKm, economy),
      });
      setSavedSummary(
        `${formatNumber(totalDistanceKm)} km recorded · ${formatNumber(Number(saved.calculated_co2e))} kg CO₂e`,
      );
      setLegs([initialLeg()]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Trip could not be saved.");
    } finally {
      setPending(false);
    }
  }

  const fuelLabel = selectedFactor?.activity_label
    .replace(/ burned$/i, "")
    .replace(/ used in a generator$/i, "") ?? "";

  return (
    <div className="trip-planner-page">
      <header className="page-heading">
        <div>
          <div className="eyebrow">Distance-based emissions</div>
          <h1>Trip planner</h1>
          <p>Use a free OpenStreetMap route estimate or enter the distance yourself, then add estimated fuel and emissions to your activity record.</p>
        </div>
      </header>

      {error && <div className="form-error activity-error" role="alert">{error}</div>}
      {savedSummary && <div className="form-success trip-saved" role="status">Trip saved: {savedSummary}</div>}

      <div className="trip-planner-layout">
        <form id="trip-form" className="panel trip-form" onSubmit={submit}>
          <div className="trip-section-heading">
            <span className="trip-section-icon"><Route size={19} /></span>
            <div>
              <h2>Trip route</h2>
              <p>Calculate a driving route or enter its distance manually for each part of your journey.</p>
            </div>
          </div>

          {loading ? (
            <div className="skeleton trip-options-skeleton" role="status" aria-label="Loading vehicle options" />
          ) : (
            <>
              <label className="field-label">Vehicle fuel
                <select required value={activityType} onChange={(event) => setActivityType(event.target.value)}>
                  {carFactors.map((factor) => (
                    <option key={factor.activity_type} value={factor.activity_type}>
                      {factor.activity_label.replace(/ burned$/i, "").replace(/ used in a generator$/i, "")}
                    </option>
                  ))}
                </select>
              </label>
              <div className="trip-leg-list">
                {legs.map((leg, index) => (
                  <fieldset className="trip-leg" key={leg.id}>
                    <legend>Leg {index + 1}</legend>
                    <div className="trip-leg-fields">
                      <label className="field-label">From
                        <input required maxLength={200} placeholder="Full address, city" value={leg.origin} onChange={(event) => updateLeg(leg.id, "origin", event.target.value)} />
                      </label>
                      <label className="field-label">To
                        <input required maxLength={200} placeholder="Full address, city" value={leg.destination} onChange={(event) => updateLeg(leg.id, "destination", event.target.value)} />
                      </label>
                      <label className="field-label trip-distance-field">Distance (km)
                        <input
                          aria-label={`Distance in kilometres for leg ${index + 1}`}
                          type="number"
                          min="0.01"
                          step="any"
                          inputMode="decimal"
                          placeholder="Enter distance or calculate"
                          value={leg.distanceKm}
                          onChange={(event) => {
                            routeRequestIds.current.set(leg.id, (routeRequestIds.current.get(leg.id) ?? 0) + 1);
                            setLegs((current) => current.map((item) => item.id === leg.id
                              ? {
                                  ...item,
                                  distanceKm: event.target.value,
                                  durationSeconds: null,
                                  distanceSource: event.target.value ? "manual" : null,
                                  routePending: false,
                                  routeError: null,
                                }
                              : item));
                          }}
                        />
                        {leg.distanceSource === "manual" && (
                          <span className="field-hint">Manually entered distance</span>
                        )}
                        {leg.distanceSource === "openstreetmap" && leg.durationSeconds !== null && (
                          <span className="field-hint">OpenStreetMap route · {formatDuration(leg.durationSeconds)}</span>
                        )}
                      </label>
                      <button
                        className="button-secondary trip-calculate-route"
                        type="button"
                        disabled={leg.routePending || !leg.origin.trim() || !leg.destination.trim()}
                        onClick={() => void calculateRoute(leg)}
                      >
                        <Route size={15} /> {leg.routePending ? "Calculating…" : "Calculate route"}
                      </button>
                      {legs.length > 1 && (
                        <button
                          className="icon-button trip-remove-leg"
                          type="button"
                          aria-label={`Remove leg ${index + 1}`}
                          onClick={() => setLegs((current) => current.filter((item) => item.id !== leg.id))}
                        >
                          <Trash2 size={17} />
                        </button>
                      )}
                    </div>
                    {leg.routeError && <div className="form-error trip-route-error" role="alert">{leg.routeError}</div>}
                  </fieldset>
                ))}
              </div>
              <button className="button-secondary trip-add-leg" type="button" onClick={addLeg} disabled={legs.length >= 20}>
                <Plus size={16} /> Add another leg
              </button>

              <div className="trip-settings-grid">
                <label className="field-label">Car fuel economy (L/100 km)
                  <input required type="number" min="0.1" step="any" inputMode="decimal" placeholder="e.g. 8.5" value={fuelEconomy} onChange={(event) => setFuelEconomy(event.target.value)} />
                  <span className="field-hint">We’ll remember this on this browser for next time.</span>
                </label>
                <label className="field-label">Date travelled
                  <input required type="date" value={tripDate} onChange={(event) => setTripDate(event.target.value)} />
                </label>
                <label className="field-label trip-price-field">Fuel price (₦ per litre, optional)
                  <input type="number" min="0" step="any" inputMode="decimal" placeholder="Use the price you paid" value={unitCostNgn} onChange={(event) => setUnitCostNgn(event.target.value)} />
                </label>
              </div>
            </>
          )}
        </form>

        <aside className="panel trip-estimate" aria-label="Trip emissions estimate">
          <div className="trip-section-heading">
            <span className="trip-section-icon"><Calculator size={19} /></span>
            <div>
              <h2>Journey estimate</h2>
              <p>{selectedFactor ? `${fuelLabel} · ${selectedFactor.source_name}` : "Estimated from your route and vehicle."}</p>
            </div>
          </div>
          <div className="trip-estimate-values">
            <div><span>Total distance</span><strong>{formatNumber(totalDistanceKm)} <small>km</small></strong></div>
            <div><span>Estimated driving time</span><strong>{legs.every((leg) => leg.durationSeconds !== null)
              ? formatDuration(legs.reduce((total, leg) => total + (leg.durationSeconds ?? 0), 0))
              : "Unavailable for manual legs"}</strong></div>
            <div><span>Estimated fuel</span><strong>{formatNumber(estimatedFuelLitres, 3)} <small>L</small></strong></div>
            <div className="trip-co2e-estimate"><span>Estimated emissions</span><strong>{formatNumber(estimatedCo2e)} <small>kg CO₂e</small></strong></div>
            {estimatedSpend !== null && <div><span>Estimated fuel cost</span><strong>{formatNaira(estimatedSpend)}</strong></div>}
          </div>
          <p className="trip-method-note">
            Estimate = total distance × your vehicle’s L/100 km ÷ 100. Emissions use EcoTrack’s selected fuel factor. Actual fuel use varies with traffic, vehicle condition, and driving style.
          </p>
          {selectedFactor && (
            <p className="trip-factor-note">
              Factor: {formatNumber(Number(selectedFactor.factor_value), 3)} kg CO₂e per L · {selectedFactor.region ?? "fuel-combustion estimate"}
            </p>
          )}
          <button className="button-primary trip-save-button" type="submit" form="trip-form" disabled={!canSave}>
            <CarFront size={17} /> {pending ? "Saving trip…" : "Save trip and emissions"}
          </button>
          <span className="trip-privacy-note">
            Route lookups send the locations you enter to the public OpenStreetMap Nominatim and OSRM services. EcoTrack does not access your GPS or track live location. Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>. Public services are free to use but have usage limits and no uptime guarantee; manual distance entry is always available.
          </span>
        </aside>
      </div>
    </div>
  );
}
