'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Save, Loader2, Search, CheckCircle, AlertCircle } from 'lucide-react';
import { CriteriaFormData } from '@/types';
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

  const { register, handleSubmit, reset, getValues, formState: { errors } } = useForm<CriteriaFormData>({
    resolver: zodResolver(criteriaSchema),
  });

  useEffect(() => {
    loadCriteria();
  }, []);

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
    setMessage({ type: 'info', text: 'Searching jobs…' });

    try {
      const result = await apiClient.searchJobs();
      setMessage({ type: 'success', text: result.message || 'Search completed.' });
      if (onSearchComplete) {
        onSearchComplete();
      }
    } catch (error: unknown) {
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setSearching(false);
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

  return (
    <div className="card p-6 sm:p-8">
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">Search criteria & Job search</h2>
      <p className="text-sm text-[var(--color-muted)] mb-6">
        Define your search criteria and start the AI-powered job search.
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
          <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Keywords & roles</label>
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
            {searching ? 'Searching…' : 'Save and Run'}
          </button>
        </div>
      </form>
    </div>
  );
}
