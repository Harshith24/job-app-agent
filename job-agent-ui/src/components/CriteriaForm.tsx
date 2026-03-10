'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Save, Loader2 } from 'lucide-react';
import { CriteriaFormData } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';

const criteriaSchema = z.object({
  keywords: z.string(),
  locations: z.string(),
  experience_levels: z.string(),
  job_types: z.string(),
  exclude_terms: z.string().optional(),
});

export function CriteriaForm() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CriteriaFormData>({
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

  const onSubmit = async (data: CriteriaFormData) => {
    setSaving(true);
    setMessage(null);
    try {
      const payload = {
        keywords: data.keywords.split(',').map(s => s.trim()).filter(Boolean),
        locations: data.locations.split(',').map(s => s.trim()).filter(Boolean),
        experience_levels: data.experience_levels.split(',').map(s => s.trim()).filter(Boolean),
        job_types: data.job_types.split(',').map(s => s.trim()).filter(Boolean),
        exclude_terms: data.exclude_terms?.split(',').map(s => s.trim()).filter(Boolean) || [],
      };

      await apiClient.updateCriteria(payload);
      setMessage({ type: 'success', text: 'Search criteria saved successfully!' });
    } catch (error) {
      console.error('Failed to save criteria:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading search criteria...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Job Search Criteria</h2>

        {message && (
          <div className={`mb-6 p-4 rounded-md ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Keywords & Roles
              </label>
              <textarea
                {...register('keywords')}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                rows={3}
                placeholder="software engineer, cybersecurity, red team, blue team, penetration testing"
              />
              <p className="mt-1 text-sm text-gray-500">
                Enter keywords and job titles separated by commas
              </p>
              {errors.keywords && <p className="mt-1 text-sm text-red-600">{errors.keywords.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Locations
              </label>
              <input
                {...register('locations')}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="remote, San Francisco, New York"
              />
              <p className="mt-1 text-sm text-gray-500">
                Cities, states, or "remote"
              </p>
              {errors.locations && <p className="mt-1 text-sm text-red-600">{errors.locations.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Experience Levels
              </label>
              <input
                {...register('experience_levels')}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="entry, junior, mid-level, senior"
              />
              <p className="mt-1 text-sm text-gray-500">
                Experience levels you're targeting
              </p>
              {errors.experience_levels && <p className="mt-1 text-sm text-red-600">{errors.experience_levels.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Job Types
              </label>
              <input
                {...register('job_types')}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="full-time, contract, internship"
              />
              <p className="mt-1 text-sm text-gray-500">
                Employment types you're interested in
              </p>
              {errors.job_types && <p className="mt-1 text-sm text-red-600">{errors.job_types.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Exclude Terms (Optional)
              </label>
              <input
                {...register('exclude_terms')}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="senior only, management, sales"
              />
              <p className="mt-1 text-sm text-gray-500">
                Terms to exclude from search results
              </p>
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-md">
            <h3 className="text-sm font-medium text-blue-800 mb-2">Search Tips:</h3>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Use specific keywords from job descriptions you want</li>
              <li>• Include "remote" if you prefer remote work</li>
              <li>• Be specific about experience levels (entry, junior, mid, senior)</li>
              <li>• The AI will use these criteria to rank and filter jobs</li>
            </ul>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              {saving ? 'Saving...' : 'Save Criteria'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}