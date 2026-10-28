"""Subagent implementations for research, verification, and analysis tasks."""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.ai_provider import get_ai_manager
from app.services.job_queue import AgentType, JobType


@dataclass
class AgentResult:
    success: bool
    data: dict
    error: Optional[str] = None
    metadata: Optional[dict] = None


class BaseAgent(ABC):
    """Base class for all subagents."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.ai_manager = get_ai_manager()

    @abstractmethod
    async def execute(self, payload: dict) -> AgentResult:
        """Execute the agent's task."""
        pass

    def log(self, level: str, message: str, context: Optional[dict] = None):
        """Log agent activity."""
        self._write_log(level, message, context)

    def _write_log(self, level: str, message: str, context: Optional[dict] = None):
        from app.db import get_connection
        now = _now()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO agent_logs (id, agent_id, job_id, log_level, message, context, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"log-{uuid.uuid4().hex[:12]}", self.agent_id, None, level, message, json.dumps(context or {}), now),
            )

    def remember(self, memory_type: str, content: str, metadata: Optional[dict] = None):
        """Store information in agent memory."""
        from app.db import get_connection
        now = _now()
        memory_id = f"mem-{uuid.uuid4().hex[:12]}"
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO agent_memory (id, agent_id, memory_type, content, metadata, relevance_score, access_count, last_accessed_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (memory_id, self.agent_id, memory_type, content, json.dumps(metadata or {}), 1.0, 0, None, now, now),
            )

    def recall(self, memory_type: str, limit: int = 10) -> list[dict]:
        """Retrieve memories by type."""
        from app.db import get_connection
        memories = []
        with get_connection() as conn:
            for row in conn.execute(
                """SELECT * FROM agent_memory WHERE agent_id = ? AND memory_type = ? ORDER BY created_at DESC LIMIT ?""",
                (self.agent_id, memory_type, limit),
            ):
                memories.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "metadata": json.loads(row["metadata"] or "{}"),
                        "relevance_score": row["relevance_score"],
                        "created_at": row["created_at"],
                    }
                )
        return memories


class ResearcherAgent(BaseAgent):
    """Agent that discovers leads across platforms."""

    PLATFORMS = [
        "twitter",
        "x",
        "reddit",
        "telegram",
        "discord",
        "linkedin",
        "github",
        "producthunt",
        "hackernews",
        "indiehackers",
    ]

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def execute(self, payload: dict) -> AgentResult:
        """Research platforms for AI access opportunities."""
        platform = payload.get("platform", "all")
        keywords = payload.get("keywords", ["free trial", "credits", "student", "startup"])
        depth = payload.get("depth", "shallow")

        self.log("info", f"Starting research on platform: {platform}", {"keywords": keywords, "depth": depth})

        try:
            system_prompt = """You are a research agent specializing in discovering AI and SaaS access opportunities.
Your task is to identify legitimate public offers such as:
- Free trials with AI model access
- Student or education programs
- Startup credits
- Partner programs
- Limited-time promotions
- Beta access programs

Focus on official, public, and verifiable opportunities. Do not suggest hacks, exploits, or bypass methods."""

            user_prompt = f"""Research the following for AI/SaaS access opportunities:
Platform: {platform}
Keywords: {', '.join(keywords)}
Search depth: {depth}

Provide a structured response with:
1. Platform name
2. Discovered opportunities (title, description, source URL)
3. Eligibility requirements
4. Estimated value/reward
5. Confidence score (0-100)
6. Verification needed (yes/no)"""

            response = await self.ai_manager.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2048,
            )

            opportunities = self._parse_opportunities(response["content"])

            for opp in opportunities:
                self.remember("opportunity", json.dumps(opp), {"platform": platform, "discovered_at": _now()})

            self.log("info", f"Research completed, found {len(opportunities)} opportunities")

            return AgentResult(
                success=True,
                data={
                    "platform": platform,
                    "opportunities": opportunities,
                    "total_found": len(opportunities),
                },
                metadata={"model_used": response["model"], "provider": response["provider"]},
            )

        except Exception as e:
            self.log("error", f"Research failed: {str(e)}")
            return AgentResult(success=False, data={}, error=str(e))

    def _parse_opportunities(self, content: str) -> list[dict]:
        """Parse AI response into structured opportunities."""
        try:
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
            else:
                return [{"raw_response": content, "confidence": 50}]
        except Exception:
            return [{"raw_response": content, "confidence": 30}]


