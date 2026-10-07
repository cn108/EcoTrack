import { BookOpenText, Calculator, CarFront, CircleHelp, ExternalLink, Leaf, Scale } from "lucide-react";
import type { ReactNode } from "react";

const calculationSources = [
  {
    name: "2006 IPCC Guidelines for National Greenhouse Gas Inventories — Energy, Volume 2",
    detail: "Motor gasoline and gas/diesel oil combustion factors. EcoTrack uses global default factors for direct fuel combustion; they are not full fuel lifecycle estimates.",
    year: "2006",
    url: "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html",
  },
  {
    name: "2006 IPCC Guidelines — Stationary Combustion, Chapter 2",
    detail: "Combustion guidance used for LPG and kerosene household-fuel defaults; the application records its unit conversions and direct-combustion scope in factor metadata.",
    year: "2006",
    url: "https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf",
  },
  {
    name: "Ember electricity data, via Our World in Data",
    detail: "Electricity carbon-intensity factor uses an Africa-wide regional proxy. It is not a Nigeria-specific grid measurement.",
    year: "2024",
    url: "https://ourworldindata.org/grapher/electricity-mix.csv?frequency=annual&metric=carbon_intensity&source=total",
  },
  {
    name: "Poore & Nemecek food emissions data, via Our World in Data",
    detail: "Food factors use global supply-chain averages. Results can vary substantially with local production, sourcing, and food-system boundaries.",
    year: "2018",
    url: "https://ourworldindata.org/grapher/food-emissions-supply-chain.csv",
  },
];

const routingSources = [
  {
    name: "OpenStreetMap contributors",
    detail: "Map data and attribution for driving route lookups.",
    url: "https://www.openstreetmap.org/copyright",
  },
  {
    name: "Nominatim usage policy",
    detail: "Geocoding service and public-service usage limits.",
    url: "https://operations.osmfoundation.org/policies/nominatim/",
  },
  {
    name: "OSRM backend documentation",
    detail: "Open-source driving-route service used by the trip planner.",
    url: "https://github.com/Project-OSRM/osrm-backend",
  },
];

function SourceLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}<ExternalLink size={13} aria-hidden="true" />
    </a>
  );
}

