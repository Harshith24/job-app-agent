// ── API types ───────────────────────────────────────────────

export interface UserProfile {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
  location?: string;
  experience: string[];
  projects: string[];
  certifications: string[];
  education: string[];
  skills: string[];
}

export interface JobSearchCriteria {
  keywords: string[];
  locations: string[];
  experience_levels: string[];
  job_types: string[];
  exclude_terms?: string[];
}

/** A row from the `jobs` table. */
export interface JobRow {
  id: string;
  user_id: string;
  title: string;
  company: string;
  location: string | null;
  description: string | null;
  url: string | null;
  posted_date: string | null;
  salary_range: string | null;
  job_type: string | null;
  source: string | null;
  added_by: 'user' | 'agent';
  relevance_score: number | null;
  status: string;
  resume_text: string | null;
  cover_letter_text: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface HealthStatus {
  overall: boolean;
  services: Record<string, { healthy: boolean; status: string }>;
}

export interface GenerateFromJDRequest {
  job_description: string;
  title?: string;
  company?: string;
  location?: string;
}

export interface ResumeData {
  summary?: string;
  experience?: Array<{
    title?: string;
    company?: string;
    duration?: string;
    bullets?: string[];
  } | string>;
  education?: Array<{
    degree?: string;
    school?: string;
    year?: string;
  } | string>;
  skills?: string[];
  projects?: Array<{
    name?: string;
    description?: string;
  } | string>;
  certifications?: string[];
}

export interface CoverLetterData {
  greeting?: string;
  body?: string[];
  paragraphs?: string[];
  closing?: string;
}

export interface GenerateFromJDResponse {
  id?: string;
  resume_data: ResumeData;
  cover_letter_data: CoverLetterData;
  title: string;
  company: string;
}

// ── Form types ──────────────────────────────────────────────

export interface ProfileFormData {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
  location?: string;
  experience: { value: string }[];
  projects: { value: string }[];
  certifications: { value: string }[];
  education: { value: string }[];
  skills: { value: string }[];
}

export interface CriteriaFormData {
  keywords: string;
  locations: string;
  experience_levels: string;
  job_types: string;
  exclude_terms?: string;
}
