"""REST API server for Job Search Agent"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from src.config.settings import config
from src.core.agent import JobSearchAgent
from src.models.job import JobApplication, UserProfile

logger = logging.getLogger(__name__)

class JobAgentAPI:
    """REST API for Job Search Agent"""

    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for frontend

        self.agent = JobSearchAgent()
        self.applications_file = config.app.config_path / 'applications.json'

        self.setup_routes()

    def setup_routes(self):
        """Setup API routes"""

        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            health = self.agent.health_check()
            return jsonify(health), 200 if health['overall'] else 503

        @self.app.route('/api/profile', methods=['GET', 'POST'])
        def profile():
            """Get or update user profile"""
            if request.method == 'GET':
                try:
                    profile = self.agent._load_profile()
                    if profile:
                        return jsonify({
                            'name': profile.name,
                            'email': profile.email,
                            'phone': profile.phone,
                            'linkedin': profile.linkedin,
                            'location': profile.location,
                            'experience': profile.experience,
                            'projects': profile.projects,
                            'certifications': profile.certifications,
                            'education': profile.education,
                            'skills': profile.skills
                        })
                    return jsonify({}), 404
                except Exception as e:
                    logger.error(f"Failed to load profile: {e}")
                    return jsonify({'error': 'Failed to load profile'}), 500

            elif request.method == 'POST':
                try:
                    data = request.json
                    if not data:
                        return jsonify({'error': 'No data provided'}), 400

                    # Create profile object
                    profile = UserProfile(
                        name=data.get('name'),
                        email=data.get('email'),
                        phone=data.get('phone'),
                        linkedin=data.get('linkedin'),
                        location=data.get('location'),
                        experience=data.get('experience', []),
                        projects=data.get('projects', []),
                        certifications=data.get('certifications', []),
                        education=data.get('education', []),
                        skills=data.get('skills', [])
                    )

                    # Save to file
                    profile_file = config.app.config_path / 'profile.md'
                    profile_file.write_text(profile.to_markdown(), encoding='utf-8')

                    logger.info("Profile updated successfully")
                    return jsonify({'message': 'Profile updated successfully'})

                except Exception as e:
                    logger.error(f"Failed to update profile: {e}")
                    return jsonify({'error': 'Failed to update profile'}), 500

        @self.app.route('/api/criteria', methods=['GET', 'POST'])
        def criteria():
            """Get or update job search criteria"""
            if request.method == 'GET':
                try:
                    criteria = self.agent._load_criteria()
                    if criteria:
                        return jsonify({
                            'keywords': criteria.keywords,
                            'locations': criteria.locations,
                            'experience_levels': criteria.experience_levels,
                            'job_types': criteria.job_types,
                            'exclude_terms': criteria.exclude_terms
                        })
                    return jsonify({}), 404
                except Exception as e:
                    logger.error(f"Failed to load criteria: {e}")
                    return jsonify({'error': 'Failed to load criteria'}), 500

            elif request.method == 'POST':
                try:
                    data = request.json
                    if not data:
                        return jsonify({'error': 'No data provided'}), 400

                    # Create criteria markdown
                    criteria_md = f"""# Job search criteria

## Roles and focus
- Roles: {', '.join(data.get('keywords', []))}
- Keywords: {', '.join(data.get('keywords', []))}

## Experience level
- Target levels: {', '.join(data.get('experience_levels', []))}

## Location and remote
- Locations: {', '.join(data.get('locations', []))}