class WorkerAgent(BaseAgent):
    """Agent that verifies leads and checks eligibility."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def execute(self, payload: dict) -> AgentResult:
        """Verify a specific opportunity or lead."""
        opportunity = payload.get("opportunity")
        if not opportunity:
            return AgentResult(success=False, data={}, error="No opportunity provided")

        self.log("info", f"Verifying opportunity: {opportunity.get('title', 'Unknown')}")

        try:
            system_prompt = """You are a verification agent for AI/SaaS access opportunities.
Your task is to:
1. Verify if the opportunity is still active
2. Check eligibility requirements
3. Assess legitimacy and risk
4. Identify any red flags
5. Recommend action (apply, monitor, ignore)"""

            user_prompt = f"""Verify this opportunity:
Title: {opportunity.get('title')}
Description: {opportunity.get('description')}
Source: {opportunity.get('source_url')}
Requirements: {opportunity.get('eligibility', 'Not specified')}

Provide a structured response with:
1. Active status (yes/no/uncertain)
2. Eligibility clarity (clear/ambiguous/unclear)
3. Legitimacy score (0-100)
4. Risk level (low/medium/high)
5. Red flags (list any)
6. Recommended action
7. Additional evidence needed"""

            response = await self.ai_manager.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2048,
            )

            verification = self._parse_verification(response["content"])

            self.remember("verification", json.dumps(verification), {"opportunity_id": opportunity.get("id")})

            self.log("info", f"Verification completed: {verification.get('recommended_action')}")

            return AgentResult(
                success=True,
                data={
                    "opportunity": opportunity,
                    "verification": verification,
                },
                metadata={"model_used": response["model"], "provider": response["provider"]},
            )

        except Exception as e:
            self.log("error", f"Verification failed: {str(e)}")
            return AgentResult(success=False, data={}, error=str(e))

    def _parse_verification(self, content: str) -> dict:
        """Parse AI response into verification data."""
        try:
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
                return json.loads(json_str)
            else:
                return {"raw_response": content, "recommended_action": "manual_review"}
        except Exception:
            return {"raw_response": content, "recommended_action": "manual_review"}


class AnalyzerAgent(BaseAgent):
    """Agent that analyzes trends and patterns."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def execute(self, payload: dict) -> AgentResult:
        """Analyze opportunity patterns and trends."""
        data_type = payload.get("type", "opportunities")
        time_range = payload.get("time_range", "7d")

        self.log("info", f"Analyzing {data_type} over {time_range}")

        try:
            memories = self.recall("opportunity", limit=50)
            verifications = self.recall("verification", limit=50)

            system_prompt = """You are an analysis agent for AI/SaaS access intelligence.
Your task is to identify patterns, trends, and insights from research data."""

            user_prompt = f"""Analyze the following data:
Opportunities discovered: {len(memories)}
Verifications completed: {len(verifications)}

Provide insights on:
1. Most promising platforms
2. Common eligibility patterns
3. Trending offer types
4. Success rate of verifications
5. Recommendations for research focus"""

            response = await self.ai_manager.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=2048,
            )

            insights = {"analysis": response["content"], "data_points": len(memories) + len(verifications)}

            self.remember("analysis", json.dumps(insights), {"time_range": time_range})

            self.log("info", "Analysis completed")

            return AgentResult(
                success=True,
                data=insights,
                metadata={"model_used": response["model"], "provider": response["provider"]},
            )

        except Exception as e:
            self.log("error", f"Analysis failed: {str(e)}")
            return AgentResult(success=False, data={}, error=str(e))


class AgentFactory:
    """Factory for creating agent instances."""

    @staticmethod
    def create_agent(agent_type: AgentType) -> BaseAgent:
        agent_id = f"agent-{agent_type.value}-{uuid.uuid4().hex[:8]}"
        if agent_type == AgentType.RESEARCHER:
            return ResearcherAgent(agent_id)
        elif agent_type == AgentType.WORKER:
            return WorkerAgent(agent_id)
        elif agent_type == AgentType.ANALYZER:
            return AnalyzerAgent(agent_id)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")


def _now():
    return datetime.now(timezone.utc).isoformat()
