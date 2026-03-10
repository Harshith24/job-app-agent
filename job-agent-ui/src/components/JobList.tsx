'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, FileText, Download, Eye, Loader2, CheckCircle, Clock, XCircle } from 'lucide-react';
import { Job, JobDetails } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';

export function JobList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [jobDetails, setJobDetails] = useState<JobDetails | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const result = await apiClient.getJobs();
      setJobs(result.jobs || []);
    } catch (error) {
      console.error('Failed to load jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateApplicationStatus = async (job: Job, newStatus: string) => {
    const jobKey = `${job.title}|${job.company}|${job.url}`;
    setUpdatingStatus(jobKey);
    try {
      await apiClient.updateApplicationStatus(jobKey, newStatus);

      // Update local state
      setJobs(jobs.map(j =>
        j === job ? { ...j, status: newStatus } : j
      ));
    } catch (error) {
      console.error('Failed to update status:', error);
    } finally {
      setUpdatingStatus(null);
    }
  };

  const viewJobDetails = async (job: Job) => {
    setSelectedJob(job);
    try {
      const details = await apiClient.getJobDetails(`${job.title}|${job.company}|${job.url}`);
      setJobDetails(details);
    } catch (error) {
      console.error('Failed to load job details:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'applied':
        return 'bg-green-100 text-green-800';
      case 'interested':
        return 'bg-blue-100 text-blue-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'interviewing':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'applied':
        return <CheckCircle className="h-4 w-4" />;
      case 'interested':
        return <Clock className="h-4 w-4" />;
      case 'rejected':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading applications...</span>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Job List */}
        <div className="lg:col-span-2">
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Job Applications</h2>
              <p className="text-sm text-gray-600 mt-1">{jobs.length} jobs found</p>
            </div>

            <div className="divide-y divide-gray-200">
              {jobs.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  <p>No jobs found yet. Run a job search to get started!</p>
                </div>
              ) : (
                jobs.map((job, index) => (
                  <div key={index} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900">{job.title}</h3>
                        <p className="text-sm text-gray-600">{job.company} • {job.location}</p>

                        <div className="mt-2 flex items-center space-x-4">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
                            {getStatusIcon(job.status)}
                            <span className="ml-1 capitalize">{job.status.replace('_', ' ')}</span>
                          </span>

                          <select
                            value={job.status}
                            onChange={(e) => updateApplicationStatus(job, e.target.value)}
                            disabled={updatingStatus === `${job.title}|${job.company}|${job.url}`}
                            className="text-xs border-gray-300 rounded-md focus:border-blue-500 focus:ring-blue-500"
                          >
                            <option value="not_applied">Not Applied</option>
                            <option value="interested">Interested</option>
                            <option value="applied">Applied</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => viewJobDetails(job)}
                          className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </button>

                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center px-3 py-1 border border-transparent text-sm font-medium rounded-md text-blue-600 bg-blue-50 hover:bg-blue-100"
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Apply
                        </a>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Job Details */}
        <div className="lg:col-span-1">
          {selectedJob && jobDetails ? (
            <div className="bg-white shadow rounded-lg sticky top-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Application Materials</h3>
                <p className="text-sm text-gray-600 mt-1">{selectedJob.title} at {selectedJob.company}</p>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Resume</h4>
                  <div className="bg-gray-50 p-4 rounded-md max-h-64 overflow-y-auto">
                    <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                      {jobDetails.resume || 'Resume not available'}
                    </pre>
                  </div>
                  {jobDetails.resume && (
                    <button className="mt-2 inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                      <Download className="h-4 w-4 mr-1" />
                      Download Resume
                    </button>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Cover Letter</h4>
                  <div className="bg-gray-50 p-4 rounded-md max-h-64 overflow-y-auto">
                    <pre className="text-xs text-gray-800 whitespace-pre-wrap">
                      {jobDetails.cover_letter || 'Cover letter not available'}
                    </pre>
                  </div>
                  {jobDetails.cover_letter && (
                    <button className="mt-2 inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                      <Download className="h-4 w-4 mr-1" />
                      Download Cover Letter
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white shadow rounded-lg p-6">
              <div className="text-center text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                <p>Select a job to view application materials</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}