## Employment types
- Types: {', '.join(data.get('job_types', []))}
"""

                    # Save to file
                    criteria_file = config.app.config_path / 'job-criteria.md'
                    criteria_file.write_text(criteria_md, encoding='utf-8')

                    logger.info("Criteria updated successfully")
                    return jsonify({'message': 'Criteria updated successfully'})

                except Exception as e:
                    logger.error(f"Failed to update criteria: {e}")
                    return jsonify({'error': 'Failed to update criteria'}), 500

        @self.app.route('/api/search', methods=['POST'])
        def search():
            """Trigger job search"""
            try:
                result = self.agent.run_search_cycle()
                if result:
                    return jsonify({
                        'message': 'Job search completed',
                        'output_path': result
                    })
                else:
                    return jsonify({'error': 'Job search failed'}), 500
            except Exception as e:
                logger.error(f"Job search failed: {e}")
                return jsonify({'error': 'Job search failed'}), 500

        @self.app.route('/api/jobs', methods=['GET'])
        def get_jobs():
            """Get job results"""
            try:
                # Read the latest job list CSV
                output_dirs = sorted(config.app.output_path.glob('*/'), key=lambda x: x.stat().st_mtime, reverse=True)
                if not output_dirs:
                    return jsonify({'jobs': []})

                latest_dir = output_dirs[0]
                csv_file = latest_dir / 'job-list.csv'

                if not csv_file.exists():
                    return jsonify({'jobs': []})

                # Parse CSV
                import csv
                jobs = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Get application status
                        applications = self.load_applications()
                        job_key = f"{row['Title']}|{row['Company']}|{row['URL']}"
                        status = applications.get(job_key, {}).get('status', 'not_applied')

                        job = {
                            'title': row['Title'],
                            'company': row['Company'],
                            'location': row['Location'],
                            'url': row['URL'],
                            'resume_file': row['Resume File'],
                            'cover_file': row['Cover File'],
                            'status': status,
                            'output_dir': str(latest_dir)
                        }
                        jobs.append(job)

                return jsonify({'jobs': jobs})

            except Exception as e:
                logger.error(f"Failed to get jobs: {e}")
                return jsonify({'error': 'Failed to get jobs'}), 500

        @self.app.route('/api/applications/<path:job_key>', methods=['POST'])
        def update_application(job_key):
            """Update application status"""
            try:
                data = request.json
                if not data or 'status' not in data:
                    return jsonify({'error': 'Status required'}), 400

                applications = self.load_applications()
                applications[job_key] = {
                    'status': data['status'],
                    'updated_at': datetime.now().isoformat(),
                    'notes': data.get('notes', '')
                }

                self.save_applications(applications)
                return jsonify({'message': 'Application updated successfully'})

            except Exception as e:
                logger.error(f"Failed to update application: {e}")
                return jsonify({'error': 'Failed to update application'}), 500

        @self.app.route('/api/job/<path:job_key>', methods=['GET'])
        def get_job_details(job_key):
            """Get job details and documents"""
            try:
                # Find the job in recent results
                output_dirs = sorted(config.app.output_path.glob('*/'), key=lambda x: x.stat().st_mtime, reverse=True)

                for output_dir in output_dirs[:5]:  # Check last 5 runs
                    csv_file = output_dir / 'job-list.csv'
                    if csv_file.exists():
                        import csv
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                current_key = f"{row['Title']}|{row['Company']}|{row['URL']}"
                                if current_key == job_key:
                                    # Read resume and cover files
                                    resume_file = output_dir / row['Resume File']
                                    cover_file = output_dir / row['Cover File']

                                    resume_content = resume_file.read_text(encoding='utf-8') if resume_file.exists() else ""
                                    cover_content = cover_file.read_text(encoding='utf-8') if cover_file.exists() else ""

                                    return jsonify({
                                        'title': row['Title'],
                                        'company': row['Company'],
                                        'location': row['Location'],
                                        'url': row['URL'],
                                        'resume': resume_content,
                                        'cover_letter': cover_content
                                    })

                return jsonify({'error': 'Job not found'}), 404

            except Exception as e:
                logger.error(f"Failed to get job details: {e}")
                return jsonify({'error': 'Failed to get job details'}), 500

    def load_applications(self) -> Dict[str, Dict]:
        """Load application tracking data"""
        try:
            if self.applications_file.exists():
                return json.loads(self.applications_file.read_text(encoding='utf-8'))
            return {}
        except Exception as e:
            logger.error(f"Failed to load applications: {e}")
            return {}

    def save_applications(self, applications: Dict[str, Dict]):
        """Save application tracking data"""
        try:
            self.applications_file.write_text(json.dumps(applications, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save applications: {e}")

    def run(self, host='0.0.0.0', port=8000, debug=False):
        """Run the API server"""
        logger.info(f"Starting Job Agent API on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)