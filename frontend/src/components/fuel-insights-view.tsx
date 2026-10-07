"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowDownRight, Lightbulb, Sun } from "lucide-react";

import { api, type FuelInsight } from "@/lib/api";

const FUEL_LABELS: Record<string, string> = {
  car_petrol: "Vehicle petrol",
  car_diesel: "Vehicle diesel",
  generator_petrol: "Generator petrol",
  generator_diesel: "Generator diesel",
  cooking_lpg: "Cooking LPG",
  cooking_kerosene: "Cooking kerosene",
};

function formatNaira(value: number) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatNumber(value: number, digits = 2) {
  return new Intl.NumberFormat("en-NG", {
    maximumFractionDigits: digits,
  }).format(value);
}

function alternativeFor(activityType: string) {
  if (activityType.startsWith("generator_")) {
    return {
      title: "Alternative to investigate: solar plus battery",
      detail:
        "For essential loads, compare a correctly sized solar-and-battery quote with your recorded generator spending. It can avoid on-site generator fuel use while covered by solar or stored power; equipment cost, battery replacement, and lifecycle emissions are not included in this estimate.",
    };
  }
  if (activityType.startsWith("cooking_")) {
    return {
      title: "Lower-fuel option to investigate",
      detail:
        "A well-fitting pot lid, batch cooking, or a pressure cooker where reliable electricity is available may reduce fuel needed for the same meals. Results depend on cooking habits and equipment; compare your own costs before switching.",
    };
  }
  return {
    title: "Lower-cost travel option to investigate",
    detail:
      "Combining trips or using public transport where safe and available may reduce fuel use. Route, fares, access, and travel time vary, so compare with your own situation.",
  };
}

function FuelCard({ fuel }: { fuel: FuelInsight }) {
  const totalCost = Number(fuel.total_cost_ngn);
  const totalCo2e = Number(fuel.total_co2e);
  const alternative = alternativeFor(fuel.activity_type);

  return (
    <article className="panel fuel-insight-card">
      <div className="fuel-insight-top">
        <div>
          <span className="section-kicker">{fuel.activity_count} priced {fuel.activity_count === 1 ? "entry" : "entries"}</span>
          <h2>{FUEL_LABELS[fuel.activity_type] ?? fuel.activity_type.replaceAll("_", " ")}</h2>
        </div>
        <div className="fuel-insight-spend">
          <span>Recorded spend</span>
          <strong className="fuel-insight-total">{formatNaira(totalCost)}</strong>
        </div>
      </div>
      <div className="fuel-insight-metrics">
        <div className="fuel-insight-metric">
          <span>Fuel logged</span>
          <strong>{formatNumber(Number(fuel.total_quantity))} {fuel.unit}</strong>
        </div>
        <div className="fuel-insight-metric">
          <span>Direct fuel emissions</span>
          <strong>{formatNumber(totalCo2e)} <small>kg CO₂e</small></strong>
        </div>
      </div>
      <div className="fuel-scenario">
        <ArrowDownRight size={20} aria-hidden="true" />
        <div>
          <strong>What if you used 10% less?</strong>
          <p>Illustrative scenario: about {formatNaira(totalCost * 0.1)} less spend and {formatNumber(totalCo2e * 0.1)} kg less direct fuel CO₂e over the same recorded entries.</p>
        </div>
      </div>
      <div className="fuel-alternative">
        {fuel.activity_type.startsWith("generator_") ? <Sun size={20} aria-hidden="true" /> : <Lightbulb size={20} aria-hidden="true" />}
        <div>
          <strong>{alternative.title}</strong>
          <p>{alternative.detail}</p>
        </div>
      </div>
    </article>
  );
}

export function FuelInsightsView() {
  const [fuels, setFuels] = useState<FuelInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.fuelInsights()
      .then((result) => {
        if (mounted) setFuels(result.fuels);
      })
      .catch((cause: unknown) => {
        if (mounted) setError(cause instanceof Error ? cause.message : "Fuel insights could not be loaded.");
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="fuel-insights-page">
      <header className="page-heading">
        <div>
          <div className="eyebrow">Your choices, your prices</div>
          <h1>Fuel insights</h1>
          <p>Explore possible savings using the prices you entered—not national averages.</p>
        </div>
      </header>

      {error && <div className="form-error activity-error" role="alert">{error}</div>}
      <div className="fuel-insights-note panel">
        <strong>How to read these estimates</strong>
        Estimates use only fuel entries with a price you supplied. A 10% reduction is a scenario, not a promised saving. Alternatives are ideas to compare—not a claim that they will be cheaper for every household.
      </div>

      {loading ? (
        <div className="fuel-insights-grid" role="status" aria-label="Loading fuel insights">
          {[1, 2].map((item) => <div className="skeleton fuel-insight-skeleton" key={item} />)}
        </div>
      ) : fuels.length ? (
        <div className="fuel-insights-grid">
          {fuels.map((fuel) => <FuelCard key={`${fuel.activity_type}-${fuel.unit}`} fuel={fuel} />)}
        </div>
      ) : (
        <section className="empty-dashboard panel">
          <div className="empty-emblem"><Lightbulb size={25} /></div>
          <span className="section-kicker">Personalized estimates need your prices</span>
          <h2>No fuel prices recorded yet</h2>
          <p>When logging petrol, diesel, LPG, or kerosene, optionally enter the price you paid per litre or kilogram. You can still track activities without entering a price.</p>
          <Link className="button-primary" href="/activities">Add a fuel activity</Link>
        </section>
      )}
    </div>
  );
}
