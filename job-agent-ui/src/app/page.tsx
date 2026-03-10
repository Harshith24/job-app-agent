'use client';

import { useState } from 'react';
import { ProfileForm } from '@/components/ProfileForm';
import { CriteriaForm } from '@/components/CriteriaForm';
import { JobSearch } from '@/components/JobSearch';
import { JobList } from '@/components/JobList';
import { Tabs } from '@/components/ui/Tabs';

export default function Home() {
  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'criteria', label: 'Search Criteria', icon: '🔍' },
    { id: 'search', label: 'Job Search', icon: '💼' },
    { id: 'applications', label: 'My Applications', icon: '📋' }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Job Search AI Agent
          </h1>
          <p className="text-lg text-gray-600">
            AI-powered job search with personalized resume and cover letter generation
          </p>
        </div>

        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

        <div className="mt-8">
          {activeTab === 'profile' && <ProfileForm />}
          {activeTab === 'criteria' && <CriteriaForm />}
          {activeTab === 'search' && <JobSearch onSearchComplete={() => setActiveTab('applications')} />}
          {activeTab === 'applications' && <JobList />}
        </div>
      </div>
    </div>
  );
}