"""App configuration loaded from environment variables."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # Paths
    config_path: Path = Path(os.getenv("CONFIG_PATH", "./config"))
    output_path: Path = Path(os.getenv("OUTPUT_PATH", "./output"))

    # Job processing
    top_n_jobs: int = int(os.getenv("TOP_N_JOBS", "10"))

    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")

    # Optional job-search API keys (currently unused — kept for future board integrations)
    jsearch_api_key: Optional[str] = os.getenv("JSEARCH_API_KEY")
    adzuna_app_id: Optional[str] = os.getenv("ADZUNA_APP_ID")
    adzuna_app_key: Optional[str] = os.getenv("ADZUNA_APP_KEY")

    # HTTP
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "300"))

    # Background agent
    relevance_threshold: int = int(os.getenv("RELEVANCE_THRESHOLD", "80"))
    agent_interval_minutes: int = int(os.getenv("AGENT_INTERVAL_MINUTES", "60"))

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # CORS
    cors_origins: str = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "")


settings = Settings()


def setup_logging():
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.log_file:
        try:
            handlers.append(logging.FileHandler(settings.log_file))
        except OSError:
            pass
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


setup_logging()
