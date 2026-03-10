"""Basic tests for Job Search Agent"""

import unittest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path
import requests

from src.config.settings import config
from src.models.job import Job, JobSearchCriteria, UserProfile
from src.services.ollama import OllamaClient, JobRanker, DocumentGenerator
from src.services.job_search import JobSearchService
from src.services.output import OutputService
from src.core.agent import JobSearchAgent

class TestJobModels(unittest.TestCase):
    """Test job data models"""

    def test_job_creation(self):
        """Test Job dataclass creation"""
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            location="Remote",
            description="Great job",
            url="https://example.com/job"
        )
        self.assertEqual(job.title, "Software Engineer")
        self.assertEqual(job.company, "Tech Corp")

    def test_job_search_criteria_parsing(self):
        """Test parsing job search criteria from markdown"""
        markdown = """
## Roles and focus
- Roles: Software Engineer, Developer
- Keywords: python, javascript

## Experience level
- Target levels: entry, junior
"""
        criteria = JobSearchCriteria.from_markdown(markdown)
        # Check that some keywords were extracted
        self.assertTrue(len(criteria.keywords) > 0)
        self.assertTrue(len(criteria.experience_levels) > 0)
        self.assertIn("entry", criteria.experience_levels)

    def test_user_profile_parsing(self):
        """Test parsing user profile from markdown"""
        markdown = """
## Contact
- Name: John Doe
- Email: john@example.com

## Experience
- Senior Developer at Tech Corp
"""
        profile = UserProfile.from_markdown(markdown)
        # Check that some data was parsed
        self.assertIsNotNone(profile)
        self.assertTrue(len(profile.experience) > 0)

class TestOllamaClient(unittest.TestCase):
    """Test Ollama client"""

    @patch('src.services.ollama.requests.post')
    def test_generate_success(self, mock_post):
        """Test successful text generation"""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        mock_post.return_value = mock_response

        client = OllamaClient("http://localhost:11434", "test-model")
        result = client.generate("Test prompt")

        self.assertEqual(result, "Generated text")
        mock_post.assert_called_once()

    @patch('src.services.ollama.requests.post')
    def test_generate_failure(self, mock_post):
        """Test generation failure handling"""
        from src.services.ollama import OllamaError
        from tenacity import RetryError

        mock_post.side_effect = requests.RequestException("Connection failed")

        client = OllamaClient("http://localhost:11434", "test-model")

        # Should raise RetryError wrapping OllamaError
        with self.assertRaises(RetryError):
            client.generate("Test prompt")

class TestJobRanker(unittest.TestCase):
    """Test job ranking functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_ollama = Mock()
        self.ranker = JobRanker(self.mock_ollama)

    def test_keyword_ranking(self):
        """Test keyword-based ranking"""
        jobs = [
            Job("Python Developer", "Company A", "Remote", "Python development", "url1"),
            Job("Java Developer", "Company B", "NYC", "Java development", "url2"),
            Job("Python Engineer", "Company C", "Remote", "Senior python role", "url3")
        ]

        ranked = self.ranker._keyword_ranking(jobs, ["python"])

        # Python jobs should rank higher than Java job
        python_job1 = jobs[0]  # "Python Developer"
        python_job2 = jobs[2]  # "Python Engineer"
        java_job = jobs[1]     # "Java Developer"

        self.assertGreater(ranked[python_job1], ranked[java_job])
        self.assertGreater(ranked[python_job2], ranked[java_job])

class TestOutputService(unittest.TestCase):
    """Test output generation"""

    def setUp(self):
        """Set up temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        config.app.output_path = Path(self.temp_dir)
        self.output_service = OutputService()

    def test_safe_filename(self):
        """Test filename sanitization"""
        unsafe = 'File:with<bad>chars?|and"quotes'
        safe = self.output_service._safe_filename(unsafe)
        self.assertEqual(safe, 'File_with_bad_chars_and_quotes')

class TestJobSearchAgent(unittest.TestCase):
    """Test main agent functionality"""

    def setUp(self):
        """Set up test agent with mocked services"""
        self.temp_dir = tempfile.mkdtemp()
        config.app.config_path = Path(self.temp_dir) / "config"
        config.app.output_path = Path(self.temp_dir) / "output"

        # Create test config files
        config.app.config_path.mkdir(parents=True, exist_ok=True)
        (config.app.config_path / "job-criteria.md").write_text("# Test criteria\n- Keywords: python")
        (config.app.config_path / "profile.md").write_text("# Test profile\n- Name: Test User")

    @patch('src.core.agent.JobSearchService')
    @patch('src.core.agent.JobRanker')
    @patch('src.core.agent.DocumentGenerator')
    @patch('src.core.agent.OutputService')
    def test_run_search_cycle(self, mock_output, mock_doc_gen, mock_ranker, mock_search):
        """Test complete search cycle"""
        # Setup mocks
        mock_search_instance = Mock()
        mock_search.return_value = mock_search_instance
        mock_search_instance.search_jobs.return_value = [
            Job("Test Job", "Test Company", "Remote", "Description", "url")
        ]

        mock_ranker_instance = Mock()
        mock_ranker.return_value = mock_ranker_instance
        mock_ranker_instance.rank_jobs.return_value = [
            Job("Test Job", "Test Company", "Remote", "Description", "url")
        ]

        mock_doc_gen_instance = Mock()
        mock_doc_gen.return_value = mock_doc_gen_instance
        mock_doc_gen_instance.generate_application.return_value = ("Resume content", "Cover letter content")

        mock_output_instance = Mock()
        mock_output.return_value = mock_output_instance
        mock_output_instance.generate_output.return_value = "/tmp/test-output"

        agent = JobSearchAgent()
        result = agent.run_search_cycle()

        self.assertIsNotNone(result)
        mock_search_instance.search_jobs.assert_called_once()
        mock_ranker_instance.rank_jobs.assert_called_once()

if __name__ == '__main__':
    unittest.main()