export function AboutView() {
  return (
    <div className="about-page">
      <header className="page-heading about-heading">
        <div>
          <span className="eyebrow">Open methods · sourced factors</span>
          <h1>About EcoTrack</h1>
          <p>How your footprint is estimated, where the numbers come from, and what they can—and cannot—tell you.</p>
        </div>
      </header>

      <section className="about-principle panel" aria-labelledby="about-principle-title">
        <span className="about-principle-icon"><Leaf size={23} /></span>
        <div>
          <h2 id="about-principle-title">Useful estimates, with their assumptions in view</h2>
          <p>EcoTrack is designed to make everyday activity easier to understand. Estimates depend on what is entered and on the coverage and scope of each published factor; they are not a personal measurement or a verified carbon inventory.</p>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-method-title">
        <div className="about-section-heading">
          <span className="about-section-icon"><Calculator size={19} /></span>
          <div>
            <span className="eyebrow">The method</span>
            <h2 id="about-method-title">How activity emissions are calculated</h2>
          </div>
        </div>
        <div className="about-method-grid">
          <article className="panel about-method-card">
            <span className="about-card-number">01</span>
            <h3>Choose a matching factor</h3>
            <p>The backend selects one active factor for the activity category, activity type, and entered unit. Unsupported units and ambiguous matches are rejected rather than guessed.</p>
          </article>
          <article className="panel about-method-card">
            <span className="about-card-number">02</span>
            <h3>Multiply quantity by factor</h3>
            <p><code>Activity CO₂e = quantity × factor</code>. For example, litres of fuel are multiplied by that fuel’s kg CO₂e-per-litre factor. The calculation is performed server-side using decimal arithmetic.</p>
          </article>
          <article className="panel about-method-card">
            <span className="about-card-number">03</span>
            <h3>Store a consistent result</h3>
            <p>Each result is rounded to six decimal places using half-up rounding and saved with the selected factor reference. Charts and summaries aggregate these saved results.</p>
          </article>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-trips-title">
        <div className="about-section-heading">
          <span className="about-section-icon"><CarFront size={19} /></span>
          <div>
            <span className="eyebrow">Travel estimates</span>
            <h2 id="about-trips-title">How the trip planner works</h2>
          </div>
        </div>
        <div className="panel about-explanation">
          <p>For each leg, the planner uses a driving distance from OpenStreetMap’s Nominatim geocoder and OSRM routing service, or a distance you enter yourself. It estimates fuel from your car’s stated efficiency:</p>
          <p className="about-formula"><code>Estimated fuel (L) = distance (km) × fuel economy (L/100 km) ÷ 100</code></p>
          <p>Estimated fuel is then multiplied by the selected fuel factor. This is a planning estimate, not a live GPS track or a vehicle readout. Public routes may not represent the route you actually drove and do not include real-time congestion, idling, vehicle condition, or driving style. Route lookup sends entered location text to those public services; manual distance entry remains available.</p>
          <p className="about-attribution">Route data: <SourceLink href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</SourceLink>.</p>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-goals-title">
        <div className="about-section-heading">
          <span className="about-section-icon"><Scale size={19} /></span>
          <div>
            <span className="eyebrow">Progress tracking</span>
            <h2 id="about-goals-title">Goals, costs, and comparisons</h2>
          </div>
        </div>
        <div className="about-method-grid about-method-grid-two">
          <article className="panel about-method-card">
            <h3>Goal progress</h3>
            <p>Current emissions are the sum of saved activity emissions inside the goal’s date range. Planned reduction progress is <code>(baseline − current) ÷ (baseline − target) × 100</code>, displayed between 0% and 100%. A goal is met when current emissions are at or below its target.</p>
          </article>
          <article className="panel about-method-card">
            <h3>Fuel spend and scenarios</h3>
            <p>Fuel spend is estimated as entered quantity × the per-unit price you provide in naira. The 10% reduction shown in Fuel Insights is an illustrative scenario applied to recorded priced use; it is not a forecast. Different fuels may not be directly comparable for the same service.</p>
          </article>
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-sources-title">
        <div className="about-section-heading">
          <span className="about-section-icon"><BookOpenText size={19} /></span>
          <div>
            <span className="eyebrow">Evidence behind the estimates</span>
            <h2 id="about-sources-title">Calculation sources</h2>
          </div>
        </div>
        <p className="about-source-intro">These references describe the public datasets and guidance used by EcoTrack. This page is a static methodology and bibliography page: it does not request, read, or display any account’s activities or profile data.</p>
        <div className="about-source-list" role="region" aria-label="Emissions calculation references">
          {calculationSources.map((source) => (
            <article className="panel about-source-card" key={source.url}>
              <div className="about-source-title">
                <h3><SourceLink href={source.url}>{source.name}</SourceLink></h3>
                <span className="about-source-year">{source.year}</span>
              </div>
              <p>{source.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="about-section" aria-labelledby="about-routing-sources-title">
        <div className="about-section-heading">
          <span className="about-section-icon"><CarFront size={19} /></span>
          <div>
            <span className="eyebrow">Routes and attribution</span>
            <h2 id="about-routing-sources-title">Routing and map references</h2>
          </div>
        </div>
        <div className="about-source-list about-source-list-routing">
          {routingSources.map((source) => (
            <article className="panel about-source-card" key={source.url}>
              <h3><SourceLink href={source.url}>{source.name}</SourceLink></h3>
              <p>{source.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <aside className="about-caveat" aria-label="Important limitations">
        <CircleHelp size={19} />
        <div>
          <strong>Interpret results in context</strong>
          <p>Some factors are global or regional proxies rather than Nigeria-specific measurements. Fuel factors generally describe direct combustion; food and other factors may use broader life-cycle boundaries. Read the source descriptions before comparing categories. EcoTrack is an educational tracker, not regulatory reporting or a substitute for a full lifecycle assessment.</p>
        </div>
      </aside>
    </div>
  );
}
