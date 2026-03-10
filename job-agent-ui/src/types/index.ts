// API Types

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

export interface Job {
  title: string;
  company: string;
  location: string;
  url: string;
  resume_file: string;
  cover_file: string;
  status: string;
  output_dir: string;
}

export interface JobDetails {
  title: string;
  company: string;
  location: string;
  url: string;
  resume: string;
  cover_letter: string;
}

export interface HealthStatus {
  overall: boolean;
  services: {
    [key: string]: {
      healthy: boolean;
      status: string;
    };
  };
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Form Types
export interface ProfileFormData {
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

export interface CriteriaFormData {
  keywords: string;
  locations: string;
  experience_levels: string;
  job_types: string;
  exclude_terms?: string;
}