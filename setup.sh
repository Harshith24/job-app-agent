#!/bin/bash

# Job Search AI Agent Setup Script
# This script helps you set up the local AI agent to replace your n8n workflow

set -e

echo "🚀 Job Search AI Agent Setup"
echo "=============================="

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it first:"
    echo "   - macOS: brew install ollama"
    echo "   - Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "   - Windows: Download from https://ollama.ai/download"
    exit 1
fi

echo "✅ Ollama is installed"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "🔄 Starting Ollama service..."
    ollama serve &
    sleep 3
fi

echo "✅ Ollama is running"

# Pull the required model (Llama 3.2 is good for this task)
echo "📥 Pulling Llama 3.2 model (this may take a few minutes)..."
if ! ollama list | grep -q "llama3.2"; then
    ollama pull llama3.2
fi

echo "✅ Llama 3.2 model ready"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

echo "✅ Python dependencies installed"

# Create config directory if it doesn't exist
if [ ! -d "config" ]; then
    mkdir -p config
    echo "📁 Created config directory"
fi

# Create output directory if it doesn't exist
if [ ! -d "output" ]; then
    mkdir -p output
    echo "📁 Created output directory"
fi

# Check for API keys
echo ""
echo "🔑 API Keys Setup"
echo "=================="
echo "You'll need API keys for job search. You can get them from:"
echo "- JSearch (RapidAPI): https://rapidapi.com/letscrape-6bRKe3QkOiy/api/jsearch"
echo "- Adzuna: https://developer.adzuna.com/"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Job Search Agent Configuration

# Paths
CONFIG_PATH=./config
OUTPUT_PATH=./output
TOP_N_JOBS=10

# Ollama Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Job Search APIs (optional - at least one required)
# JSEARCH_API_KEY=your_jsearch_api_key_here
# ADZUNA_APP_ID=your_adzuna_app_id_here
# ADZUNA_APP_KEY=your_adzuna_app_key_here
EOF
    echo "📝 Created .env file template"
    echo "   ⚠️  Please edit .env and add your API keys!"
else
    echo "✅ .env file already exists"
fi

# Check config files
if [ ! -f "config/job-criteria.md" ]; then
    echo "📝 Please edit config/job-criteria.md with your job search criteria"
fi

if [ ! -f "config/profile.md" ]; then
    echo "📝 Please edit config/profile.md with your professional profile"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Edit config/job-criteria.md with your job search criteria"
echo "3. Edit config/profile.md with your professional profile"
echo "4. Test the agent: python job_agent.py --run-once"
echo "5. Set up daily schedule: python job_agent.py (runs at 7:00 AM daily)"
echo ""
echo "For help, run: python job_agent.py --help"