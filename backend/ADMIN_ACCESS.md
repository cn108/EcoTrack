# Admin read-only API

The admin API provides a paginated user search and a read-only, filterable view of a selected user's activity. It is not a general account-management API.

## Configure the administrator

Set `ADMIN_EMAIL` in `backend/.env` to the email of an existing account:

```dotenv
ADMIN_EMAIL=admin@example.com
```

The configured account must also have `is_verified = true`. EcoTrack's current sign-up flow does not perform email verification, so only mark the account verified after you have independently confirmed control of the configured mailbox. For a local development database:

```bash
docker compose exec postgres psql -U ecotrack -d ecotrack \
  -c "UPDATE users SET is_verified = TRUE WHERE lower(email) = lower('admin@example.com');"
```

Restart the backend after changing its environment. If `ADMIN_EMAIL` is missing, or the signed-in account is not both the configured email and verified, every admin API request is denied. Do not use an email address that a public user can claim without independent ownership verification.

## Endpoints

- `GET /admin/users` — search email, first name, or last name; optionally filter account status and account-creation date; returns a paginated activity count, total recorded CO₂e, and latest activity date.
- `GET /admin/users/{user_id}/activities` — filter one user's activities by type, category, date range, and pagination. Results include quantities, calculated emissions, and factor provenance.

Both endpoints require the normal Bearer access token for the configured verified admin account. Page size is capped at 100. The activity response intentionally excludes free-text notes, route locations, and user-entered fuel prices. Admin reads are recorded in application logs by administrator ID, target user ID where applicable, and page metadata; search strings and user activity details are not logged.

This API is read-only: it cannot edit, disable, or delete accounts or activity records.
