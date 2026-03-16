'use client';

import { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Trash2, Save, Loader2 } from 'lucide-react';
import { ProfileFormData, UserProfile } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';

const profileSchema = z.object({
  name: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  phone: z.string().optional(),
  linkedin: z.string().url().optional().or(z.literal('')),
  location: z.string().optional(),
  experience: z.array(z.object({ value: z.string() })).min(0),
  projects: z.array(z.object({ value: z.string() })).min(0),
  certifications: z.array(z.object({ value: z.string() })).min(0),
  education: z.array(z.object({ value: z.string() })).min(0),
  skills: z.array(z.object({ value: z.string() })).min(0),
});

function _transformProfileForForm(profile: UserProfile): ProfileFormData {
  return {
    ...profile,
    experience: (profile.experience || []).map(val => ({ value: val })),
    projects: (profile.projects || []).map(val => ({ value: val })),
    certifications: (profile.certifications || []).map(val => ({ value: val })),
    education: (profile.education || []).map(val => ({ value: val })),
    skills: (profile.skills || []).map(val => ({ value: val })),
  };
}

function _transformFormToProfile(formData: ProfileFormData): UserProfile {
  return {
    ...formData,
    experience: formData.experience.map(item => item.value),
    projects: formData.projects.map(item => item.value),
    certifications: formData.certifications.map(item => item.value),
    education: formData.education.map(item => item.value),
    skills: formData.skills.map(item => item.value),
  };
}

export function ProfileForm() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { register, control, handleSubmit, reset, formState: { errors } } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      experience: [],
      projects: [],
      certifications: [],
      education: [],
      skills: [],
    },
  });

  const experienceFields = useFieldArray({ control, name: 'experience' });
  const projectFields = useFieldArray({ control, name: 'projects' });
  const certificationFields = useFieldArray({ control, name: 'certifications' });
  const educationFields = useFieldArray({ control, name: 'education' });
  const skillFields = useFieldArray({ control, name: 'skills' });

  useEffect(() => {
    const cachedProfile = localStorage.getItem('profile_cache');
    if (cachedProfile) {
      try {
        const parsed = JSON.parse(cachedProfile);
        reset(_transformProfileForForm(parsed));
        // Still load in background to refresh cache, but don't show loading state
        refreshProfile();
      } catch (e) {
        loadProfile();
      }
    } else {
      loadProfile();
    }
  }, []);

  const refreshProfile = async () => {
    try {
      const profile = await apiClient.getProfile();
      localStorage.setItem('profile_cache', JSON.stringify(profile));
      reset(_transformProfileForForm(profile));
    } catch (error) {
      console.error('Failed to refresh profile:', error);
    }
  };

  const loadProfile = async () => {
    setLoading(true);
    try {
      const profile = await apiClient.getProfile();
      localStorage.setItem('profile_cache', JSON.stringify(profile));
      reset(_transformProfileForForm(profile));
    } catch (error) {
      console.error('Failed to load profile:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: ProfileFormData) => {
    setSaving(true);
    setMessage(null);
    try {
      const profileToSave = _transformFormToProfile(data);
      await apiClient.updateProfile(profileToSave);
      localStorage.setItem('profile_cache', JSON.stringify(profileToSave));
      setMessage({ type: 'success', text: 'Profile saved.' });
    } catch (error) {
      console.error('Failed to save profile:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--color-accent)]" />
        <span className="ml-3 text-[var(--color-muted)]">Loading profile…</span>
      </div>
    );
  }

  return (
    <div className="card p-6 sm:p-8">
      <h2 className="text-lg font-semibold text-[var(--color-text)] mb-6">Professional profile</h2>

      {message && (
        <div
          className={`mb-6 p-4 rounded-[var(--radius)] text-sm ${
            message.type === 'success'
              ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent-hover)] border border-[var(--color-accent)]/20'
              : 'bg-red-50 text-red-700 border border-red-100'
          }`}
        >
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Full name</label>
            <input {...register('name')} className="input mt-1" placeholder="Jane Doe" />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Email</label>
            <input {...register('email')} type="email" className="input mt-1" placeholder="jane@example.com" />
            {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Phone</label>
            <input {...register('phone')} className="input mt-1" placeholder="+1 555 000 0000" />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text)] mb-1">LinkedIn</label>
            <input {...register('linkedin')} className="input mt-1" placeholder="https://linkedin.com/in/janedoe" />
            {errors.linkedin && <p className="mt-1 text-sm text-red-600">{errors.linkedin.message}</p>}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--color-text)] mb-1">Location</label>
          <input {...register('location')} className="input" placeholder="San Francisco, CA" />
        </div>

        <FieldSection
          title="Work experience"
          fields={experienceFields.fields}
          register={register}
          name="experience"
          placeholder="Senior Engineer at Acme (2020–Present) — Led …"
          onAdd={() => experienceFields.append({ value: '' })}
          onRemove={(i) => experienceFields.remove(i)}
        />
        <FieldSection
          title="Projects"
          fields={projectFields.fields}
          register={register}
          name="projects"
          placeholder="Job Search Agent — Python, Ollama, Next.js"
          onAdd={() => projectFields.append({ value: '' })}
          onRemove={(i) => projectFields.remove(i)}
        />
        <FieldSection
          title="Certifications"
          fields={certificationFields.fields}
          register={register}
          name="certifications"
          placeholder="AWS Solutions Architect (2023)"
          onAdd={() => certificationFields.append({ value: '' })}
          onRemove={(i) => certificationFields.remove(i)}
        />
        <FieldSection
          title="Education"
          fields={educationFields.fields}
          register={register}
          name="education"
          placeholder="B.S. Computer Science — University (2016–2020)"
          onAdd={() => educationFields.append({ value: '' })}
          onRemove={(i) => educationFields.remove(i)}
        />
        <FieldSection
          title="Skills"
          fields={skillFields.fields}
          register={register}
          name="skills"
          placeholder="Python, React, AWS, Docker"
          onAdd={() => skillFields.append({ value: '' })}
          onRemove={(i) => skillFields.remove(i)}
        />

        <div className="flex justify-end pt-2">
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>
    </div>
  );
}

interface FieldSectionProps {
  title: string;
  fields: { id: string, value?: string }[];
  register: any;
  name: string;
  placeholder: string;
  onAdd: () => void;
  onRemove: (index: number) => void;
}

function FieldSection({ title, fields, register, name, placeholder, onAdd, onRemove }: FieldSectionProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-[var(--color-text)]">{title}</h3>
        <button type="button" onClick={onAdd} className="btn-secondary text-sm py-1.5 px-2">
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>
      <div className="space-y-2">
        {fields.map((field, index) => (
          <div key={field.id} className="flex gap-2">
            <textarea
              {...register(`${name}.${index}.value`)}
              className="input flex-1 min-h-[72px] resize-y"
              placeholder={placeholder}
              rows={2}
              defaultValue={field.value}
            />
            {fields.length > 0 && (
              <button
                type="button"
                onClick={() => onRemove(index)}
                className="btn-secondary p-2 text-[var(--color-muted)] hover:text-red-600 shrink-0"
                aria-label="Remove"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
