#!/usr/bin/env python3
"""
Job Search AI Agent - Demo Script

This script demonstrates how to use the complete Job Search AI Agent system
with both backend API and frontend UI.
"""

import os
import sys
import time
import subprocess
import signal
import webbrowser
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")

    # Check Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False

    # Check Node.js (for frontend)
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Node.js not found (required for frontend)")
            return False
        print(f"✅ Node.js {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Node.js not found (required for frontend)")
        return False

    # Check Ollama
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ollama not found")
            return False
        print(f"✅ {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Ollama not found")
        return False

    # Check if Ollama is running and has the model
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            if 'llama3.2' in model_names:
                print("✅ Llama 3.2 model available")
            else:
                print("⚠️  Llama 3.2 model not found (will be downloaded)")
        else:
            print("❌ Ollama not responding")
            return False
    except:
        print("❌ Cannot connect to Ollama")
        return False

    return True

def setup_demo_config():
    """Set up demo configuration files"""
    print("\n📝 Setting up demo configuration...")

    # Create config directory
    config_dir = Path('./config')
    config_dir.mkdir(exist_ok=True)

    # Create demo profile
    profile_path = config_dir / 'profile.md'
    if not profile_path.exists():
        profile_content = """# Demo Professional Profile

## Contact
- Name: Alex Johnson
- Email: alex.johnson@email.com
- Phone: +1 (555) 123-4567
- LinkedIn: https://linkedin.com/in/alexjohnson
- Location: San Francisco, CA

## Experience
- Senior Software Engineer at TechCorp (2022-Present)
  - Led development of AI-powered job search platform using Python, React, and machine learning
  - Built scalable microservices handling 10k+ requests per minute
  - Mentored junior developers and conducted technical interviews

- Software Engineer at StartupXYZ (2020-2022)
  - Developed full-stack web applications using Node.js and PostgreSQL
  - Implemented CI/CD pipelines reducing deployment time by 60%
  - Collaborated with cross-functional teams in agile environment

## Projects
- Job Search AI Agent - Built an intelligent job search platform that uses AI to match candidates with opportunities
- Real-time Chat Application - Developed scalable chat system using WebSockets and Redis
- E-commerce Platform - Created full-featured online store with payment integration

## Education
- Master of Science in Computer Science - Stanford University (2018-2020)
- Bachelor of Science in Software Engineering - UC Berkeley (2014-2018)

## Skills
- Programming: Python, JavaScript, TypeScript, Go
- Web Development: React, Next.js, Node.js, Express
- Cloud & DevOps: AWS, Docker, Kubernetes, Terraform
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Git, Jenkins, Elasticsearch, Grafana

## Certifications
- AWS Certified Solutions Architect - Amazon Web Services (2023)
- Certified Kubernetes Administrator - Cloud Native Computing Foundation (2022)
"""
        profile_path.write_text(profile_content)
        print("✅ Created demo profile")

    # Create demo criteria
    criteria_path = config_dir / 'job-criteria.md'
    if not criteria_path.exists():
        criteria_content = """# Job search criteria

## Roles and focus
- Roles: Senior Software Engineer, Tech Lead, Engineering Manager
- Keywords: python, react, typescript, ai, machine learning, cloud

## Experience level
- Target levels: senior, lead, principal
- Employment types: full-time, contract

## Location and remote
- Locations: remote, San Francisco, New York, Seattle
"""
        criteria_path.write_text(criteria_content)
        print("✅ Created demo search criteria")

def start_backend_api():
    """Start the backend API server"""
    print("\n🚀 Starting backend API server...")
    cmd = [sys.executable, '-m', 'src.main', '--api', '--port', '8000']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def start_frontend():
    """Start the frontend development server"""
    print("\n🎨 Starting frontend development server...")
    os.chdir('job-agent-ui')
    cmd = ['npm', 'run', 'dev']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def wait_for_services(api_process, frontend_process):
    """Wait for services to be ready"""
    print("\n⏳ Waiting for services to start...")

    # Wait for API
    for i in range(30):
        try:
            import requests
            response = requests.get('http://localhost:8000/api/health', timeout=2)
            if response.status_code == 200:
                print("✅ Backend API ready")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ Backend API failed to start")
        return False

    # Wait for frontend
    for i in range(30):
        try:
            response = requests.get('http://localhost:3000', timeout=2)
            if response.status_code == 200:
                print("✅ Frontend ready")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ Frontend failed to start")
        return False

    return True

def open_browser():
    """Open browser to the application"""
    print("\n🌐 Opening browser...")
    webbrowser.open('http://localhost:3000')

def main():
    """Main demo function"""
    print("🎯 Job Search AI Agent - Full Stack Demo")
    print("=" * 50)

    if not check_requirements():
        print("\n❌ Requirements not met. Please install missing dependencies.")
        return 1

    setup_demo_config()

    # Start services
    api_process = start_backend_api()
    time.sleep(2)  # Give API time to start

    frontend_process = start_frontend()
    time.sleep(3)  # Give frontend time to start

    try:
        if wait_for_services(api_process, frontend_process):
            print("\n" + "=" * 50)
            print("🎉 Demo environment ready!")
            print("=" * 50)
            print("📱 Frontend: http://localhost:3000")
            print("🔧 Backend API: http://localhost:8000")
            print("📊 API Health: http://localhost:8000/api/health")
            print("")
            print("📋 What you can do:")
            print("1. Go to the Profile tab to view/edit your professional information")
            print("2. Check the Search Criteria tab to set job preferences")
            print("3. Run a job search in the Job Search tab")
            print("4. View and manage applications in the My Applications tab")
            print("")
            print("⚠️  Note: Job search requires API keys (JSearch/Adzuna)")
            print("   Set them in .env file for full functionality")
            print("")
            print("Press Ctrl+C to stop all services")

            open_browser()

            # Keep running until interrupted
            while True:
                time.sleep(1)

        else:
            print("\n❌ Failed to start services")
            return 1

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down services...")
    finally:
        # Cleanup
        if frontend_process and frontend_process.poll() is None:
            frontend_process.terminate()
            frontend_process.wait()
        if api_process and api_process.poll() is None:
            api_process.terminate()
            api_process.wait()

        print("✅ All services stopped")
        # return 0

if __name__ == '__main__':
    sys.exit(main())