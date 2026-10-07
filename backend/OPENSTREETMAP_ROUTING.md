# OpenStreetMap routing

EcoTrack uses the public OpenStreetMap Nominatim geocoder and OSRM routing demo service for user-requested driving routes. No API key or billing account is required. The trip planner also supports manual distance entry if a public service is unavailable or a user prefers not to send location text to those services.

## Service behavior and attribution

- The backend sends location text entered by the user to Nominatim to find coordinates, then requests a driving route from OSRM.
- EcoTrack does not access device GPS or track live location.
- Nominatim requests are serialized to at most one per second per backend process. Successful geocoding results are cached in memory (up to 512 locations); the cache is lost when the API restarts.
- Requests have a 12-second timeout. Public services can be busy, rate-limit requests, change their policies, or become unavailable. They have no uptime guarantee and should not be treated as a production routing SLA.
- Display attribution wherever route results are shown: [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
- Review the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) and the [OSRM project documentation](https://github.com/Project-OSRM/osrm-backend) before increasing traffic. For a deployed or higher-traffic product, use a provider whose terms meet the product's needs, or operate a compliant geocoding/routing service.

## Optional service URL configuration

The defaults target the public demo services. A compatible endpoint can be selected in `backend/.env` without changing application code:

```dotenv
OSM_NOMINATIM_URL=https://nominatim.openstreetmap.org/search
OSM_ROUTING_URL=https://router.project-osrm.org/route/v1/driving
```

These settings do not require API credentials. Restart the backend after changing them.
