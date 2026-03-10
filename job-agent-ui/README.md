# Job Search AI Agent - Frontend UI

A modern React/TypeScript frontend for the Job Search AI Agent, built with Next.js and Tailwind CSS.

## Features

- **Profile Management**: Easy-to-use forms for entering professional information
- **Search Criteria Configuration**: Set job search preferences through a user-friendly interface
- **Job Search**: Trigger AI-powered job searches with one click
- **Application Tracking**: View, manage, and track job applications
- **Document Generation**: View generated resumes and cover letters
- **Responsive Design**: Works on desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js 18+
- The Job Agent backend API running on `http://localhost:8000`

### Quick Start (with Demo)

The easiest way to get started is to use the demo script from the parent directory:

```bash
# From the job-search-agent directory
python3 demo.py
```

This will start both the backend API and frontend automatically.

### Manual Installation

1. Install dependencies:
```bash
npm install
```

2. Start the backend API (in another terminal):
```bash
# From the job-search-agent directory
python3 -m src.main --api --port 8000
```

3. Start the frontend development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Backend Setup

Make sure the Job Agent backend is running:

```bash
# In a separate terminal, start the API server
python -m src.main --api --port 8000
```

## Usage

### 1. Set Up Your Profile
- Go to the "Profile" tab
- Fill in your contact information, experience, projects, certifications, education, and skills
- Save your profile

### 2. Configure Search Criteria
- Go to the "Search Criteria" tab
- Enter keywords, locations, experience levels, and job types
- Save your criteria

### 3. Run Job Search
- Go to the "Job Search" tab
- Click "Start Job Search" to find and rank jobs
- The AI will search job boards and generate personalized documents

### 4. Manage Applications
- Go to the "My Applications" tab
- View all found jobs with their status
- Update application status (interested, applied, interviewing, rejected)
- View generated resumes and cover letters
- Click job links to apply

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`:

- `GET /api/profile` - Get user profile
- `POST /api/profile` - Save user profile
- `GET /api/criteria` - Get search criteria
- `POST /api/criteria` - Save search criteria
- `POST /api/search` - Trigger job search
- `GET /api/jobs` - Get job results
- `GET /api/job/{key}` - Get job details and documents
- `POST /api/applications/{key}` - Update application status

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Forms**: React Hook Form with Zod validation
- **HTTP Client**: Axios
- **Icons**: Lucide React

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Project Structure

```
src/
├── app/                    # Next.js app directory
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Main page
│   └── globals.css        # Global styles
└── components/             # React components
    ├── ProfileForm.tsx    # Profile management
    ├── CriteriaForm.tsx   # Search criteria
    ├── JobSearch.tsx      # Job search trigger
    ├── JobList.tsx        # Application management
    └── ui/                # UI components
        └── Tabs.tsx       # Tab navigation
```

## Deployment

Build for production:

```bash
npm run build
npm start
```

The app will be available on port 3000 by default.

## Contributing

1. Make sure the backend API is running
2. Start the frontend development server
3. Make changes and test locally
4. Build and test production version

## License

MIT