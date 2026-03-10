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
    setStatus({ type: 'info', message: 'Starting job search...' });

    try {
      const result = await apiClient.searchJobs();
      setStatus({
        type: 'success',
        message: `Job search completed! ${result.message}`
      });
      onSearchComplete();
    } catch (error: any) {
      console.error('Search failed:', error);
      setStatus({ type: 'error', message: handleApiError(error) });
    } finally {
      setSearching(false);
    }
  };

  const getStatusIcon = () => {
    if (!status) return null;

    switch (status.type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'info':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Job Search</h2>

        <div className="text-center">
          <p className="text-gray-600 mb-6">
            Search for jobs using your configured criteria and AI-powered ranking.
            The system will find relevant jobs, rank them by match quality, and generate personalized resumes and cover letters.
          </p>

          {status && (
            <div className={`mb-6 p-4 rounded-md flex items-center justify-center space-x-2 ${
              status.type === 'success' ? 'bg-green-50 text-green-800' :
              status.type === 'error' ? 'bg-red-50 text-red-800' :
              'bg-blue-50 text-blue-800'
            }`}>
              {getStatusIcon()}
              <span>{status.message}</span>
            </div>
          )}

          <button
            onClick={handleSearch}
            disabled={searching}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {searching ? (
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
            ) : (
              <Search className="h-5 w-5 mr-2" />
            )}
            {searching ? 'Searching...' : 'Start Job Search'}
          </button>

          <div className="mt-6 text-sm text-gray-500">
            <p>This will:</p>
            <ul className="mt-2 space-y-1">
              <li>• Query job boards with your search criteria</li>
              <li>• Use AI to rank jobs by relevance</li>
              <li>• Generate personalized resumes and cover letters</li>
              <li>• Save results to the Applications tab</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}