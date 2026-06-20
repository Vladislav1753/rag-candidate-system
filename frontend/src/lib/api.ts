import type {
  ExpandResponse,
  ExtractResponse,
  OnboardingPayload,
  SearchParams,
  SearchResponse,
} from "./types";

// All requests go to the same-origin /api proxy (see next.config.ts), which
// forwards to the FastAPI backend.
const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail.map((d: { msg?: string }) => d.msg).join(", ");
  } catch {
    /* fall through to status text */
  }
  return res.statusText || "Request failed";
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(await readError(res), res.status);
  return res.json() as Promise<T>;
}

export function searchCandidates(params: SearchParams): Promise<SearchResponse> {
  return postJson<SearchResponse>("/candidates", params);
}

export function expandQuery(query: string): Promise<ExpandResponse> {
  return postJson<ExpandResponse>("/queries/expand", { query });
}

export function onboardCandidate(
  payload: OnboardingPayload,
): Promise<{ status: string; candidate_id: string }> {
  return postJson("/candidates/onboarding", payload);
}

export async function extractResume(file: File): Promise<ExtractResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/cvs/extract`, { method: "POST", body: form });
  if (!res.ok) throw new ApiError(await readError(res), res.status);
  return res.json() as Promise<ExtractResponse>;
}
