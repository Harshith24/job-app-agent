'use client';

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { AuthForm } from '@/components/AuthForm';
import { ProfileForm } from '@/components/ProfileForm';
import { CriteriaForm } from '@/components/CriteriaForm';
import { JobSearch } from '@/components/JobSearch';
import { JobList } from '@/components/JobList';
import { UploadJD } from '@/components/UploadJD';
import { Tabs } from '@/components/ui/Tabs';
import { User, Search, FileInput, ListTodo, Sparkles, LogOut, Loader2 } from 'lucide-react';

export default function Home() {
  const { user, loading, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
      </div>
    );
  }

  if (!user) return <AuthForm />;

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'criteria', label: 'Criteria & Search', icon: Search },
    { id: 'ondemand', label: 'Upload JD', icon: FileInput },
    { id: 'applications', label: 'Applications', icon: ListTodo },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-surface)]/95 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-semibold tracking-tight">Job Search AI Agent</h1>
                <p className="text-sm text-[var(--color-muted)]">{user.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <nav>
                <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
              </nav>
              <button
                onClick={signOut}
                className="btn-secondary py-2 px-3"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8">
        {activeTab === 'profile' && <ProfileForm />}
        {activeTab === 'criteria' && (
          <CriteriaForm onSearchComplete={() => setActiveTab('applications')} />
        )}
        {activeTab === 'ondemand' && <UploadJD />}
        {activeTab === 'applications' && <JobList />}
      </main>
    </div>
  );
}
