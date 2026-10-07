# Free portfolio deployment

This guide deploys EcoTrack as a public **portfolio/demo** using free tiers:

- [Vercel Hobby](https://vercel.com/pricing) for the Next.js frontend.
- [Render Free](https://render.com/docs/free) for the FastAPI backend.
- [Neon Free](https://neon.com/pricing) for PostgreSQL.

Free does not mean always-on or production-grade. Render Free services sleep after 15 minutes without inbound traffic and can take about a minute to wake. Render Free Postgres expires after 30 days, so do **not** use it for user data. Neon Free currently offers a persistent small Postgres database within its published quotas; review its current limits and back up anything important. Provider limits and terms can change. Vercel Hobby is intended for personal/non-commercial projects; check its current terms before using this deployment for a business.

Use this stack for a job-portfolio demo with test data, not for sensitive information or an app that needs guaranteed availability, support, or backups. Never promise users that free services are permanent or always available.

## 1. Put the project in your own GitHub repository

Both Vercel and Render can deploy from GitHub. Create a repository under your own account, then push the project to it. Choose public if you want employers to inspect the source; private works for deployment but reviewers won't be able to browse the code.

Before the first push:

- Confirm local `.env` and `.env.local` files, database dumps, and access tokens are not staged. The project `.gitignore` excludes environment files and local data.
- Keep `.env.example` free of real credentials.
- If a secret has ever been committed or shared, rotate it before deployment; deleting it from the latest version does not remove it from Git history.

## 2. Create a Neon database

1. Create a Neon account and a project in the free tier.
2. Copy the PostgreSQL connection string from the Neon dashboard. Keep the password private.
3. In Render's environment settings, set `DATABASE_URL` to the connection string, changing the driver prefix from `postgresql://` to `postgresql+psycopg://` if needed. Use Neon SSL settings from the generated connection string; do not paste the URL into chat, GitHub, or source files.

## 3. Deploy the FastAPI backend to Render

1. In Render, select **New → Blueprint** and connect the GitHub repository. Render reads [`render.yaml`](./render.yaml).
2. Provide `DATABASE_URL` in the Render dashboard when prompted. The blueprint generates a secret `SECRET_KEY`.
3. Wait for the backend deployment to finish. Render applies Alembic migrations at service start and checks `/health`.
4. Copy the backend's public URL, such as `https://ecotrack-api.onrender.com`. Open `/health` on that URL and confirm it returns `{"status":"healthy"}`.

Do not enable `ADMIN_EMAIL` for a public demo unless you have reviewed [admin access setup](./backend/ADMIN_ACCESS.md) and secured the configured, verified account.

## 4. Deploy the frontend to Vercel

1. Import the same repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Add these environment variables for Production (and Preview if desired):
   - `NEXT_PUBLIC_API_URL` = `/api/backend`
   - `BACKEND_API_URL` = the Render backend URL from step 3, with no trailing slash.
4. Deploy. Next.js proxies `/api/backend/...` to FastAPI, keeping the browser API and secure refresh cookie same-origin. Do not set `NEXT_PUBLIC_API_URL` to the Render URL; direct cross-site cookies can be blocked by browsers.
5. Visit the Vercel URL, register a test account, sign in, create an activity, refresh the page, and confirm the saved activity remains. Also test logout/login and a route lookup after the Render service has slept.

## 5. Keep the public demo safe and free

- Start with fictional/demo data. Do not invite people to enter sensitive location details or private information into a hobby deployment.
- Do not set up billing or add a payment method unless you intentionally accept possible charges. Check each provider's account spend/usage controls where available.
- Check Render, Neon, and Vercel usage dashboards periodically; free quotas, availability, and product terms can change.
- Expect the first API request after idle to be slow while Render wakes.
- Render's filesystem is ephemeral. The database is on Neon; never store user records or uploads on the backend filesystem.
- The public Nominatim and OSRM services have their own usage policies and no uptime guarantee. Keep route lookups user-initiated and manual distance entry available.
- Before moving beyond a portfolio demo, arrange a maintained database with backups, service monitoring, email verification and account recovery, privacy disclosures/data deletion, abuse controls, and a budget for reliable hosting.

## Troubleshooting authentication

The production refresh cookie is `Secure`, `HttpOnly`, `SameSite=Strict`, and scoped to `/api/backend/auth`. Keep `REFRESH_COOKIE_PATH` in Render aligned with the public Vercel proxy path. If the API responds successfully but sign-in does not persist after a browser refresh, inspect the browser's Network panel for the `/api/backend/auth/refresh` request and check the Render environment setting; do not weaken the cookie to cross-site `SameSite=None` as a workaround.
