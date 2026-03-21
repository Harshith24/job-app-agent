'use client';

import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Save, Loader2, Search, CheckCircle, AlertCircle, Play, Square, Bot, Clock } from 'lucide-react';
import { CriteriaFormData, AgentStatus } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';

const criteriaSchema = z.object({
  keywords: z.string(),
  locations: z.string(),
  experience_levels: z.string(),
  job_types: z.string(),
  exclude_terms: z.string().optional(),
});

interface CriteriaFormProps {
  onSearchComplete?: () => void;
}

export function CriteriaForm({ onSearchComplete }: CriteriaFormProps) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [togglingAgent, setTogglingAgent] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CriteriaFormData>({
    resolver: zodResolver(criteriaSchema),
  });

  const loadAgentStatus = useCallback(async () => {
    try {
      const status = await apiClient.agentStatus();
      setAgentStatus(status);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    loadCriteria();
    loadAgentStatus();
    const interval = setInterval(loadAgentStatus, 15_000);
    return () => clearInterval(interval);
  }, [loadAgentStatus]);

  const loadCriteria = async () => {
    setLoading(true);
    try {
      const criteria = await apiClient.getCriteria();
      reset({
        keywords: criteria.keywords?.join(', ') || '',
        locations: criteria.locations?.join(', ') || '',
        experience_levels: criteria.experience_levels?.join(', ') || '',
        job_types: criteria.job_types?.join(', ') || '',
        exclude_terms: criteria.exclude_terms?.join(', ') || '',
      });
    } catch (error) {
      console.error('Failed to load criteria:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setLoading(false);
    }
  };

  const saveCriteria = async (data: CriteriaFormData) => {
    setSaving(true);
    setMessage(null);
    try {
      await apiClient.updateCriteria({
        keywords: data.keywords.split(',').map(s => s.trim()).filter(Boolean),
        locations: data.locations.split(',').map(s => s.trim()).filter(Boolean),
        experience_levels: data.experience_levels.split(',').map(s => s.trim()).filter(Boolean),
        job_types: data.job_types.split(',').map(s => s.trim()).filter(Boolean),
        exclude_terms: data.exclude_terms?.split(',').map(s => s.trim()).filter(Boolean) || [],
      });
      setMessage({ type: 'success', text: 'Criteria saved.' });
      return true;
    } catch (error) {
      console.error('Failed to save criteria:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
      return false;
    } finally {
      setSaving(false);
    }
  };

  const onSaveOnly = async (data: CriteriaFormData) => {
    await saveCriteria(data);
  };

  const onSaveAndRun = async (data: CriteriaFormData) => {
    const saved = await saveCriteria(data);
    if (saved) {
      handleSearch();
    }
  };

  const handleSearch = async () => {
    setSearching(true);
    setMessage({ type: 'info', text: 'Agent is searching and scoring jobs in the background…' });

    try {
      const result = await apiClient.searchJobs();
      setMessage({ type: 'success', text: result.message || 'Agent search started. Jobs will appear in Applications as they are processed.' });
      loadAgentStatus();
      if (onSearchComplete) {
        setTimeout(onSearchComplete, 2000);
      }
    } catch (error: unknown) {
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setSearching(false);
    }
  };

  const toggleAgent = async () => {
    setTogglingAgent(true);
    try {
      if (agentStatus?.running) {
        await apiClient.agentStop();
        setMessage({ type: 'info', text: 'Background agent stopped.' });
      } else {
        await apiClient.agentStart();
        setMessage({ type: 'success', text: `Background agent started — will search every ${agentStatus?.interval_minutes ?? 60} minutes.` });
      }
      await loadAgentStatus();
    } catch (error) {
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setTogglingAgent(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
        <span className="ml-3 text-[var(--color-muted)]">Loading criteria…</span>
      </div>
    );
  }

  const lastRun = agentStatus?.last_run;

  return (
    <div className="space-y-6">
      {/* Agent Status Card */}
      <div className="card p-6 sm:p-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-[var(--color-accent)]" />
            <h2 className="text-lg font-semibold text-[var(--color-text)]">Background Agent</h2>
          </div>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${agentStatus?.running ? 'text-green-600' : 'text-[var(--color-muted)]'}`}>
              <span className={`w-2 h-2 rounded-full ${agentStatus?.running ? 'bg-green-500 animate-pulse' : 'bg-[var(--color-muted)]'}`} />
              {agentStatus?.running ? 'Running' : 'Stopped'}
            </span>
            <button
              onClick={toggleAgent}
              disabled={togglingAgent}
              className={agentStatus?.running ? 'btn-secondary' : 'btn-primary'}
            >
              {togglingAgent
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : agentStatus?.running ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />
              }
              {agentStatus?.running ? 'Stop' : 'Start'}
            </button>
          </div>
        </div>

        <p className="text-sm text-[var(--color-muted)] mb-4">
          When running, the agent searches for jobs every {agentStatus?.interval_minutes ?? 60} minutes, scores each against your profile,
          and stores matches with relevance &ge; {agentStatus?.relevance_threshold ?? 80}%. Resume &amp; cover letter are auto-generated for each match.
        </p>

        {lastRun && (
          <div className="bg-[var(--color-bg)] rounded-lg p-4 border border-[var(--color-border)]">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-muted)] mb-2">Last run</h4>
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-[var(--color-text)]">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[var(--color-muted)]" />
                {new Date(lastRun.started_at).toLocaleString()}
              </span>
              <span>
                Status: <span className={`font-medium ${lastRun.status === 'completed' ? 'text-green-600' : lastRun.status === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>
                  {lastRun.status}
                </span>
              </span>
              <span>Found: <strong>{lastRun.jobs_found}</strong></span>
              <span>Stored: <strong>{lastRun.jobs_stored}</strong></span>
              {lastRun.error && <span className="text-red-600 text-xs">{lastRun.error}</span>}
            </div>
          </div>
        )}
      </div>

      {/* Criteria Form */}
      <div className="card p-6 sm:p-8">
        <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">Search Criteria</h2>
        <p className="text-sm text-[var(--color-muted)] mb-6">
          Define what jobs the agent should look for. Click &quot;Save &amp; Run&quot; to trigger an immediate search.
        </p>

        {message && (
          <div
            className={`mb-6 p-4 rounded-[var(--radius)] flex items-center gap-3 text-sm ${
              message.type === 'success'
                ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent-hover)] border border-[var(--color-accent)]/20'
                : message.type === 'error'
                  ? 'bg-red-50 text-red-700 border border-red-100'
                  : 'bg-[var(--color-border)]/50 text-[var(--color-text)] border border-[var(--color-border)]'
            }`}
          >
            {message.type === 'success' && <CheckCircle className="w-5 h-5 shrink-0" />}
            {message.type === 'error' && <AlertCircle className="w-5 h-5 shrink-0" />}
            {message.type === 'info' && <Loader2 className="w-5 h-5 shrink-0 animate-spin" />}
            <span>{message.text}</span>
          </div>
        )}

        <form className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Keywords &amp; roles</label>
            <textarea
              {...register('keywords')}
              className="input min-h-[80px] resize-y"
              rows={3}
              placeholder="software engineer, cybersecurity, red team, penetration testing"
            />
            <p className="mt-1 text-xs text-[var(--color-muted)]">Comma-separated</p>
            {errors.keywords && <p className="mt-1 text-sm text-red-600">{errors.keywords.message}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Locations</label>
              <input
                {...register('locations')}
                className="input"
                placeholder="remote, San Francisco, New York"
              />
              {errors.locations && <p className="mt-1 text-sm text-red-600">{errors.locations.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Experience levels</label>
              <input
                {...register('experience_levels')}
                className="input"
                placeholder="entry, junior, mid-level, senior"
              />
              {errors.experience_levels && <p className="mt-1 text-sm text-red-600">{errors.experience_levels.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Job types</label>
              <input
                {...register('job_types')}
                className="input"
                placeholder="full-time, contract, internship"
              />
              {errors.job_types && <p className="mt-1 text-sm text-red-600">{errors.job_types.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Exclude terms (optional)</label>
              <input
                {...register('exclude_terms')}
                className="input"
                placeholder="management, sales"
              />
            </div>
          </div>

          <div className="flex flex-col sm:flex-row justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleSubmit(onSaveOnly)}
              disabled={saving || searching}
              className="btn-secondary"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving…' : 'Save criteria'}
            </button>
            <button
              type="button"
              onClick={handleSubmit(onSaveAndRun)}
              disabled={saving || searching}
              className="btn-primary"
            >
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {searching ? 'Starting…' : 'Save & Run now'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
