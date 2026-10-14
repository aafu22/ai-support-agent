export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Options = Omit<RequestInit, "body"> & { json?: unknown; form?: FormData };

/** The only place the frontend talks to the backend. Requests go to /api/*, which Next.js proxies. */
export async function api<T = unknown>(path: string, { json, form, ...init }: Options = {}): Promise<T> {
  const headers = new Headers(init.headers);
  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  } else if (form) {
    body = form; // browser sets the multipart boundary
  }
  const res = await fetch(`/api${path}`, { ...init, headers, body, credentials: "same-origin" });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {}
    throw new ApiError(res.status, message);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
