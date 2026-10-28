"""Modular AI provider system with multi-key support, auto-failover, and rate limiting."""

import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

from app.config import settings
from app.db import get_connection


class ProviderType(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
    TOGETHER = "together"
    OPENROUTER = "openrouter"
    CUSTOM = "custom"


class ModelTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class AIModel:
    id: str
    name: str
    provider: ProviderType
    tier: ModelTier
    context_tokens: int
    max_output_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float


@dataclass
class APIKey:
    id: str
    provider: ProviderType
    key_name: str
    api_key: str
    rate_limit_per_minute: int
    usage_count: int
    last_used_at: Optional[str]
    is_active: bool
    metadata: dict


class RateLimiter:
    """Token bucket rate limiter for API keys."""

    def __init__(self, rate_per_minute: int):
        self.rate_per_minute = rate_per_minute
        self.tokens = rate_per_minute
        self.last_update = time.time()

    def acquire(self) -> bool:
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.rate_per_minute, self.tokens + elapsed * (self.rate_per_minute / 60))
        self.last_update = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def wait_time(self) -> float:
        if self.tokens >= 1:
            return 0
        return (1 - self.tokens) * (60 / self.rate_per_minute)


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: APIKey):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(api_key.rate_limit_per_minute)
        self.client = httpx.Client(timeout=30.0)

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        pass

    @abstractmethod
    def get_available_models(self) -> list[AIModel]:
        pass

    def close(self):
        self.client.close()


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    BASE_URL = "https://api.anthropic.com/v1"

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "claude-3-haiku-20240307",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded, please wait")

        headers = {
            "x-api-key": self.api_key.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        system_message = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_message:
            payload["system"] = system_message

        try:
            response = self.client.post(
                f"{self.BASE_URL}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            self._increment_usage()
            return {
                "content": result["content"][0]["text"],
                "model": result["model"],
                "usage": result.get("usage", {}),
                "provider": "anthropic",
            }
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise

    def get_available_models(self) -> list[AIModel]:
        return [
            AIModel(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider=ProviderType.ANTHROPIC,
                tier=ModelTier.BASIC,
                context_tokens=200000,
                max_output_tokens=4096,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
            ),
            AIModel(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider=ProviderType.ANTHROPIC,
                tier=ModelTier.STANDARD,
                context_tokens=200000,
                max_output_tokens=4096,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
            ),
            AIModel(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                provider=ProviderType.ANTHROPIC,
                tier=ModelTier.PREMIUM,
                context_tokens=200000,
                max_output_tokens=4096,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
            ),
        ]

    def _increment_usage(self):
        self.api_key.usage_count += 1
        self.api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        _update_api_key_usage(self.api_key.id, self.api_key.usage_count, self.api_key.last_used_at)

    def _handle_error(self, error: httpx.HTTPStatusError):
        if error.response.status_code == 401:
            _deactivate_api_key(self.api_key.id)
        elif error.response.status_code == 429:
            pass


class OpenAIProvider(AIProvider):
    """OpenAI GPT API provider."""

    BASE_URL = "https://api.openai.com/v1"

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "gpt-4o-mini",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded, please wait")

        headers = {
            "authorization": f"Bearer {self.api_key.api_key}",
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = self.client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            self._increment_usage()
            return {
                "content": result["choices"][0]["message"]["content"],
                "model": result["model"],
                "usage": result.get("usage", {}),
                "provider": "openai",
            }
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise

    def get_available_models(self) -> list[AIModel]:
        return [
            AIModel(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                provider=ProviderType.OPENAI,
                tier=ModelTier.BASIC,
                context_tokens=128000,
                max_output_tokens=16384,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
            ),
            AIModel(
                id="gpt-4o",
                name="GPT-4o",
                provider=ProviderType.OPENAI,
                tier=ModelTier.STANDARD,
                context_tokens=128000,
                max_output_tokens=4096,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
            ),
        ]

    def _increment_usage(self):
        self.api_key.usage_count += 1
        self.api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        _update_api_key_usage(self.api_key.id, self.api_key.usage_count, self.api_key.last_used_at)

    def _handle_error(self, error: httpx.HTTPStatusError):
        if error.response.status_code == 401:
            _deactivate_api_key(self.api_key.id)
        elif error.response.status_code == 429:
            pass


class GroqProvider(AIProvider):
    """Groq API provider (fast inference)."""

    BASE_URL = "https://api.groq.com/openai/v1"

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "llama3-8b-8192",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        if not self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded, please wait")

        headers = {
            "authorization": f"Bearer {self.api_key.api_key}",
            "content-type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = self.client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            self._increment_usage()
            return {
                "content": result["choices"][0]["message"]["content"],
                "model": result["model"],
                "usage": result.get("usage", {}),
                "provider": "groq",
            }
        except httpx.HTTPStatusError as e:
            self._handle_error(e)
            raise

    def get_available_models(self) -> list[AIModel]:
        return [
            AIModel(
                id="llama3-8b-8192",
                name="Llama 3 8B",
                provider=ProviderType.GROQ,
                tier=ModelTier.FREE,
                context_tokens=8192,
                max_output_tokens=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            ),
            AIModel(
                id="llama3-70b-8192",
                name="Llama 3 70B",
                provider=ProviderType.GROQ,
                tier=ModelTier.FREE,
                context_tokens=8192,
                max_output_tokens=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            ),
        ]

    def _increment_usage(self):
        self.api_key.usage_count += 1
        self.api_key.last_used_at = datetime.now(timezone.utc).isoformat()
        _update_api_key_usage(self.api_key.id, self.api_key.usage_count, self.api_key.last_used_at)

    def _handle_error(self, error: httpx.HTTPStatusError):
        if error.response.status_code == 401:
            _deactivate_api_key(self.api_key.id)
        elif error.response.status_code == 429:
            pass


class AIProviderManager:
    """Manages multiple AI providers with automatic failover."""

    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self.active_keys: list[APIKey] = []
        self._load_api_keys()

    def _load_api_keys(self):
        self.active_keys = []
        with get_connection() as conn:
            for row in conn.execute("SELECT * FROM api_keys WHERE is_active = 1"):
                key = APIKey(
                    id=row["id"],
                    provider=ProviderType(row["provider"]),
                    key_name=row["key_name"],
                    api_key=row["api_key_encrypted"],
                    rate_limit_per_minute=row["rate_limit_per_minute"],
                    usage_count=row["usage_count"],
                    last_used_at=row["last_used_at"],
                    is_active=bool(row["is_active"]),
                    metadata=json.loads(row["metadata"] or "{}"),
                )
                self.active_keys.append(key)
                self._create_provider(key)

    def _create_provider(self, api_key: APIKey) -> AIProvider:
        provider_classes = {
            ProviderType.ANTHROPIC: AnthropicProvider,
            ProviderType.OPENAI: OpenAIProvider,
            ProviderType.GROQ: GroqProvider,
        }
        provider_class = provider_classes.get(api_key.provider)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {api_key.provider}")
        provider = provider_class(api_key)
        self.providers[api_key.id] = provider
        return provider

    def get_provider(self, preferred_provider: Optional[ProviderType] = None) -> AIProvider:
        if preferred_provider:
            matching = [k for k in self.active_keys if k.provider == preferred_provider]
            if matching:
                return self.providers[matching[0].id]

        if not self.active_keys:
            raise Exception("No active API keys available. Please add API keys first.")

        return self.providers[self.active_keys[0].id]

    async def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        preferred_provider: Optional[ProviderType] = None,
    ) -> dict:
        provider = self.get_provider(preferred_provider)
        available_models = provider.get_available_models()
        target_model = model or available_models[0].id

        try:
            return await provider.chat_completion(
                messages=messages,
                model=target_model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            for key in self.active_keys:
                if key.id != provider.api_key.id:
                    try:
                        alt_provider = self.providers[key.id]
                        return await alt_provider.chat_completion(
                            messages=messages,
                            model=target_model,
                            max_tokens=max_tokens,
                            temperature=temperature,
                        )
                    except Exception:
                        continue
            raise Exception(f"All providers failed. Last error: {str(e)}")

    def add_api_key(
        self,
        provider: ProviderType,
        key_name: str,
        api_key: str,
        rate_limit_per_minute: int = 60,
        metadata: Optional[dict] = None,
    ) -> str:
        key_id = f"key-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO api_keys (id, provider, key_name, api_key_encrypted, rate_limit_per_minute, usage_count, last_used_at, is_active, metadata, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    key_id,
                    provider.value,
                    key_name,
                    api_key,
                    rate_limit_per_minute,
                    0,
                    None,
                    1,
                    json.dumps(metadata or {}),
                    now,
                    now,
                ),
            )
        self._load_api_keys()
        return key_id

    def list_api_keys(self) -> list[dict]:
        with get_connection() as conn:
            keys = []
            for row in conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC"):
                keys.append(
                    {
                        "id": row["id"],
                        "provider": row["provider"],
                        "key_name": row["key_name"],
                        "rate_limit_per_minute": row["rate_limit_per_minute"],
                        "usage_count": row["usage_count"],
                        "last_used_at": row["last_used_at"],
                        "is_active": bool(row["is_active"]),
                        "metadata": json.loads(row["metadata"] or "{}"),
                        "created_at": row["created_at"],
                    }
                )
            return keys

    def deactivate_api_key(self, key_id: str):
        with get_connection() as conn:
            conn.execute("UPDATE api_keys SET is_active = 0, updated_at = ? WHERE id = ?", (_now(), key_id))
        self._load_api_keys()

    def get_available_models(self) -> list[AIModel]:
        models = []
        for provider in self.providers.values():
            models.extend(provider.get_available_models())
        return models


def _update_api_key_usage(key_id: str, usage_count: int, last_used_at: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE api_keys SET usage_count = ?, last_used_at = ?, updated_at = ? WHERE id = ?",
            (usage_count, last_used_at, _now(), key_id),
        )


def _deactivate_api_key(key_id: str):
    with get_connection() as conn:
        conn.execute("UPDATE api_keys SET is_active = 0, updated_at = ? WHERE id = ?", (_now(), key_id))


def _now():
    return datetime.now(timezone.utc).isoformat()


_global_manager: Optional[AIProviderManager] = None


def get_ai_manager() -> AIProviderManager:
    global _global_manager
    if _global_manager is None:
        _global_manager = AIProviderManager()
    return _global_manager
