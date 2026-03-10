'use client';

import { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Trash2, Save, Loader2 } from 'lucide-react';
import { ProfileFormData } from '@/types';
import { apiClient, handleApiError } from '@/lib/api';

const profileSchema = z.object({
  name: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  phone: z.string().optional(),
  linkedin: z.string().url().optional().or(z.literal('')),
  location: z.string().optional(),
  experience: z.array(z.string()).min(0),
  projects: z.array(z.string()).min(0),
  certifications: z.array(z.string()).min(0),
  education: z.array(z.string()).min(0),
  skills: z.array(z.string()).min(0),
});

// Form uses ProfileFormData type from types/index.ts

export function ProfileForm() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const { register, control, handleSubmit, reset, formState: { errors } } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      experience: [''],
      projects: [''],
      certifications: [''],
      education: [''],
      skills: [''],
    }
  });

  // @ts-ignore - TypeScript issues with react-hook-form useFieldArray
  const experienceFields = useFieldArray({ control, name: 'experience' });
  // @ts-ignore
  const projectFields = useFieldArray({ control, name: 'projects' });
  // @ts-ignore
  const certificationFields = useFieldArray({ control, name: 'certifications' });
  // @ts-ignore
  const educationFields = useFieldArray({ control, name: 'education' });
  // @ts-ignore
  const skillFields = useFieldArray({ control, name: 'skills' });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const profile = await apiClient.getProfile();
      reset(profile);
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
      await apiClient.updateProfile(data);
      setMessage({ type: 'success', text: 'Profile saved successfully!' });
    } catch (error) {
      console.error('Failed to save profile:', error);
      setMessage({ type: 'error', text: handleApiError(error) });
    } finally {
      setSaving(false);
    }
  };

  const addField = (fields: any[], append: (value: string) => void) => {
    append('');
  };

  const removeField = (fields: any[], index: number, remove: (index: number) => void) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading profile...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Professional Profile</h2>

        {message && (
          <div className={`mb-6 p-4 rounded-md ${message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Contact Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">Full Name</label>
              <input
                {...register('name')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="John Doe"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                {...register('email')}
                type="email"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="john@example.com"
              />
              {errors.email && <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Phone</label>
              <input
                {...register('phone')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="+1 (555) 123-4567"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">LinkedIn URL</label>
              <input
                {...register('linkedin')}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                placeholder="https://linkedin.com/in/johndoe"
              />
              {errors.linkedin && <p className="mt-1 text-sm text-red-600">{errors.linkedin.message}</p>}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Location</label>
            <input
              {...register('location')}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder="San Francisco, CA"
            />
          </div>

          {/* Dynamic Fields */}
          <FieldArray
            title="Work Experience"
            fields={experienceFields.fields}
            register={register}
            name="experience"
            placeholder="Senior Software Engineer at Tech Corp (2020-Present) - Led development of AI-powered job search platform..."
            onAdd={() => addField(experienceFields.fields, experienceFields.append)}
            onRemove={(index) => removeField(experienceFields.fields, index, experienceFields.remove)}
          />

          <FieldArray
            title="Projects"
            fields={projectFields.fields}
            register={register}
            name="projects"
            placeholder="Job Search AI Agent - Built an AI-powered job search platform using Python, Ollama, and Next.js..."
            onAdd={() => addField(projectFields.fields, projectFields.append)}
            onRemove={(index) => removeField(projectFields.fields, index, projectFields.remove)}
          />

          <FieldArray
            title="Certifications"
            fields={certificationFields.fields}
            register={register}
            name="certifications"
            placeholder="AWS Certified Solutions Architect - Amazon Web Services (2023)"
            onAdd={() => addField(certificationFields.fields, certificationFields.append)}
            onRemove={(index) => removeField(certificationFields.fields, index, certificationFields.remove)}
          />

          <FieldArray
            title="Education"
            fields={educationFields.fields}
            register={register}
            name="education"
            placeholder="Bachelor of Science in Computer Science - University Name (2016-2020)"
            onAdd={() => addField(educationFields.fields, educationFields.append)}
            onRemove={(index) => removeField(educationFields.fields, index, educationFields.remove)}
          />

          <FieldArray
            title="Skills"
            fields={skillFields.fields}
            register={register}
            name="skills"
            placeholder="Python, React, Node.js, AWS, Docker, Kubernetes"
            onAdd={() => addField(skillFields.fields, skillFields.append)}
            onRemove={(index) => removeField(skillFields.fields, index, skillFields.remove)}
          />

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
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface FieldArrayProps {
  title: string;
  fields: any[];
  register: any;
  name: string;
  placeholder: string;
  onAdd: () => void;
  onRemove: (index: number) => void;
}

function FieldArray({ title, fields, register, name, placeholder, onAdd, onRemove }: FieldArrayProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        <button
          type="button"
          onClick={onAdd}
          className="inline-flex items-center px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
        >
          <Plus className="h-4 w-4 mr-1" />
          Add
        </button>
      </div>
      <div className="space-y-2">
        {fields.map((field, index) => (
          <div key={field.id} className="flex items-center space-x-2">
            <textarea
              {...register(`${name}.${index}`)}
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              placeholder={placeholder}
              rows={2}
            />
            {fields.length > 1 && (
              <button
                type="button"
                onClick={() => onRemove(index)}
                className="inline-flex items-center p-2 border border-gray-300 rounded-md text-gray-400 hover:text-red-600 hover:border-red-300"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}