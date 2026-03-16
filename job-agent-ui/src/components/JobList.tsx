'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, FileText, Download, Eye, Loader2, CheckCircle, Clock, XCircle, Trash2, X, Building2, MapPin } from 'lucide-react';
import { JobRow } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';
import { Modal } from '@/components/ui/Modal';

function hasStructuredData(text: string | null): boolean {
  if (!text) return false;
  try { JSON.parse(text); return true; } catch { return false; }
}

export function JobList() {
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<JobRow | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  useEffect(() => { loadJobs(); }, []);

  const loadJobs = async () => {
    try {
      const { jobs } = await apiClient.getJobs();
      setJobs(jobs ?? []);
    } catch (e) {
      console.error('Failed to load jobs:', e);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (job: JobRow, status: string) => {
    setUpdatingId(job.id);
    try {
      await apiClient.updateJobStatus(job.id, status);
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status } : j));
      if (selected?.id === job.id) setSelected({ ...selected!, status });
    } catch (e) {
      console.error('Failed to update status:', e);
    } finally {
      setUpdatingId(null);
    }
  };

  const deleteJob = async (job: JobRow) => {
    try {
      await apiClient.deleteJob(job.id);
      setJobs(prev => prev.filter(j => j.id !== job.id));
      if (selected?.id === job.id) {
        setSelected(null);
        setIsModalOpen(false);
      }
    } catch (e) {
      console.error('Failed to delete job:', e);
    }
  };

  const viewDetail = async (job: JobRow) => {
    setIsModalOpen(true);
    try {
      const detail = await apiClient.getJobDetail(job.id);
      setSelected(detail);
    } catch {
      setSelected(job);
    }
  };

  const downloadPdf = async (jobId: string, type: 'resume' | 'cover', company: string) => {
    try {
      const blob = type === 'resume'
        ? await apiClient.downloadResumePdf(jobId)
        : await apiClient.downloadCoverLetterPdf(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const slug = company.replace(/\s+/g, '-').toLowerCase();
      a.download = type === 'resume' ? `resume-${slug}.pdf` : `cover-letter-${slug}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(`Failed to download ${type} PDF:`, e);
    }
  };

  const badgeColor = (s: string) => {
    if (s === 'applied') return 'bg-green-100 text-green-800';
    if (s === 'interested') return 'bg-sky-100 text-sky-800';
    if (s === 'interviewing') return 'bg-purple-100 text-purple-800';
    if (s === 'rejected') return 'bg-red-100 text-red-800';
    if (s === 'offered') return 'bg-amber-100 text-amber-800';
    return 'bg-[var(--color-border)] text-[var(--color-muted)]';
  };

  const badgeIcon = (s: string) => {
    if (s === 'applied') return <CheckCircle className="w-3.5 h-3.5" />;
    if (s === 'rejected') return <XCircle className="w-3.5 h-3.5" />;
    return <Clock className="w-3.5 h-3.5" />;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
        <span className="ml-3 text-[var(--color-muted)]">Loading applications…</span>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="card overflow-hidden">
        <div className="card-header flex items-center justify-between">
          <span>Applications</span>
          <span className="text-sm font-normal text-[var(--color-muted)]">{jobs.length} jobs</span>
        </div>

        <div className="divide-y divide-[var(--color-border)]">
          {jobs.length === 0 ? (
            <p className="p-8 text-center text-sm text-[var(--color-muted)]">
              No jobs yet. Search or upload a JD to get started.
            </p>
          ) : (
            jobs.map((job) => (
              <div key={job.id} className="p-4 hover:bg-[var(--color-bg)]/80 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="font-medium text-[var(--color-text)] truncate">{job.title}</h3>
                    <p className="text-sm text-[var(--color-muted)]">
                      {job.company}{job.location ? ` · ${job.location}` : ''}
                      {job.added_by === 'agent' && (
                        <span className="ml-2 text-xs font-medium text-[var(--color-accent)]">agent</span>
                      )}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className={`badge ${badgeColor(job.status)} inline-flex items-center gap-1`}>
                        {badgeIcon(job.status)}
                        <span className="capitalize">{job.status.replace('_', ' ')}</span>
                      </span>
                      <select
                        value={job.status}
                        onChange={(e) => updateStatus(job, e.target.value)}
                        disabled={updatingId === job.id}
                        className="input text-xs py-1 w-auto max-w-[140px]"
                      >
                        <option value="not_applied">Not applied</option>
                        <option value="interested">Interested</option>
                        <option value="applied">Applied</option>
                        <option value="interviewing">Interviewing</option>
                        <option value="offered">Offered</option>
                        <option value="rejected">Rejected</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button onClick={() => viewDetail(job)} className="btn-secondary text-sm py-2">
                      <Eye className="w-4 h-4" /> View
                    </button>
                    {job.url && (
                      <a href={job.url} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm py-2">
                        <ExternalLink className="w-4 h-4" /> Apply
                      </a>
                    )}
                    <button onClick={() => deleteJob(job)} className="btn-secondary text-sm py-2 text-red-500 hover:text-red-700" title="Delete">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Detail Modal */}
      <Modal 
        isOpen={isModalOpen} 
        onClose={() => {
          setIsModalOpen(false);
          setSelected(null);
        }}
        title="Job Details"
      >
        {selected && (
          <div className="space-y-6">
            <div>
              <h3 className="text-xl font-bold text-[var(--color-text)]">{selected.title}</h3>
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-[var(--color-muted)]">
                <div className="flex items-center gap-1.5">
                  <Building2 className="w-4 h-4" />
                  {selected.company}
                </div>
                {selected.location && (
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-4 h-4" />
                    {selected.location}
                  </div>
                )}
                <div className={`badge ${badgeColor(selected.status)}`}>
                  <span className="capitalize">{selected.status.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            {selected.description && (
              <div>
                <h4 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Job Description</h4>
                <div className="bg-[var(--color-bg)] rounded-lg p-4 border border-[var(--color-border)]">
                  <p className="text-sm text-[var(--color-text)] whitespace-pre-wrap leading-relaxed">
                    {selected.description}
                  </p>
                </div>
              </div>
            )}

            {(selected.resume_text || selected.cover_letter_text) && (
              <div>
                <h4 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-3">Application Materials</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {hasStructuredData(selected.resume_text) && (
                    <button onClick={() => downloadPdf(selected.id, 'resume', selected.company)}
                            className="btn-primary py-2.5 w-full">
                      <Download className="w-4 h-4" /> Resume PDF
                    </button>
                  )}
                  {hasStructuredData(selected.cover_letter_text) && (
                    <button onClick={() => downloadPdf(selected.id, 'cover', selected.company)}
                            className="btn-secondary py-2.5 w-full">
                      <Download className="w-4 h-4" /> Cover Letter PDF
                    </button>
                  )}
                </div>
              </div>
            )}

            {selected.url && (
              <div className="pt-4 border-t border-[var(--color-border)]">
                <a 
                  href={selected.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="btn-primary w-full py-3 text-base"
                >
                  <ExternalLink className="w-5 h-5" /> View Original Posting
                </a>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

