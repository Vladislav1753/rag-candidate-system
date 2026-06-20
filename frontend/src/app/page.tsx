"use client";

import { useState } from "react";
import { Loader2, Search, Sparkles, Undo2 } from "lucide-react";
import { ApiError, expandQuery, searchCandidates } from "@/lib/api";
import type { Candidate } from "@/lib/types";
import { CandidateCard } from "@/components/CandidateCard";
import { FieldShell, NumberStepper, TextField } from "@/components/Field";

const EXAMPLES = [
  "Senior Python engineer with AWS and distributed systems",
  "Frontend developer fluent in React and TypeScript",
  "ML engineer focused on NLP and retrieval",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState("");
  const [minExp, setMinExp] = useState(0);
  const [topK, setTopK] = useState(5);

  const [originalQuery, setOriginalQuery] = useState<string | null>(null);
  const [expanding, setExpanding] = useState(false);

  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Candidate[] | null>(null);
  const [cached, setCached] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usedQuery = query.trim().length > 0;

  function onQueryChange(value: string) {
    setQuery(value);
    if (originalQuery !== null) setOriginalQuery(null);
  }

  async function handleExpand() {
    if (query.trim().length < 2) return;
    setExpanding(true);
    setError(null);
    try {
      const res = await expandQuery(query.trim());
      if (res.expanded_query && res.expanded_query.trim() !== query.trim()) {
        setOriginalQuery(query);
        setQuery(res.expanded_query);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not expand the query.");
    } finally {
      setExpanding(false);
    }
  }

  function restore() {
    if (originalQuery !== null) {
      setQuery(originalQuery);
      setOriginalQuery(null);
    }
  }

  async function handleSearch(e?: React.FormEvent) {
    e?.preventDefault();
    if (!query.trim() && !location.trim()) {
      setError("Enter a description or a location to search.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await searchCandidates({
        query: query.trim() || null,
        location: location.trim() || null,
        min_experience: minExp || null,
        top_k: topK,
      });
      setResults(res.results);
      setCached(res.cached);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.message} (${e.status})`
          : "Could not reach the search service. Is the backend running?",
      );
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="pt-12 sm:pt-16">
      {/* Hero — the thesis: describe a person, the pool gets ranked. */}
      <section className="mb-8">
        <p className="eyebrow mb-4">Semantic retrieval · pgvector + cross-encoder</p>
        <h1 className="max-w-2xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl">
          Find people by what
          <br />
          they can <span className="text-cobalt">actually do</span>.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">
          Describe the role in plain language. We embed it, search the candidate
          pool by meaning, and rerank the closest matches.
        </p>
      </section>

      {/* Composer */}
      <form
        onSubmit={handleSearch}
        className="rounded-2xl border border-line bg-surface p-5 sm:p-6"
      >
        <FieldShell
          label="What are you looking for?"
          hint={
            originalQuery !== null ? (
              <button
                type="button"
                onClick={restore}
                className="inline-flex items-center gap-1 text-cobalt hover:text-cobalt-deep"
              >
                <Undo2 className="size-3" />
                restore
              </button>
            ) : undefined
          }
        >
          <div className="relative">
            <textarea
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              rows={2}
              placeholder="e.g. Backend engineer who has scaled Postgres and led a small team"
              className="w-full resize-none rounded-lg border border-line bg-surface px-3 py-2.5 pr-32 text-base text-ink placeholder:text-faint outline-none transition-colors focus:border-cobalt"
            />
            <button
              type="button"
              onClick={handleExpand}
              disabled={expanding || query.trim().length < 2}
              className="absolute right-2 top-2 inline-flex items-center gap-1.5 rounded-md border border-line bg-canvas px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:border-cobalt hover:text-cobalt disabled:cursor-not-allowed disabled:opacity-40"
            >
              {expanding ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              Expand with AI
            </button>
          </div>
        </FieldShell>

        {originalQuery !== null && (
          <p className="data mt-2 text-xs text-faint">
            expanded from “{originalQuery}”
          </p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="col-span-2">
            <FieldShell label="Location">
              <TextField
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Any city"
              />
            </FieldShell>
          </div>
          <FieldShell label="Min. experience">
            <NumberStepper
              value={minExp}
              onChange={setMinExp}
              min={0}
              max={40}
              suffix="yrs"
            />
          </FieldShell>
          <FieldShell label="Results">
            <NumberStepper value={topK} onChange={setTopK} min={1} max={10} />
          </FieldShell>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cobalt px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-cobalt-deep disabled:opacity-60 sm:w-auto"
        >
          {loading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Search className="size-4" />
          )}
          {loading ? "Searching…" : "Search the pool"}
        </button>
      </form>

      {/* Example prompts before the first search. */}
      {results === null && !loading && (
        <div className="mt-6">
          <p className="eyebrow mb-2.5">Try</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => setQuery(ex)}
                className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-sm text-muted transition-colors hover:border-cobalt hover:text-ink"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink">
          {error}
        </div>
      )}

      {/* Results */}
      {results !== null && (
        <section className="mt-10">
          <div className="mb-4 flex items-baseline justify-between border-b border-line pb-2.5">
            <h2 className="data text-sm text-muted">
              {results.length === 0
                ? "No matches"
                : `${results.length} ranked ${results.length === 1 ? "match" : "matches"}`}
            </h2>
            {cached && <span className="eyebrow text-faint">cached</span>}
          </div>

          {results.length === 0 ? (
            <p className="rounded-xl border border-dashed border-line-strong bg-surface px-5 py-10 text-center text-sm text-muted">
              Nothing matched those constraints. Broaden the description or drop a
              filter, then search again.
            </p>
          ) : (
            <div className="space-y-4">
              {results.map((c, i) => (
                <CandidateCard
                  key={c.id}
                  candidate={c}
                  index={i}
                  showScore={usedQuery}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
