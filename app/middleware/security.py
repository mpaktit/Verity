"""Security middleware including rate limiting and input validation."""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import re
from typing import Optional


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def validate_url(url: str) -> bool:
    """Validate URL format and ensure it's not a local/internal address."""
    if not url:
        return False

    # Basic URL format validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False

    # Block internal/private IPs
    private_ip_patterns = [
        r'127\.0\.0\.1',
        r'10\.',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
        r'192\.168\.',
        r'localhost',
    ]

    for pattern in private_ip_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False

    return True


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return ""

    # Limit length
    text = text[:max_length]

    # Remove potentially dangerous characters
    # This is a basic sanitization - in production, use more sophisticated libraries
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)

    return text


def get_security_middleware() -> list[Middleware]:
    """Get list of security middleware."""
    return [
        Middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        ),
        Middleware(GZipMiddleware, minimum_size=1000),
        Middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*"],  # "*" for development, restrict in production
        ),
    ]


async def validate_request_body(request: Request) -> dict:
    """Validate and sanitize request body."""
    try:
        body = await request.json()

        # Recursively sanitize string values
        def sanitize_dict(data: dict) -> dict:
            sanitized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    sanitized[key] = sanitize_input(value)
                elif isinstance(value, dict):
                    sanitized[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    sanitized[key] = [sanitize_input(item) if isinstance(item, str) else item for item in value]
                else:
                    sanitized[key] = value
            return sanitized

        return sanitize_dict(body)

    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
