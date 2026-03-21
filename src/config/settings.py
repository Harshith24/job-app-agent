"""Configuration management for Job Search Agent"""

import os
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AppConfig:
    """Application configuration"""
    # Paths
    config_path: Path = Path(os.getenv('CONFIG_PATH', './config'))
    output_path: Path = Path(os.getenv('OUTPUT_PATH', './output'))

    # Job processing
    top_n_jobs: int = int(os.getenv('TOP_N_JOBS', '10'))

    # Ollama settings
    ollama_url: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    ollama_model: str = os.getenv('OLLAMA_MODEL', 'llama3.2')

    # API Keys
    jsearch_api_key: Optional[str] = os.getenv('JSEARCH_API_KEY')
    adzuna_app_id: Optional[str] = os.getenv('ADZUNA_APP_ID')
    adzuna_app_key: Optional[str] = os.getenv('ADZUNA_APP_KEY')

    # Service settings
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    request_timeout: int = int(os.getenv('REQUEST_TIMEOUT', '120'))

    # Agent settings
    relevance_threshold: int = int(os.getenv('RELEVANCE_THRESHOLD', '80'))
    agent_interval_minutes: int = int(os.getenv('AGENT_INTERVAL_MINUTES', '60'))

    # Supabase
    supabase_url: str = os.getenv('SUPABASE_URL', '')
    supabase_anon_key: str = os.getenv('SUPABASE_ANON_KEY', '')
    supabase_service_role_key: str = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

    # CORS — comma-separated origins (used by server.py)
    cors_origins: str = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000',
    )

    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: str = os.getenv('LOG_FILE', '')

@dataclass
class ServiceHealth:
    """Service health status"""
    service_name: str
    is_healthy: bool
    last_check: Optional[float] = None
    error_message: Optional[str] = None

class Config:
    """Centralized configuration management"""

    def __init__(self):
        self.app = AppConfig()
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging"""
        handlers: list[logging.Handler] = [logging.StreamHandler()]
        if self.app.log_file:
            try:
                handlers.append(logging.FileHandler(self.app.log_file))
            except OSError:
                pass
        logging.basicConfig(
            level=getattr(logging, self.app.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )

    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger"""
        return logging.getLogger(name)

    def ensure_directories(self):
        """Ensure required directories exist"""
        self.app.config_path.mkdir(parents=True, exist_ok=True)
        self.app.output_path.mkdir(parents=True, exist_ok=True)

# Global config instance
config = Config()