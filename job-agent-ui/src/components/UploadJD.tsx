'use client';

import { useState, useRef, useEffect } from 'react';
import {
  FileText, Loader2, Download, Sparkles, Upload, Briefcase, GraduationCap,
  Wrench, FolderOpen, Award, ChevronDown, ChevronUp, Trash2,
} from 'lucide-react';
import { apiClient, handleApiError } from '@/lib/api';
import { GenerateFromJDResponse, ResumeData, CoverLetterData } from '@/types';

export function UploadJD() {
  const [jobDescription, setJobDescription] = useState('');
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [location, setLocation] = useState('');
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateFromJDResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<'resume' | 'cover' | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const savedJD = localStorage.getItem('upload_jd_description');
    const savedTitle = localStorage.getItem('upload_jd_title');
    const savedCompany = localStorage.getItem('upload_jd_company');
    const savedLocation = localStorage.getItem('upload_jd_location');

    if (savedJD) setJobDescription(savedJD);
    if (savedTitle) setTitle(savedTitle);
    if (savedCompany) setCompany(savedCompany);
    if (savedLocation) setLocation(savedLocation);
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    localStorage.setItem('upload_jd_description', jobDescription);
  }, [jobDescription]);

  useEffect(() => {
    localStorage.setItem('upload_jd_title', title);
  }, [title]);

  useEffect(() => {
    localStorage.setItem('upload_jd_company', company);
  }, [company]);

  useEffect(() => {
    localStorage.setItem('upload_jd_location', location);
  }, [location]);

  const handleClear = () => {
    setJobDescription('');
    setTitle('');
    setCompany('');
    setLocation('');
    setResult(null);
    setError(null);
    localStorage.removeItem('upload_jd_description');
    localStorage.removeItem('upload_jd_title');
    localStorage.removeItem('upload_jd_company');
    localStorage.removeItem('upload_jd_location');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setJobDescription(String(reader.result));
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleGenerate = async () => {
    if (!jobDescription.trim()) {
      setError('Paste or upload a job description first.');
      return;
    }
    setError(null);
    setResult(null);
    setGenerating(true);
    try {
      const data = await apiClient.generateFromJobDescription({
        job_description: jobDescription.trim(),
        title: title.trim() || undefined,
        company: company.trim() || undefined,
        location: location.trim() || undefined,
      });
      setResult(data);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPdf = async (type: 'resume' | 'cover') => {
    if (!result?.id) return;
    setDownloading(type);
    try {
      const blob = type === 'resume'
        ? await apiClient.downloadResumePdf(result.id)
        : await apiClient.downloadCoverLetterPdf(result.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const slug = result.company.replace(/\s+/g, '-').toLowerCase();
      a.download = type === 'resume' ? `resume-${slug}.pdf` : `cover-letter-${slug}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Input card ── */}
      <div className="card p-6 sm:p-8">
        <div className="flex items-start gap-3 mb-6">
          <div className="p-2 rounded-[var(--radius)] bg-[var(--color-accent-muted)] text-[var(--color-accent)]">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">On-demand documents</h2>
            <p className="text-sm text-[var(--color-muted)] mt-0.5">
              Paste or upload a JD and we&apos;ll generate a tailored resume and cover letter
              as downloadable PDFs.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Job title (optional)</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
                   placeholder="e.g. Security Engineer" className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Company (optional)</label>
            <input type="text" value={company} onChange={(e) => setCompany(e.target.value)}
                   placeholder="e.g. Acme Inc." className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Location (optional)</label>
            <input type="text" value={location} onChange={(e) => setLocation(e.target.value)}
                   placeholder="e.g. Remote" className="input" />
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium">Job description *</label>
            <input ref={fileInputRef} type="file" accept=".txt,.md" onChange={handleFileChange} className="hidden" />
            <button type="button" onClick={() => fileInputRef.current?.click()} className="btn-secondary text-sm py-1.5">
              <Upload className="w-4 h-4" /> Upload file
            </button>
          </div>
          <textarea
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            placeholder="Paste the full job description here or upload a .txt / .md file…"
            rows={10}
            className="input min-h-[220px] resize-y"
          />
        </div>

        {error && (
          <div className="mb-4 p-4 rounded-[var(--radius)] bg-red-50 border border-red-100 text-red-700 text-sm">{error}</div>
        )}

        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={handleGenerate} disabled={generating} className="btn-primary px-6 py-3">
            {generating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
            {generating ? 'Generating…' : 'Generate resume & cover letter'}
          </button>
          <button type="button" onClick={handleClear} className="btn-secondary px-6 py-3 text-red-500 hover:text-red-700">
            <Trash2 className="w-5 h-5" />
            Clear all
          </button>
        </div>
      </div>

      {/* ── Results ── */}
      {result && (
        <div className="space-y-6">
          {/* Download bar */}
          <div className="card p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold text-base">Documents ready</h3>
              <p className="text-sm text-[var(--color-muted)]">
                {result.title} at {result.company}
              </p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => handleDownloadPdf('resume')} disabled={downloading === 'resume'} className="btn-primary py-2.5 px-5">
                {downloading === 'resume' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Resume PDF
              </button>
              <button onClick={() => handleDownloadPdf('cover')} disabled={downloading === 'cover'} className="btn-secondary py-2.5 px-5">
                {downloading === 'cover' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Cover Letter PDF
              </button>
            </div>
          </div>

          {/* Previews */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ResumePreview data={result.resume_data} />
            <CoverLetterPreview data={result.cover_letter_data} />
          </div>
        </div>
      )}
    </div>
  );
}


/* ── Resume structured preview ── */

function ResumePreview({ data }: { data: ResumeData }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className="card overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="card-header flex items-center justify-between w-full text-left"
      >
        <span className="font-semibold">Resume preview</span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {expanded && (
        <div className="p-5 space-y-4 text-sm max-h-[520px] overflow-y-auto">
          {data.summary && (
            <Section icon={<FileText className="w-4 h-4" />} title="Summary">
              <p className="text-[var(--color-muted)] leading-relaxed">{data.summary}</p>
            </Section>
          )}

          {data.experience && data.experience.length > 0 && (
            <Section icon={<Briefcase className="w-4 h-4" />} title="Experience">
              {data.experience.map((exp, i) =>
                typeof exp === 'string' ? (
                  <p key={i} className="text-[var(--color-muted)]">&bull; {exp}</p>
                ) : (
                  <div key={i} className="mb-3">
                    <div className="flex justify-between items-baseline">
                      <span className="font-medium">{exp.title}{exp.company ? ` — ${exp.company}` : ''}</span>
                      {exp.duration && <span className="text-xs text-[var(--color-muted)] shrink-0 ml-2">{exp.duration}</span>}
                    </div>
                    {exp.bullets?.map((b, j) => (
                      <p key={j} className="text-[var(--color-muted)] ml-3">&bull; {b}</p>
                    ))}
                  </div>
                )
              )}
            </Section>
          )}

          {data.education && data.education.length > 0 && (
            <Section icon={<GraduationCap className="w-4 h-4" />} title="Education">
              {data.education.map((edu, i) =>
                typeof edu === 'string' ? (
                  <p key={i} className="text-[var(--color-muted)]">&bull; {edu}</p>
                ) : (
                  <div key={i} className="flex justify-between items-baseline">
                    <span>{edu.degree}{edu.school ? ` — ${edu.school}` : ''}</span>
                    {edu.year && <span className="text-xs text-[var(--color-muted)] ml-2">{edu.year}</span>}
                  </div>
                )
              )}
            </Section>
          )}

          {data.skills && data.skills.length > 0 && (
            <Section icon={<Wrench className="w-4 h-4" />} title="Skills">
              <div className="flex flex-wrap gap-1.5">
                {data.skills.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-[var(--color-accent-muted)] text-[var(--color-accent)] text-xs font-medium">
                    {s}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {data.projects && data.projects.length > 0 && (
            <Section icon={<FolderOpen className="w-4 h-4" />} title="Projects">
              {data.projects.map((p, i) =>
                typeof p === 'string' ? (
                  <p key={i} className="text-[var(--color-muted)]">&bull; {p}</p>
                ) : (
                  <div key={i}>
                    <span className="font-medium">{p.name}</span>
                    {p.description && <span className="text-[var(--color-muted)]"> — {p.description}</span>}
                  </div>
                )
              )}
            </Section>
          )}

          {data.certifications && data.certifications.length > 0 && (
            <Section icon={<Award className="w-4 h-4" />} title="Certifications">
              {data.certifications.map((c, i) => (
                <p key={i} className="text-[var(--color-muted)]">&bull; {c}</p>
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}


/* ── Cover letter preview ── */

function CoverLetterPreview({ data }: { data: CoverLetterData }) {
  const [expanded, setExpanded] = useState(true);
  const paragraphs = data.body || data.paragraphs || [];

  return (
    <div className="card overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="card-header flex items-center justify-between w-full text-left"
      >
        <span className="font-semibold">Cover letter preview</span>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {expanded && (
        <div className="p-5 space-y-4 text-sm max-h-[520px] overflow-y-auto leading-relaxed">
          {data.greeting && <p className="font-medium">{data.greeting}</p>}
          {paragraphs.map((p, i) => (
            <p key={i} className="text-[var(--color-muted)]">{p}</p>
          ))}
          {data.closing && (
            <p className="font-medium pt-2">{data.closing}</p>
          )}
        </div>
      )}
    </div>
  );
}


/* ── Shared section component ── */

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[var(--color-accent)]">{icon}</span>
        <h4 className="font-semibold text-xs uppercase tracking-wide">{title}</h4>
      </div>
      {children}
    </div>
  );
}
