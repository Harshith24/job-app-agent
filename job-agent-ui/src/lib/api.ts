import axios, { AxiosResponse } from 'axios';
import { UserProfile, JobSearchCriteria, Job, JobDetails, HealthStatus } from '@/types';

// Configure axios defaults
axios.defaults.baseURL = 'http://localhost:8000/api';

// API Response types
interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// API Client class
export class ApiClient {
  private static instance: ApiClient;

  public static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  // Health check
  async healthCheck(): Promise<HealthStatus> {
    const response = await axios.get<HealthStatus>('/health');
    return response.data;
  }

  // Profile management
  async getProfile(): Promise<UserProfile> {
    const response = await axios.get<UserProfile>('/profile');
    return response.data;
  }

  async updateProfile(profile: UserProfile): Promise<{ message: string }> {
    const response = await axios.post<{ message: string }>('/profile', profile);
    return response.data;
  }

  // Search criteria management
  async getCriteria(): Promise<JobSearchCriteria> {
    const response = await axios.get<JobSearchCriteria>('/criteria');
    return response.data;
  }

  async updateCriteria(criteria: JobSearchCriteria): Promise<{ message: string }> {
    const response = await axios.post<{ message: string }>('/criteria', criteria);
    return response.data;
  }

  // Job search
  async searchJobs(): Promise<{ message: string; output_path: string }> {
    const response = await axios.post<{ message: string; output_path: string }>('/search');
    return response.data;
  }

  // Job management
  async getJobs(): Promise<{ jobs: Job[] }> {
    const response = await axios.get<{ jobs: Job[] }>('/jobs');
    return response.data;
  }

  async getJobDetails(jobKey: string): Promise<JobDetails> {
    const response = await axios.get<JobDetails>(`/job/${encodeURIComponent(jobKey)}`);
    return response.data;
  }

  async updateApplicationStatus(jobKey: string, status: string, notes?: string): Promise<{ message: string }> {
    const response = await axios.post<{ message: string }>(`/applications/${encodeURIComponent(jobKey)}`, {
      status,
      notes
    });
    return response.data;
  }
}

// Export singleton instance
export const apiClient = ApiClient.getInstance();

// Error handling utility
export function handleApiError(error: any): string {
  if (error.response) {
    // Server responded with error status
    const data = error.response.data;
    return data.error || data.message || `Server error: ${error.response.status}`;
  } else if (error.request) {
    // Network error
    return 'Network error - please check if the backend is running';
  } else {
    // Other error
    return error.message || 'An unexpected error occurred';
  }
}