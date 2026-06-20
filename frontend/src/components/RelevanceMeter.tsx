import { clampScore } from "@/lib/format";

const SEGMENTS = 14;

// The signature element: a segmented gauge encoding the match score the RAG
// pipeline actually computes (cosine retrieval + cross-encoder rerank).
export function RelevanceMeter({ score }: { score: number | undefined }) {
  const s = clampScore(score);
  const filled = Math.round(s * SEGMENTS);
  const pct = Math.round(s * 100);

  return (
    <div className="flex flex-col items-end gap-1.5" aria-hidden>
      <div className="flex items-end gap-[3px]">
        {Array.from({ length: SEGMENTS }).map((_, i) => {
          const on = i < filled;
          return (
            <span
              key={i}
              className={`w-[3px] rounded-full transition-colors ${
                on ? "bg-cobalt" : "bg-line-strong"
              }`}
              // Slight ramp so the meter reads as a rising signal, not a flat bar.
              style={{ height: `${8 + (i / (SEGMENTS - 1)) * 12}px` }}
            />
          );
        })}
      </div>
      <span className="data text-[11px] text-muted">
        <span className="font-bold text-cobalt">{pct}</span>
        <span className="text-faint"> / 100 match</span>
      </span>
    </div>
  );
}
