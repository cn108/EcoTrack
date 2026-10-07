# EcoTrack

**A full-stack sustainability app for understanding the emissions behind everyday choices.**

EcoTrack lets people track household and travel activities, estimate their carbon emissions, set goals, and explore how changes to their routines could affect their footprint. It is designed with Nigeria as its initial product context and built as an end-to-end portfolio project.

### Try the live app

**[Open EcoTrack](https://eco-track-1wen2cuxa-eco-track3.vercel.app)** · [View the source code](https://github.com/cn108/EcoTrack)

Create an account to explore the app. The public demo runs on free-tier hosting, so the first request may take a little time while the backend wakes up. Please use demo data rather than sensitive personal information.

## Product capabilities

- **Personal accounts:** registration and sign-in, with activity and goals scoped to the signed-in user.
- **Emissions tracking:** record transport, household energy, food, travel, waste, and purchases; view estimates based on documented emission factors.
- **Goals and progress:** set targets and see progress toward them.
- **Trip planning:** build a multi-leg car journey and estimate distance, fuel use, emissions, and optional spend using the vehicle efficiency and fuel price provided by the user.
- **Open routing:** look up driving routes using OpenStreetMap geocoding and OSRM, with manual distance entry as a fallback.
- **Fuel insights:** compare estimated fuel costs using prices entered by the user.
- **Calculation transparency:** review calculation methods, factor sources, and limitations in the app.

## Engineering highlights

- Built and deployed a complete web application: Next.js frontend, FastAPI backend, PostgreSQL database, and cloud hosting.
- Validates and calculates activity emissions on the backend using sourced factors; the browser does not supply the final emissions result.
- Uses authenticated API requests, protected user data, database migrations, and an optional read-only admin API with privacy boundaries.
- Routes browser API calls through a same-origin Next.js proxy to support secure refresh cookies in the deployed app.
- Includes automated frontend and backend tests, linting, and a production build in GitHub Actions.
- Uses OpenStreetMap-based route estimates rather than a paid Google Maps API. EcoTrack does not access device GPS or track live location.

## What it does

- Account registration and sign-in, with protected personal activity and goal data.
- Activity tracking for transport, household energy, food, travel, waste, and purchases.
- Emissions calculations backed by named, sourced emission factors.
- Goals with progress rings and clear target status.
- Fuel insights based on prices users enter themselves; estimates are labelled and do not promise an alternative will be cheaper.
- A multi-leg trip planner that estimates fuel, emissions, and optional spend from distance and the user's vehicle efficiency.
- Driving-route estimates through public OpenStreetMap Nominatim and OSRM services, with manual distance entry when routing is unavailable.

## Technology

- **Frontend:** Next.js App Router, React, TypeScript, CSS, Vitest, and Testing Library.
- **Backend:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, and Alembic.
- **Data services:** PostgreSQL and Redis for local development.
- **Routing:** OpenStreetMap Nominatim geocoding and OSRM route estimates; no Google Maps API key is required.

## Architecture at a glance

```text
Browser (Next.js :3000)
        │ authenticated API requests
        ▼
FastAPI (:8001) ───── PostgreSQL (:5432)
        │
        └── user-requested route lookup → Nominatim / OSRM

Redis (:6379) is available in the local development stack.
```

The browser submits activity quantities; the backend validates them and calculates emissions using the selected factor. Route lookup is proxied by the backend. EcoTrack does not access device GPS or track live location.

## Run locally (Ubuntu / WSL)

Requirements: Docker Compose, Node.js 22 or newer, and [uv](https://docs.astral.sh/uv/).

1. Start the local data services from the project root:

   ```bash
   docker compose up -d postgres redis
   ```

2. Configure and migrate the backend:

   ```bash
   cd backend
   cp ../.env.example .env
   uv sync --locked
   uv run alembic upgrade head
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

3. In a second terminal, configure and start the frontend:

   ```bash
   cd frontend
   cp .env.example .env.local
   npm ci
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) and create an account.

Keep local `.env` files private; use `.env.example` only as a template. The backend API is available at [http://localhost:8001](http://localhost:8001), with interactive docs at `/docs`.

## Checks

The GitHub Actions workflow runs frontend linting, tests, and a production build, and runs the backend tests against a temporary PostgreSQL database after applying migrations.

Run the same checks locally:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

```bash
cd backend
uv sync --locked
uv run alembic upgrade head
uv run python -m unittest discover -s tests -p 'test_*.py' -v
```

Backend tests that use the database need PostgreSQL running and `DATABASE_URL` configured as in `.env.example`.

## Admin API

An optional, read-only admin API can search user accounts and filter a user's activity records. It is disabled until `ADMIN_EMAIL` is configured and the matching existing account is explicitly verified. See [admin access setup](backend/ADMIN_ACCESS.md) for the access requirements, endpoints, and privacy boundaries.

## Deploy the portfolio demo

See [DEPLOYMENT.md](DEPLOYMENT.md) for a Vercel + Render + Neon free-tier deployment walkthrough and its sleep, usage, and data-safety limitations.

## Emissions and routing limitations

- Emission estimates depend on the selected factor and entered quantity. Factors include their source and scope; regional/global defaults are not necessarily Nigeria-specific.
- Transport fuel estimates use the factor's stated scope and should not be mistaken for a full lifecycle assessment. Real-world emissions vary.
- Route estimates depend on public geocoding/routing data and do not model live traffic, idling, or actual fuel consumption. The planner estimates fuel from the user's L/100 km input.
- Public OpenStreetMap services are free to use but have usage policies, rate limits, and no uptime guarantee. A route lookup sends the entered location text to those services. Users can enter a distance manually instead.
- See [OpenStreetMap routing notes](backend/OPENSTREETMAP_ROUTING.md) and the [OpenStreetMap attribution page](https://www.openstreetmap.org/copyright).

## Project status

EcoTrack is a portfolio and learning project. It is not a production-ready carbon-accounting or navigation system. Before a public deployment, review privacy and data-retention requirements, security hardening, observability, database backups, and routing-service terms and capacity.
