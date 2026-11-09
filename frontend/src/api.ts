/**
 * Fetch wrapper for authenticated, state-changing API requests.
 * Login itself uses ordinary fetch because no session exists yet.
 */

export async function apiFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const method = (init.method ?? "GET").toUpperCase();

  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    return fetch(input, init);
  }

  const tokenResponse = await fetch("/api/auth/csrf", {
    credentials: "same-origin",
    cache: "no-store",
  });

  if (!tokenResponse.ok) {
    throw new Error("Session expired. Please sign in again.");
  }

  const data: { csrf_token: string } = await tokenResponse.json();

  const headers = new Headers(init.headers);
  headers.set("X-CSRF-Token", data.csrf_token);

  return fetch(input, {
    ...init,
    headers,
    credentials: "same-origin",
  });
}
