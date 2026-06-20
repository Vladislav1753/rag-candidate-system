import { type NextRequest, NextResponse } from "next/server";

// Runtime proxy to the FastAPI backend. This must run per-request (not via
// next.config rewrites, whose destinations are frozen at build time) so that
// BACKEND_URL is read live — e.g. http://backend:8000 inside Docker Compose,
// http://localhost:8000 in local dev.
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function backendUrl(): string {
  return process.env.BACKEND_URL ?? "http://localhost:8000";
}

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const target = `${backendUrl()}/${path.join("/")}${req.nextUrl.search}`;

  // Forward incoming headers minus hop-by-hop / host ones that must be
  // recomputed by fetch for the upstream connection.
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const body = hasBody ? await req.arrayBuffer() : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      redirect: "manual",
    });
  } catch {
    return NextResponse.json(
      { detail: "Backend is unreachable." },
      { status: 502 },
    );
  }

  const resHeaders = new Headers(upstream.headers);
  resHeaders.delete("content-encoding");
  resHeaders.delete("content-length");
  resHeaders.delete("transfer-encoding");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: resHeaders,
  });
}

type Ctx = { params: Promise<{ path: string[] }> };

async function handler(req: NextRequest, ctx: Ctx): Promise<NextResponse> {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export {
  handler as GET,
  handler as POST,
  handler as PUT,
  handler as PATCH,
  handler as DELETE,
};
