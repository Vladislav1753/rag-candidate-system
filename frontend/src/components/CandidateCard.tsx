"use client";

import { useState } from "react";
import {
  Award,
  ChevronDown,
  GraduationCap,
  Mail,
  MapPin,
  Phone,
} from "lucide-react";
import type { Candidate } from "@/lib/types";
import { initials, toStringList } from "@/lib/format";
import { RelevanceMeter } from "./RelevanceMeter";

function Chips({ items, limit }: { items: string[]; limit?: number }) {
  const shown = limit ? items.slice(0, limit) : items;
  const rest = limit ? items.length - shown.length : 0;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((t) => (
        <span
          key={t}
          className="rounded-md border border-line bg-canvas px-2 py-0.5 text-xs text-ink"
        >
          {t}
        </span>
      ))}
      {rest > 0 && (
        <span className="data px-1 py-0.5 text-xs text-faint">+{rest}</span>
      )}
    </div>
  );
}

export function CandidateCard({
  candidate,
  index,
  showScore,
}: {
  candidate: Candidate;
  index: number;
  showScore: boolean;
}) {
  const [open, setOpen] = useState(false);
  const skills = toStringList(candidate.skills);
  const tools = toStringList(candidate.tools);
  const langs = candidate.languages ?? [];

  return (
    <article
      className="reveal overflow-hidden rounded-2xl border border-line bg-surface"
      style={{ animationDelay: `${Math.min(index, 8) * 55}ms` }}
    >
      <div className="flex items-start gap-4 p-5">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-ink text-sm font-bold text-canvas">
          {initials(candidate.full_name)}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h3 className="truncate text-lg font-bold leading-tight">
                {candidate.full_name}
              </h3>
              <p className="truncate text-sm text-muted">
                {candidate.professional_title || "—"}
              </p>
            </div>
            {showScore && <RelevanceMeter score={candidate.score} />}
          </div>

          <div className="data mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
            {candidate.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5 text-faint" />
                {candidate.location}
              </span>
            )}
            {candidate.years_experience != null && (
              <span>{candidate.years_experience} yrs experience</span>
            )}
            {langs.length > 0 && (
              <span className="text-faint">{langs.join(" · ")}</span>
            )}
          </div>

          {candidate.summary && (
            <p className="mt-3 text-sm leading-relaxed text-ink/90">
              {candidate.summary}
            </p>
          )}

          {skills.length > 0 && (
            <div className="mt-3">
              <Chips items={skills} limit={open ? undefined : 6} />
            </div>
          )}
        </div>
      </div>

      {(tools.length > 0 ||
        candidate.education ||
        candidate.certifications ||
        candidate.email ||
        candidate.phone) && (
        <>
          <button
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="flex w-full items-center justify-between border-t border-line px-5 py-2.5 text-left text-xs text-muted transition-colors hover:bg-canvas"
          >
            <span className="eyebrow">{open ? "Less detail" : "Full profile"}</span>
            <ChevronDown
              className={`size-4 transition-transform ${open ? "rotate-180" : ""}`}
            />
          </button>

          {open && (
            <div className="space-y-4 border-t border-line bg-canvas/50 px-5 py-4 text-sm">
              {tools.length > 0 && (
                <Detail label="Tools & technologies">
                  <Chips items={tools} />
                </Detail>
              )}
              {candidate.education && (
                <Detail label="Education" icon={<GraduationCap className="size-4" />}>
                  {candidate.education}
                </Detail>
              )}
              {candidate.certifications && (
                <Detail label="Certifications" icon={<Award className="size-4" />}>
                  {candidate.certifications}
                </Detail>
              )}
              {(candidate.email || candidate.phone) && (
                <Detail label="Contact">
                  <div className="data flex flex-wrap gap-x-5 gap-y-1 text-ink">
                    {candidate.email && (
                      <a
                        href={`mailto:${candidate.email}`}
                        className="inline-flex items-center gap-1.5 hover:text-cobalt"
                      >
                        <Mail className="size-3.5 text-faint" />
                        {candidate.email}
                      </a>
                    )}
                    {candidate.phone && (
                      <span className="inline-flex items-center gap-1.5">
                        <Phone className="size-3.5 text-faint" />
                        {candidate.phone}
                      </span>
                    )}
                  </div>
                </Detail>
              )}
            </div>
          )}
        </>
      )}
    </article>
  );
}

function Detail({
  label,
  icon,
  children,
}: {
  label: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="eyebrow mb-1.5 flex items-center gap-1.5 text-faint">
        {icon}
        {label}
      </div>
      <div className="text-ink/90">{children}</div>
    </div>
  );
}
