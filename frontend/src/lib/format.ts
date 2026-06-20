import type { Json } from "./types";

// The candidate JSON columns arrive in inconsistent shapes depending on how a
// record was onboarded: a list, a dict of lists, or nested objects. This pulls
// out a flat list of human-readable strings regardless of shape.
export function toStringList(value: Json): string[] {
  const out: string[] = [];

  const walk = (v: unknown) => {
    if (v == null) return;
    if (typeof v === "string") {
      const s = v.trim();
      if (s) out.push(s);
    } else if (typeof v === "number" || typeof v === "boolean") {
      out.push(String(v));
    } else if (Array.isArray(v)) {
      v.forEach(walk);
    } else if (typeof v === "object") {
      Object.values(v as Record<string, unknown>).forEach(walk);
    }
  };

  walk(value);
  // De-duplicate while preserving order.
  return Array.from(new Set(out));
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Score from the backend is a cosine/cross-encoder value, roughly 0..1 but can
// drift slightly outside. Clamp for display.
export function clampScore(score: number | undefined): number {
  if (score == null || Number.isNaN(score)) return 0;
  return Math.max(0, Math.min(1, score));
}
