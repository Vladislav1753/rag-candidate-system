"use client";

import { useRef, useState } from "react";
import {
  CheckCircle2,
  FileText,
  Loader2,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { ApiError, extractResume, onboardCandidate } from "@/lib/api";
import type { ExtractedResumeData, OnboardingPayload } from "@/lib/types";
import { FieldShell, TextField, inputClassName } from "@/components/Field";

interface FormState {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  professional_title: string;
  years_experience: string;
  languages: string;
  skills: string;
  tools: string;
  education: string;
  certifications: string;
  work_history: string;
  projects: string;
}

const EMPTY: FormState = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  professional_title: "",
  years_experience: "",
  languages: "",
  skills: "",
  tools: "",
  education: "",
  certifications: "",
  work_history: "",
  projects: "",
};

const splitComma = (s: string) =>
  s.split(",").map((x) => x.trim()).filter(Boolean);
const splitLines = (s: string) =>
  s.split("\n").map((x) => x.trim()).filter(Boolean);

export default function OnboardPage() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [summary, setSummary] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);

  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedName, setSavedName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function applyExtracted(data: ExtractedResumeData, finalSummary: string) {
    setForm({
      full_name: data.full_name ?? "",
      email: data.email ?? "",
      phone: data.phone ?? "",
      location: data.location ?? "",
      professional_title: data.professional_title ?? "",
      years_experience:
        data.years_experience != null ? String(data.years_experience) : "",
      languages: (data.spoken_languages ?? []).join(", "),
      skills: (data.skills ?? []).join(", "),
      tools: (data.tools_technologies ?? []).join(", "),
      education: data.education ?? "",
      certifications: (data.certifications ?? []).join("\n"),
      work_history: (data.work_history ?? []).join("\n"),
      projects: (data.projects ?? []).join("\n"),
    });
    setSummary(finalSummary);
  }

  async function handleFile(file: File) {
    if (file.type !== "application/pdf") {
      setError("That file isn't a PDF. Upload a PDF resume to extract from.");
      return;
    }
    setFileName(file.name);
    setExtracting(true);
    setError(null);
    setSavedName(null);
    try {
      const res = await extractResume(file);
      applyExtracted(res.extracted_data, res.final_summary);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : "Could not read that resume.",
      );
    } finally {
      setExtracting(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form.full_name.trim()) {
      setError("A full name is required to add a candidate.");
      return;
    }
    setSaving(true);
    setError(null);
    const payload: OnboardingPayload = {
      full_name: form.full_name.trim(),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      location: form.location.trim() || null,
      professional_title: form.professional_title.trim() || null,
      years_experience: form.years_experience
        ? Number(form.years_experience)
        : null,
      spoken_languages: splitComma(form.languages),
      education: form.education.trim() || null,
      certifications: form.certifications.trim() || null,
      skills: { manual_list: splitComma(form.skills) },
      tools_technologies: { items: splitComma(form.tools) },
      work_history: { raw_summary: splitLines(form.work_history) },
      projects: { raw_summary: splitLines(form.projects) },
    };
    try {
      await onboardCandidate(payload);
      setSavedName(form.full_name.trim());
      setForm(EMPTY);
      setSummary("");
      setFileName(null);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? `${e.message} (${e.status})`
          : "Could not save the candidate. Is the backend running?",
      );
    } finally {
      setSaving(false);
    }
  }

  if (savedName) {
    return (
      <div className="pt-16">
        <div className="mx-auto max-w-md rounded-2xl border border-line bg-surface p-8 text-center">
          <CheckCircle2 className="mx-auto size-10 text-cobalt" />
          <h1 className="mt-4 text-2xl font-bold">{savedName} is in the pool</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            Their AI summary and embedding are generating in the background and
            will surface in search within a moment.
          </p>
          <button
            onClick={() => setSavedName(null)}
            className="mt-6 rounded-lg bg-ink px-5 py-2.5 text-sm font-bold text-canvas transition-colors hover:bg-cobalt"
          >
            Add another candidate
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-12 sm:pt-16">
      <section className="mb-8">
        <p className="eyebrow mb-4">Onboarding</p>
        <h1 className="text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl">
          Add someone to the pool.
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-muted">
          Drop a PDF resume and let the parser fill the form, or type the details
          in directly. Everything stays editable before you save.
        </p>
      </section>

      {/* Dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") fileRef.current?.click();
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? "border-cobalt bg-cobalt-soft"
            : "border-line-strong bg-surface hover:border-cobalt"
        }`}
      >
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        {extracting ? (
          <>
            <Loader2 className="size-7 animate-spin text-cobalt" />
            <p className="mt-3 text-sm font-medium">Reading {fileName}…</p>
            <p className="data mt-1 text-xs text-faint">
              parsing fields with the extraction graph
            </p>
          </>
        ) : fileName ? (
          <>
            <FileText className="size-7 text-cobalt" />
            <p className="mt-3 text-sm font-medium">{fileName}</p>
            <p className="data mt-1 text-xs text-faint">
              click to replace · fields populated below
            </p>
          </>
        ) : (
          <>
            <UploadCloud className="size-7 text-faint" />
            <p className="mt-3 text-sm font-medium">
              Drop a PDF resume, or click to browse
            </p>
            <p className="data mt-1 text-xs text-faint">
              the parser extracts name, skills, history and more
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-5 rounded-lg border border-line bg-surface px-4 py-3 text-sm text-ink">
          {error}
        </div>
      )}

      {/* Form */}
      <form
        onSubmit={handleSave}
        className="mt-8 space-y-8 rounded-2xl border border-line bg-surface p-5 sm:p-6"
      >
        <Section title="Identity">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FieldShell label="Full name *">
              <TextField
                value={form.full_name}
                onChange={(e) => set("full_name", e.target.value)}
                required
                placeholder="Ada Lovelace"
              />
            </FieldShell>
            <FieldShell label="Professional title">
              <TextField
                value={form.professional_title}
                onChange={(e) => set("professional_title", e.target.value)}
                placeholder="Staff Backend Engineer"
              />
            </FieldShell>
            <FieldShell label="Email">
              <TextField
                type="email"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                placeholder="ada@example.com"
              />
            </FieldShell>
            <FieldShell label="Phone">
              <TextField
                value={form.phone}
                onChange={(e) => set("phone", e.target.value)}
                placeholder="+1 555 0100"
              />
            </FieldShell>
            <FieldShell label="Location">
              <TextField
                value={form.location}
                onChange={(e) => set("location", e.target.value)}
                placeholder="Berlin"
              />
            </FieldShell>
            <FieldShell label="Years of experience">
              <TextField
                type="number"
                min={0}
                max={60}
                value={form.years_experience}
                onChange={(e) => set("years_experience", e.target.value)}
                placeholder="8"
              />
            </FieldShell>
          </div>
        </Section>

        <Section title="Capabilities">
          <div className="space-y-4">
            <FieldShell label="Skills" hint={<span className="text-faint">comma separated</span>}>
              <TextField
                value={form.skills}
                onChange={(e) => set("skills", e.target.value)}
                placeholder="Python, PostgreSQL, distributed systems"
              />
            </FieldShell>
            <FieldShell label="Tools & technologies" hint={<span className="text-faint">comma separated</span>}>
              <TextField
                value={form.tools}
                onChange={(e) => set("tools", e.target.value)}
                placeholder="Docker, Kubernetes, AWS, Redis"
              />
            </FieldShell>
            <FieldShell label="Languages" hint={<span className="text-faint">comma separated</span>}>
              <TextField
                value={form.languages}
                onChange={(e) => set("languages", e.target.value)}
                placeholder="English, German"
              />
            </FieldShell>
          </div>
        </Section>

        <Section title="History">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FieldShell label="Work history" hint={<span className="text-faint">one per line</span>}>
              <Textarea
                value={form.work_history}
                onChange={(e) => set("work_history", e.target.value)}
                placeholder={"Senior Engineer · Acme · 2021–now\nEngineer · Globex · 2018–2021"}
              />
            </FieldShell>
            <FieldShell label="Key projects" hint={<span className="text-faint">one per line</span>}>
              <Textarea
                value={form.projects}
                onChange={(e) => set("projects", e.target.value)}
                placeholder={"Rebuilt search ranking pipeline\nLed migration to pgvector"}
              />
            </FieldShell>
            <FieldShell label="Education">
              <Textarea
                value={form.education}
                onChange={(e) => set("education", e.target.value)}
                placeholder="BSc Computer Science, TU Berlin"
              />
            </FieldShell>
            <FieldShell label="Certifications">
              <Textarea
                value={form.certifications}
                onChange={(e) => set("certifications", e.target.value)}
                placeholder="AWS Solutions Architect"
              />
            </FieldShell>
          </div>
        </Section>

        {summary && (
          <div className="rounded-xl border border-cobalt/30 bg-cobalt-soft px-4 py-3">
            <div className="eyebrow mb-1 flex items-center gap-1.5 text-cobalt">
              <Sparkles className="size-3.5" />
              Generated summary
            </div>
            <p className="text-sm leading-relaxed text-ink">{summary}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-cobalt px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-cobalt-deep disabled:opacity-60 sm:w-auto"
        >
          {saving && <Loader2 className="size-4 animate-spin" />}
          {saving ? "Saving…" : "Save candidate"}
        </button>
      </form>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="eyebrow mb-3 border-b border-line pb-2 text-faint">{title}</h2>
      {children}
    </section>
  );
}

function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      rows={props.rows ?? 3}
      className={`${inputClassName()} resize-none leading-relaxed ${props.className ?? ""}`}
    />
  );
}
