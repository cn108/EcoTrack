const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_URL;
export const API_BASE_URL = configuredApiBaseUrl === undefined
  ? "http://localhost:8001"
  : configuredApiBaseUrl.replace(/\/+$/, "");

export type DecimalValue = string;

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  country: string | null;
  timezone: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface CategoryOption {
  id: string;
  name: string;
}

export interface EmissionFactorOption {
  id: string;
  category: string;
  activity_type: string;
  activity_label: string;
  unit: string;
  unit_label: string;
  factor_value: DecimalValue;
  co2e_unit: string;
  source_name: string;
  source_url: string | null;
  source_year: number;
  region: string | null;
}

export interface ActivityOptions {
  categories: CategoryOption[];
  emission_factors: EmissionFactorOption[];
}

export interface Activity {
  id: string;
  category: CategoryOption;
  activity_type: string;
  quantity: DecimalValue;
  unit: string;
  activity_date: string;
  calculated_co2e: DecimalValue;
  unit_cost_ngn: DecimalValue | null;
  emission_factor: {
    id: string;
    factor_value: DecimalValue;
    factor_unit: string;
    co2e_unit: string;
    source_name: string;
    source_url: string | null;
    source_year: number;
    region: string | null;
  };
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryEmission {
  category_id: string;
  category_name: string;
  total_co2e: DecimalValue;
  activity_count: number;
}

export interface MonthlyEmission {
  month: string;
  total_co2e: DecimalValue;
  activity_count: number;
}

export interface ActivityTypeEmission {
  activity_type: string;
  total_co2e: DecimalValue;
  activity_count: number;
}

export interface DashboardData {
  current_month_total_co2e: DecimalValue;
  previous_month_total_co2e: DecimalValue;
  percentage_change_percent: DecimalValue | null;
  daily_average_co2e: DecimalValue;
  activities_this_month: number;
  highest_emission_category: CategoryEmission | null;
  highest_emission_activity_type: ActivityTypeEmission | null;
  category_totals: CategoryEmission[];
  recent_activities: Activity[];
}

export interface Goal {
  id: string;
  name: string;
  target_type: string;
  baseline_co2e: DecimalValue;
  target_co2e: DecimalValue;
  start_date: string;
  end_date: string;
  is_completed: boolean;
  current_co2e: DecimalValue;
  progress_percent: DecimalValue;
  remaining_co2e: DecimalValue;
  created_at: string;
  updated_at: string;
}

export interface ActivityPayload {
  category_id: string;
  activity_type: string;
  quantity: string;
  unit: string;
  activity_date: string;
  unit_cost_ngn?: string | null;
  notes?: string | null;
}

export interface FuelInsight {
  activity_type: string;
  unit: string;
  activity_count: number;
  total_quantity: DecimalValue;
  total_cost_ngn: DecimalValue;
  total_co2e: DecimalValue;
}

export interface FuelInsights {
  fuels: FuelInsight[];
}

export interface RouteDistance {
  distance_meters: number;
  distance_km: number;
  duration_seconds: number;
}

export interface GoalPayload {
  name: string;
  target_type: string;
  baseline_co2e: string;
  target_co2e: string;
  start_date: string;
  end_date: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const REQUEST_TIMEOUT_MS = 20_000;
let accessToken: string | null = null;
let refreshInFlight: Promise<AuthResponse> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

async function readError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    const detail = body.detail;
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail) && typeof detail[0]?.msg === "string") {
      message = detail[0].msg;
    }
  } catch {
    // Keep the generic status message when an error response isn't JSON.
  }
  return new ApiError(message, response.status);
}

function refreshSession(): Promise<AuthResponse> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
    if (!response.ok) {
      throw new ApiError("Session refresh failed", response.status);
    }
    const result = (await response.json()) as AuthResponse;
    accessToken = result.access_token;
    return result;
  })();
  refreshInFlight = refreshInFlight.finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

async function renewAccessToken(): Promise<string | null> {
  try {
    return (await refreshSession()).access_token;
  } catch {
    accessToken = null;
    window.dispatchEvent(new Event("ecotrack:unauthorized"));
    return null;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: { skipAuth?: boolean; allowRefresh?: boolean } = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!options.skipAuth && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      credentials: "include",
      signal: init.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "TimeoutError") {
      throw new ApiError(
        "This request timed out. Check your connection, then reload to see whether it saved.",
        408,
      );
    }
    throw cause;
  }
  if (
    response.status === 401 &&
    !options.skipAuth &&
    options.allowRefresh !== false &&
    !["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"].includes(path)
  ) {
    const renewed = await renewAccessToken();
    if (renewed) return request<T>(path, init, { ...options, allowRefresh: false });
  }
  if (!response.ok) throw await readError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}

export const api = {
  register: (payload: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) =>
    request<User>("/auth/register", {
      method: "POST",
      body: jsonBody(payload),
    }, { skipAuth: true }),
  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: jsonBody(payload),
    }, { skipAuth: true }),
  refresh: () => refreshSession(),
  logout: () => request<void>("/auth/logout", { method: "POST" }, { skipAuth: true }),
  me: () => request<User>("/auth/me"),
  dashboard: () => request<DashboardData>("/dashboard"),
  monthlyEmissions: (startDate: string, endDate: string) =>
    request<MonthlyEmission[]>(
      `/analytics/monthly?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    ),
  categoryEmissions: () => request<CategoryEmission[]>("/analytics/categories"),
  activityTypeEmissions: () =>
    request<ActivityTypeEmission[]>("/analytics/activity-types"),
  fuelInsights: () => request<FuelInsights>("/insights/fuel"),
  routeDistance: (payload: { origin: string; destination: string }) =>
    request<RouteDistance>("/routes/distance", {
      method: "POST",
      body: jsonBody(payload),
    }),
  activityOptions: () => request<ActivityOptions>("/activity-options"),
  activities: (query: URLSearchParams) =>
    request<Activity[]>(`/activities?${query.toString()}`),
  createActivity: (payload: ActivityPayload) =>
    request<Activity>("/activities", {
      method: "POST",
      body: jsonBody(payload),
    }),
  updateActivity: (id: string, payload: Partial<ActivityPayload>) =>
    request<Activity>(`/activities/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: jsonBody(payload),
    }),
  deleteActivity: (id: string) =>
    request<void>(`/activities/${encodeURIComponent(id)}`, { method: "DELETE" }),
  goals: () => request<Goal[]>("/goals"),
  createGoal: (payload: GoalPayload) =>
    request<Goal>("/goals", {
      method: "POST",
      body: jsonBody(payload),
    }),
  updateGoal: (id: string, payload: Partial<GoalPayload>) =>
    request<Goal>(`/goals/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: jsonBody(payload),
    }),
  deleteGoal: (id: string) =>
    request<void>(`/goals/${encodeURIComponent(id)}`, { method: "DELETE" }),
};