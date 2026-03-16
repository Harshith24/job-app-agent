# Job Search AI Agent

AI agent that finds jobs matching your criteria, ranks them with Ollama, and generates tailored resumes and cover letters. Uses **Supabase** for auth + data, **FastAPI** for the backend, **Next.js** for the UI, and **Ollama** running locally for the LLM.

## Architecture

```
┌──────────────────────────────────────────┐
│          Railway (one project)            │
│                                          │
│  ┌──────────────┐   ┌────────────────┐   │
│  │   Frontend   │──▶│  API (FastAPI)  │   │
│  │   (Next.js)  │   │                │   │
│  └──────────────┘   └───────┬────────┘   │
│                              │            │
└──────────────────────────────┼────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                 ▼
     ┌──────────────┐              ┌────────────────────┐
     │   Supabase   │              │  Ollama (your Mac)  │
     │  (DB + Auth) │              │  via CF Tunnel       │
     └──────────────┘              └────────────────────┘
```

Two platforms total: **Railway** runs your app (frontend + API), **Supabase** stores your data and handles auth. Ollama runs on your own machine, exposed via a Cloudflare tunnel so the deployed API can reach it.

## Local development

```bash
# 1. Backend
cp .env.example .env          # fill in Supabase keys, job API keys
pip install -r requirements.txt
python -m src.main --api --port 8000

# 2. Frontend
cd job-agent-ui
cp .env.example .env.local    # fill in Supabase keys, set NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm install && npm run dev

# 3. Ollama
ollama serve                   # runs on localhost:11434 by default
```

Open **http://localhost:3000**.

## Deployment

### 1. Supabase (DB + Auth)

1. Create a project at [supabase.com](https://supabase.com).
2. **SQL Editor** → paste `supabase/schema.sql` → Run.
3. Copy **Project URL**, **anon key**, and **service role key** from Settings > API.

### 2. Ollama (your machine + Cloudflare Tunnel)

```bash
ollama serve
cloudflared tunnel --url http://localhost:11434
```

Note the tunnel URL (e.g. `https://abc-123.trycloudflare.com`).

### 3. Railway (frontend + API)

1. Go to [railway.app](https://railway.app) and create a new **project**.
2. Create **two services** from the same repo:

#### Service 1: API

- **Root Directory**: `/` (repo root)
- Railway auto-detects `Procfile` + `requirements.txt`.
- **Environment variables**:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | your project URL |
| `SUPABASE_ANON_KEY` | your anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | your service role key |
| `OLLAMA_URL` | your Cloudflare tunnel URL |
| `OLLAMA_MODEL` | `llama3.2` |
| `CORS_ORIGINS` | your frontend service URL (set after creating it) |
| `JSEARCH_API_KEY` | your key (if using JSearch) |
| `ADZUNA_APP_ID` | your id (if using Adzuna) |
| `ADZUNA_APP_KEY` | your key (if using Adzuna) |

#### Service 2: Frontend

- **Root Directory**: `job-agent-ui`
- Railway auto-detects Next.js.
- **Environment variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | your project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your anon key |
| `NEXT_PUBLIC_API_URL` | your API service URL + `/api` |

3. After both are deployed, copy the frontend's public URL and add it to the API's `CORS_ORIGINS`.

### Done

- Users sign up/in via Supabase Auth
- Frontend on Railway talks to API on Railway (same project)
- API calls Ollama via your Cloudflare tunnel
- All data in Supabase Postgres

## Project structure

```
job-app-agent/
├── src/                          # Python backend
│   ├── main.py                   # CLI + API entry
│   ├── api/
│   │   ├── server.py             # FastAPI routes
│   │   └── auth.py               # JWT auth
│   ├── db/
│   │   └── supabase_client.py    # DB helpers
│   ├── config/settings.py
│   ├── core/agent.py             # Search + rank + generate
│   ├── models/job.py
│   └── services/
│       ├── ollama.py
│       ├── job_search.py
│       └── output.py
├── job-agent-ui/                  # Next.js frontend
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── context/AuthContext.tsx
│   │   ├── lib/api.ts, supabase.ts
│   │   └── types/
│   └── .env.example
├── supabase/schema.sql            # Run in Supabase SQL Editor
├── Procfile                       # Railway uses this for the API
├── runtime.txt
├── requirements.txt
├── .env.example
└── README.md
```

## Database schema

| Table | Purpose |
|-------|---------|
| `profiles` | 1:1 with auth.users — name, contact info, experience/projects/certs/education/skills (JSONB). Auto-created on signup. |
| `search_criteria` | 1:1 per user — keywords, locations, experience levels, job types, exclude terms (JSONB). |
| `jobs` | Per-user — title, company, description, URL, source, added_by (user/agent), status, resume/cover letter text. Unique on (user_id, title, company, url). |

All tables have RLS — users can only access their own rows.

## Configuration

See `.env.example` (backend) and `job-agent-ui/.env.example` (frontend).

## Requirements

- Python 3.8+
- Node 18+
- [Ollama](https://ollama.com/) with a model (e.g. `llama3.2`)
- A [Supabase](https://supabase.com) project
- A [Railway](https://railway.app) account (free tier: $5/month credit)
- Optional: job API keys ([JSearch](https://rapidapi.com/letscrape-6bRKe3QkOiy/api/jsearch), [Adzuna](https://developer.adzuna.com/))

## License

MIT.
