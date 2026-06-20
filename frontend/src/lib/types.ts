// Shapes returned by the FastAPI backend. The candidate JSON columns
// (skills/tools/projects/work_history) are loosely typed because the backend
// stores arbitrary onboarding payloads under varying keys.

export type Json = unknown;

export interface Candidate {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  languages: string[] | null;
  professional_title: string | null;
  years_experience: number | null;
  skills: Json;
  tools: Json;
  projects: Json;
  work_history: Json;
  education: string | null;
  certifications: string | null;
  summary: string | null;
  score?: number;
}

export interface SearchResponse {
  results: Candidate[];
  cached: boolean;
}

export interface ExpandResponse {
  status: string;
  original_query: string;
  expanded_query: string;
  cached: boolean;
}

export interface ExtractedResumeData {
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  professional_title?: string;
  years_experience?: number;
  education?: string;
  skills?: string[];
  tools_technologies?: string[];
  spoken_languages?: string[];
  certifications?: string[];
  projects?: string[];
  work_history?: string[];
}

export interface ExtractResponse {
  status: string;
  extracted_data: ExtractedResumeData;
  final_summary: string;
}

export interface SearchParams {
  query?: string | null;
  location?: string | null;
  min_experience?: number | null;
  top_k: number;
}

// Mirrors app.services.onboarding.CandidateInput
export interface OnboardingPayload {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  spoken_languages?: string[] | null;
  professional_title?: string | null;
  years_experience?: number | null;
  skills?: Record<string, unknown> | null;
  tools_technologies?: Record<string, unknown> | null;
  projects?: Record<string, unknown> | null;
  work_history?: Record<string, unknown> | null;
  education?: string | null;
  certifications?: string | null;
}
