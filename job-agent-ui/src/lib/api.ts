import axios from 'axios';
import { supabase } from '@/lib/supabase';
import {
  UserProfile,
  JobSearchCriteria,
  JobRow,
  HealthStatus,
  GenerateFromJDRequest,
  GenerateFromJDResponse,
  AgentStatus,
} from '@/types';

axios.defaults.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Attach Supabase access token to every request
axios.interceptors.request.use(async (cfg) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    cfg.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return cfg;
});

export class ApiClient {
  private static instance: ApiClient;
  static getInstance(): ApiClient {
    if (!ApiClient.instance) ApiClient.instance = new ApiClient();
    return ApiClient.instance;
  }

  async healthCheck(): Promise<HealthStatus> {
    return (await axios.get<HealthStatus>('/health')).data;
  }

  // Profile
  async getProfile(): Promise<UserProfile> {
    return (await axios.get<UserProfile>('/profile')).data;
  }

  async updateProfile(profile: UserProfile): Promise<{ message: string }> {
    return (await axios.post<{ message: string }>('/profile', profile)).data;
  }

  // Criteria
  async getCriteria(): Promise<JobSearchCriteria> {
    return (await axios.get<JobSearchCriteria>('/criteria')).data;
  }

  async updateCriteria(criteria: JobSearchCriteria): Promise<{ message: string }> {
    return (await axios.post<{ message: string }>('/criteria', criteria)).data;
  }

  // Jobs
  async getJobs(): Promise<{ jobs: JobRow[] }> {
    return (await axios.get<{ jobs: JobRow[] }>('/jobs')).data;
  }

  async getJobDetail(jobId: string): Promise<JobRow> {
    return (await axios.get<JobRow>(`/jobs/${jobId}`)).data;
  }

  async updateJobStatus(jobId: string, status: string, notes?: string): Promise<{ message: string }> {
    return (await axios.patch<{ message: string }>(`/jobs/${jobId}`, { status, notes })).data;
  }

  async deleteJob(jobId: string): Promise<{ message: string }> {
    return (await axios.delete<{ message: string }>(`/jobs/${jobId}`)).data;
  }

  // Search
  async searchJobs(): Promise<{ message: string; count: number }> {
    return (await axios.post<{ message: string; count: number }>('/search')).data;
  }

  // Agent control
  async agentStart(): Promise<{ message: string; running: boolean }> {
    return (await axios.post('/agent/start')).data;
  }

  async agentStop(): Promise<{ message: string; running: boolean }> {
    return (await axios.post('/agent/stop')).data;
  }

  async agentStatus(): Promise<AgentStatus> {
    return (await axios.get<AgentStatus>('/agent/status')).data;
  }

  // Filtered jobs
  async getJobsFiltered(params?: { added_by?: string; date_from?: string; date_to?: string }): Promise<{ jobs: JobRow[] }> {
    return (await axios.get<{ jobs: JobRow[] }>('/jobs/filtered', { params })).data;
  }

  // Generate from JD
  async generateFromJobDescription(body: GenerateFromJDRequest): Promise<GenerateFromJDResponse> {
    return (await axios.post<GenerateFromJDResponse>('/generate-from-jd', body)).data;
  }

  // PDF downloads
  async downloadResumePdf(jobId: string): Promise<Blob> {
    const res = await axios.get(`/jobs/${jobId}/resume.pdf`, { responseType: 'blob' });
    return res.data;
  }

  async downloadCoverLetterPdf(jobId: string): Promise<Blob> {
    const res = await axios.get(`/jobs/${jobId}/cover-letter.pdf`, { responseType: 'blob' });
    return res.data;
  }
}

export const apiClient = ApiClient.getInstance();

export function handleApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (data) return data.detail || data.error || data.message || `Error ${error.response?.status}`;
    return 'Network error — check if the backend is running';
  }
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}
