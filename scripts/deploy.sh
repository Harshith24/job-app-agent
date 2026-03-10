#!/bin/bash

# Job Search Agent Deployment Script
# Deploys the agent using Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🚀 Job Search AI Agent Deployment"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
# Job Search Agent Configuration

# Paths
CONFIG_PATH=./config
OUTPUT_PATH=./output
TOP_N_JOBS=10

# Ollama Configuration
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2

# Job Search APIs (REQUIRED - get from respective services)
JSEARCH_API_KEY=your_jsearch_api_key_here
ADZUNA_APP_ID=your_adzuna_app_id_here
ADZUNA_APP_KEY=your_adzuna_app_key_here

# Application Settings
LOG_LEVEL=INFO
SCHEDULE_TIME=07:00
MAX_RETRIES=3
REQUEST_TIMEOUT=30
EOF
    echo "📝 Created .env template. Please edit with your API keys!"
    echo ""
fi

# Check for config files
if [ ! -d "config" ]; then
    echo "📁 Creating config directory..."
    mkdir -p config
fi

if [ ! -f "config/job-criteria.md" ]; then
    echo "📝 Creating job criteria template..."
    cat > config/job-criteria.md << 'EOF'
# Job search criteria

## Roles and focus
- Roles: Software Engineer with focus on cybersecurity, red team, blue team
- Keywords: security engineer, application security, penetration testing

## Experience level
- Target levels: entry, junior, mid-level
- Employment types: full-time, contract

## Location and remote
- Locations: remote, hybrid
EOF
fi

if [ ! -f "config/profile.md" ]; then
    echo "📝 Creating profile template..."
    cat > config/profile.md << 'EOF'
# My professional profile

## Contact
- Name: Your Full Name
- Email: your.email@example.com
- LinkedIn: https://linkedin.com/in/yourprofile

## Experience
- Current Role at Company Name (Dates)
  - Key responsibilities and achievements
- Previous Role at Company Name (Dates)
  - Key responsibilities and achievements

## Projects
- Project Name: Brief description of technologies and impact
- Another Project: Description and outcomes

## Education
- Degree, University Name, Graduation Year
- Relevant coursework or GPA

## Skills
- Technical: Python, JavaScript, Security Tools, etc.
- Soft Skills: Communication, Problem Solving, etc.

## Certifications
- Certification Name, Issuing Organization, Date
- Another Certification
EOF
fi

# Create output directory
mkdir -p output logs

echo "🔧 Building and starting services..."

# Use docker compose (newer syntax) if available, fallback to docker-compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Build and start services
$COMPOSE_CMD -f docker/docker-compose.yml up -d --build

echo "⏳ Waiting for services to be healthy..."

# Wait for Ollama to be ready
echo "Waiting for Ollama..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "✅ Ollama is ready"
        break
    fi
    echo "Waiting for Ollama... ($i/30)"
    sleep 2
done

# Pull the required model
echo "📥 Pulling Llama 3.2 model..."
docker exec ollama ollama pull llama3.2

# Wait for job agent to be healthy
echo "Waiting for Job Agent..."
for i in {1..30}; do
    if $COMPOSE_CMD -f docker/docker-compose.yml ps job-agent | grep -q "healthy"; then
        echo "✅ Job Agent is ready"
        break
    fi
    echo "Waiting for Job Agent... ($i/30)"
    sleep 2
done

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Service Status:"
$COMPOSE_CMD -f docker/docker-compose.yml ps
echo ""
echo "📊 View logs:"
echo "  $COMPOSE_CMD -f docker/docker-compose.yml logs -f job-agent"
echo ""
echo "🔧 Configuration:"
echo "  - Edit .env for API keys and settings"
echo "  - Edit config/job-criteria.md for search criteria"
echo "  - Edit config/profile.md for your profile"
echo "  - Output will be in ./output/ directory"
echo ""
echo "🛑 To stop: $COMPOSE_CMD -f docker/docker-compose.yml down"