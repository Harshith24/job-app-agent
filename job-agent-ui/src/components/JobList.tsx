'use client';

import { useState, useEffect } from 'react';
import { ExternalLink, Download, Eye, Loader2, CheckCircle, Clock, XCircle, Trash2, Building2, MapPin, Bot, User, Filter } from 'lucide-react';
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

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [dateFilter, setDateFilter] = useState<string>('');

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

  // Apply client-side filters
  const filteredJobs = jobs.filter(job => {
    if (sourceFilter === 'agent' && job.added_by !== 'agent') return false;
    if (sourceFilter === 'user' && job.added_by !== 'user') return false;
    if (dateFilter) {
      const jobDate = new Date(job.created_at).toISOString().slice(0, 10);
      if (jobDate < dateFilter) return false;
    }
    return true;
  });

  const agentCount = jobs.filter(j => j.added_by === 'agent').length;
  const userCount = jobs.filter(j => j.added_by === 'user').length;

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
        <span className="ml-3 text-[var(--color-muted)]">Loading applications…</span>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <Filter className="w-4 h-4 text-[var(--color-muted)]" />
            <span className="text-[var(--color-muted)]">Filter:</span>
          </div>

          <div className="flex items-center gap-1 bg-[var(--color-bg)] rounded-lg p-0.5 border border-[var(--color-border)]">
            {[
              { value: 'all', label: `All (${jobs.length})` },
              { value: 'agent', label: `Agent (${agentCount})`, icon: Bot },
              { value: 'user', label: `Manual (${userCount})`, icon: User },
            ].map(opt => (
              <button
                key={opt.value}
                onClick={() => setSourceFilter(opt.value)}
                className={`text-xs px-3 py-1.5 rounded-md transition-colors flex items-center gap-1 ${
                  sourceFilter === opt.value
                    ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-sm font-medium'
                    : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'
                }`}
              >
                {opt.icon && <opt.icon className="w-3 h-3" />}
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs text-[var(--color-muted)]">Since:</label>
            <input
              type="date"
              value={dateFilter}
              onChange={e => setDateFilter(e.target.value)}
              className="input text-xs py-1 w-auto"
            />
            {dateFilter && (
              <button onClick={() => setDateFilter('')} className="text-xs text-[var(--color-muted)] hover:text-[var(--color-text)]">
                Clear
              </button>
            )}
          </div>

          <button onClick={loadJobs} className="btn-secondary text-xs py-1.5 ml-auto">
            Refresh
          </button>
        </div>
      </div>

      {/* Job List */}
      <div className="card overflow-hidden">
        <div className="card-header flex items-center justify-between">
          <span>Applications</span>
          <span className="text-sm font-normal text-[var(--color-muted)]">{filteredJobs.length} jobs</span>
        </div>

        <div className="divide-y divide-[var(--color-border)]">
          {filteredJobs.length === 0 ? (
            <p className="p-8 text-center text-sm text-[var(--color-muted)]">
              {jobs.length === 0
                ? 'No jobs yet. Search or upload a JD to get started.'
                : 'No jobs match current filters.'}
            </p>
          ) : (
            filteredJobs.map((job) => (
              <div key={job.id} className="p-4 hover:bg-[var(--color-bg)]/80 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-[var(--color-text)] truncate">{job.title}</h3>
                      {job.relevance_score != null && (
                        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                          job.relevance_score >= 90 ? 'bg-green-100 text-green-700' :
                          job.relevance_score >= 80 ? 'bg-sky-100 text-sky-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {job.relevance_score}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[var(--color-muted)]">
                      {job.company}{job.location ? ` · ${job.location}` : ''}
                      {job.added_by === 'agent' && (
                        <span className="ml-2 inline-flex items-center gap-0.5 text-xs font-medium text-[var(--color-accent)]">
                          <Bot className="w-3 h-3" /> agent
                        </span>
                      )}
                      {job.source && (
                        <span className="ml-2 text-xs text-[var(--color-muted)]">via {job.source}</span>
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
                      <span className="text-xs text-[var(--color-muted)]">
                        {new Date(job.created_at).toLocaleDateString()}
                      </span>
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
        onClose={() => { setIsModalOpen(false); setSelected(null); }}
        title="Job Details"
      >
        {selected && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-bold text-[var(--color-text)]">{selected.title}</h3>
                {selected.relevance_score != null && (
                  <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                    selected.relevance_score >= 90 ? 'bg-green-100 text-green-700' :
                    selected.relevance_score >= 80 ? 'bg-sky-100 text-sky-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {selected.relevance_score}% match
                  </span>
                )}
              </div>
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
                {selected.added_by === 'agent' && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-accent)]">
                    <Bot className="w-3.5 h-3.5" /> Found by agent
                  </span>
                )}
                {selected.source && (
                  <span className="text-xs">Source: {selected.source}</span>
                )}
              </div>
            </div>

            {selected.description && (
              <div>
                <h4 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Job Description</h4>
                <div className="bg-[var(--color-bg)] rounded-lg p-4 border border-[var(--color-border)] max-h-64 overflow-y-auto">
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
