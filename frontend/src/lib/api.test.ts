import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, ApiError, api, setAccessToken } from "./api";

describe("central API client", () => {
  afterEach(() => {
    setAccessToken(null);
    vi.unstubAllGlobals();
  });

  it("uses the configured API base URL and includes credentials", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", undefined);
    const { API_BASE_URL, api } = await import("./api");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "healthy" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.me().catch(() => undefined);

    expect(API_BASE_URL).toBe("http://localhost:8001");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/^http:\/\/localhost:8001\/auth\/me$/),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("supports a relative same-origin API proxy for production deployments", async () => {
    vi.resetModules();
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api/backend/");
    const { API_BASE_URL, api } = await import("./api");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "user-1" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.me();

    expect(API_BASE_URL).toBe("/api/backend");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/backend/auth/me",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("sends the in-memory access token as a Bearer header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "user-1" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("short-lived-access-token");

    await api.me();

    expect(fetchMock.mock.calls[0][1].headers.get("Authorization")).toBe(
      "Bearer short-lived-access-token",
    );
  });

  it("renews once on 401 and retries the protected request", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "renewed-token" }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-1" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("expired-token");

    await api.me();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toBe(`${API_BASE_URL}/auth/refresh`);
    expect(fetchMock.mock.calls[2][1].headers.get("Authorization")).toBe(
      "Bearer renewed-token",
    );
  });

  it("deduplicates concurrent session restoration requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: "restored-token", user: { id: "user-1" } }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const [first, second] = await Promise.all([api.refresh(), api.refresh()]);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(first.access_token).toBe("restored-token");
    expect(second.access_token).toBe("restored-token");
  });

  it("sends route calculations to the authenticated backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      distance_meters: 12500,
      distance_km: 12.5,
      duration_seconds: 900,
    }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("active-token");

    const result = await api.routeDistance({ origin: "Home, Lagos", destination: "Office, Lagos" });

    expect(result.distance_km).toBe(12.5);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/routes/distance`, expect.objectContaining({
      method: "POST",
      credentials: "include",
      body: JSON.stringify({ origin: "Home, Lagos", destination: "Office, Lagos" }),
    }));
    expect(fetchMock.mock.calls[0][1].headers.get("Authorization")).toMatch(/^Bearer /);
  });

  it("shares token rotation between session restoration and a protected request retry", async () => {
    let completeRefresh!: (response: Response) => void;
    const refreshResponse = new Promise<Response>((resolve) => {
      completeRefresh = resolve;
    });
    const fetchMock = vi.fn()
      .mockReturnValueOnce(refreshResponse)
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "user-1" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const restoring = api.refresh();
    const protectedRequest = api.me();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    completeRefresh(new Response(JSON.stringify({
      access_token: "rotated-token",
      user: { id: "user-1" },
    }), { status: 200 }));
    await Promise.all([restoring, protectedRequest]);

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[2][1].headers.get("Authorization")).toMatch(
      /^Bearer /,
    );
  });

  it("normalizes API errors without exposing response internals", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Not authorized" }), { status: 401 }),
      ),
    );
    setAccessToken(null);

    await expect(api.me()).rejects.toEqual(expect.objectContaining({
      name: "ApiError",
      message: "Not authorized",
      status: 401,
    } satisfies Partial<ApiError>));
  });

  it("reports timed out requests instead of leaving callers waiting indefinitely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("The operation timed out", "TimeoutError")),
    );

    await expect(api.me()).rejects.toEqual(expect.objectContaining({
      name: "ApiError",
      message: expect.stringContaining("reload to see whether it saved"),
      status: 408,
    } satisfies Partial<ApiError>));
  });
});