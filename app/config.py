"""Application configuration with environment variable support."""

import os
from pathlib import Path
from typing import Optional


class Settings:
    def __init__(self) -> None:
        self.APP_NAME = os.environ.get('APP_NAME', 'Verity')
        self.APP_VERSION = os.environ.get('APP_VERSION', '0.2.0')
        self.DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

        # Database
        self.DATABASE_URL = os.environ.get(
            'DATABASE_URL',
            f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'verity.db'}",
        )

        # Security
        self.SECRET_KEY = os.environ.get('SECRET_KEY', self._generate_secret())
        self.ACCESS_TOKEN_EXPIRE_HOURS = int(
            os.environ.get('ACCESS_TOKEN_EXPIRE_HOURS', '24')
        )
        self.PBKDF2_ITERATIONS = int(os.environ.get('PBKDF2_ITERATIONS', '200000'))

        # Monitoring
        self.CRAWL_INTERVAL_SECONDS = int(
            os.environ.get('CRAWL_INTERVAL_SECONDS', '300')
        )
        self.MAX_SOURCES_PER_RUN = int(
            os.environ.get('MAX_SOURCES_PER_RUN', '20')
        )
        self.CRAWL_TIMEOUT_SECONDS = int(
            os.environ.get('CRAWL_TIMEOUT_SECONDS', '15')
        )
        self.USER_AGENT = os.environ.get(
            'USER_AGENT', 'Verity-Public-Research/0.2 (+https://verity.example)'
        )

        # Rate limiting
        self.RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '60'))
        self.RATE_LIMIT_WINDOW_SECONDS = int(
            os.environ.get('RATE_LIMIT_WINDOW_SECONDS', '60')
        )

        # CORS
        cors_origins = os.environ.get('CORS_ORIGINS', '*')
        self.CORS_ORIGINS = (
            [o.strip() for o in cors_origins.split(',') if o.strip()]
            if cors_origins != '*'
            else ['*']
        )

        # Frontend
        self.FRONTEND_DIR = Path(__file__).resolve().parent / 'static'

        # Logging
        self.LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
        self.LOG_FORMAT = os.environ.get(
            'LOG_FORMAT', '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        )

    @staticmethod
    def _generate_secret() -> str:
        import secrets
        return secrets.token_urlsafe(32)

    def ensure_data_dir(self) -> Path:
        path = Path(self.DATABASE_URL.replace('sqlite:///', ''))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.parent


settings = Settings()
settings.ensure_data_dir()