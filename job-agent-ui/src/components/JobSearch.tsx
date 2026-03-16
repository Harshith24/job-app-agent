'use client';

import { useState } from 'react';
import { Search, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { apiClient, handleApiError } from '@/lib/api';

interface JobSearchProps {
  onSearchComplete: () => void;
}

export function JobSearch({ onSearchComplete }: JobSearchProps) {
  const [searching, setSearching] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  const handleSearch = async () => {
    setSearching(true);
    setStatus({ type: 'info', message: 'Searching jobs…' });

    try {
      const result = await apiClient.searchJobs();
      setStatus({ type: 'success', message: result.message || 'Search completed.' });
      onSearchComplete();
    } catch (error: unknown) {
      setStatus({ type: 'error', message: handleApiError(error) });
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="card p-6 sm:p-8 max-w-2xl">
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">Job search</h2>
      <p className="text-sm text-[var(--color-muted)] mb-6">
        Uses your saved criteria and AI to find and rank jobs, then generates resume and cover letter for the top matches.
      </p>

      {status && (
        <div
          className={`mb-6 p-4 rounded-[var(--radius)] flex items-center gap-3 text-sm ${
            status.type === 'success'
              ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent-hover)] border border-[var(--color-accent)]/20'
              : status.type === 'error'
                ? 'bg-red-50 text-red-700 border border-red-100'
                : 'bg-[var(--color-border)]/50 text-[var(--color-text)] border border-[var(--color-border)]'
          }`}
        >
          {status.type === 'success' && <CheckCircle className="w-5 h-5 shrink-0" />}
          {status.type === 'error' && <AlertCircle className="w-5 h-5 shrink-0" />}
          {status.type === 'info' && <Loader2 className="w-5 h-5 shrink-0 animate-spin" />}
          <span>{status.message}</span>
        </div>
      )}

      <button
        onClick={handleSearch}
        disabled={searching}
        className="btn-primary px-6 py-3"
      >
        {searching ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
        {searching ? 'Searching…' : 'Start job search'}
      </button>
    </div>
  );
}
