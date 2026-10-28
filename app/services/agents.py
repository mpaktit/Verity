"""Subagent implementations for research, verification, and analysis tasks."""

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.ai_provider import get_ai_manager
from app.services.job_queue import AgentType, JobType
from app.services.web_scraper import get_scraper, Platform
from app.services.browser_automation import get_browser_service


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
    """Agent that discovers leads across platforms using real web scraping."""

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
        self.scraper = get_scraper()

    async def execute(self, payload: dict) -> AgentResult:
        """Research platforms for AI access opportunities using real web scraping."""
        platform = payload.get("platform", "all")
        keywords = payload.get("keywords", ["free trial", "credits", "student", "startup"])
        depth = payload.get("depth", "shallow")

        self.log("info", f"Starting research on platform: {platform}", {"keywords": keywords, "depth": depth})

        try:
            opportunities = []

            # If platform is specified, search that platform
            if platform != "all" and platform in self.PLATFORMS:
                platform_enum = Platform(platform)
                for keyword in keywords:
                    self.log("info", f"Searching {platform} for: {keyword}")
                    results = await self.scraper.search_platform(platform_enum, keyword, limit=5)
                    for result in results:
                        opp = self._convert_to_opportunity(result, platform, keyword)
                        opportunities.append(opp)
                        self.remember("opportunity", json.dumps(opp), {"platform": platform, "keyword": keyword})
            else:
                # Search all platforms
                for plat in self.PLATFORMS[:5]:  # Limit to 5 platforms for efficiency
                    try:
                        platform_enum = Platform(plat)
                        for keyword in keywords[:2]:  # Limit keywords per platform
                            self.log("info", f"Searching {plat} for: {keyword}")
                            results = await self.scraper.search_platform(platform_enum, keyword, limit=3)
                            for result in results:
                                opp = self._convert_to_opportunity(result, plat, keyword)
                                opportunities.append(opp)
                                self.remember("opportunity", json.dumps(opp), {"platform": plat, "keyword": keyword})
                    except Exception as e:
                        self.log("warning", f"Failed to search {plat}: {str(e)}")
                        continue

            # Use AI to analyze and score the opportunities
            if opportunities and depth == "deep":
                opportunities = await self._analyze_with_ai(opportunities)

            self.log("info", f"Research completed, found {len(opportunities)} opportunities")

            return AgentResult(
                success=True,
                data={
                    "platform": platform,
                    "opportunities": opportunities,
                    "total_found": len(opportunities),
                },
                metadata={"search_depth": depth, "keywords_used": keywords},
            )

        except Exception as e:
            self.log("error", f"Research failed: {str(e)}")
            return AgentResult(success=False, data={}, error=str(e))

    def _convert_to_opportunity(self, scraped_content, platform: str, keyword: str) -> dict:
        """Convert scraped content to opportunity format."""
        return {
            "title": scraped_content.title,
            "description": scraped_content.content[:500] if scraped_content.content else "",
            "source_url": scraped_content.url,
            "platform": platform,
            "keyword_matched": keyword,
            "author": scraped_content.author,
            "score": scraped_content.score,
            "published_at": scraped_content.published_at,
            "metadata": scraped_content.metadata,
            "confidence": 50,  # Initial confidence, will be updated by AI analysis
            "verification_needed": True,
        }

    async def _analyze_with_ai(self, opportunities: list[dict]) -> list[dict]:
        """Use AI to analyze and score opportunities."""
        try:
            system_prompt = """You are an analysis agent for AI/SaaS access opportunities.
Analyze the provided opportunities and assign confidence scores (0-100) based on:
- Relevance to AI/SaaS access
- Legitimacy and official status
- Recency
- Detailed information availability

Return only a JSON array with the same structure but updated confidence scores."""

            opportunities_json = json.dumps(opportunities[:10], indent=2)  # Limit to 10 for token efficiency

            user_prompt = f"""Analyze these opportunities and update their confidence scores:
{opportunities_json}

Respond with a JSON array containing the updated opportunities."""

            response = await self.ai_manager.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=4096,
            )

            analyzed = self._parse_opportunities(response["content"])
            if analyzed and len(analyzed) > 0:
                return analyzed
            return opportunities

        except Exception as e:
            self.log("warning", f"AI analysis failed: {str(e)}")
            return opportunities

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
    """Agent that verifies leads using real browser automation."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.browser_service = get_browser_service()

    async def execute(self, payload: dict) -> AgentResult:
        """Verify a specific opportunity using browser automation."""
        opportunity = payload.get("opportunity")
        if not opportunity:
            return AgentResult(success=False, data={}, error="No opportunity provided")

        source_url = opportunity.get("source_url")
        if not source_url:
            return AgentResult(success=False, data={}, error="No source URL provided")

        self.log("info", f"Verifying opportunity: {opportunity.get('title', 'Unknown')} at {source_url}")

        try:
            # Initialize browser if needed
            await self.browser_service.initialize()

            # Verify the URL with browser automation
            verification_result = await self.browser_service.verify_url(
                url=source_url,
                wait_for_selector=None,
                timeout=30000,
                screenshot=True,
            )

            # Check for eligibility indicators
            eligibility_check = await self.browser_service.check_eligibility_page(
                url=source_url,
                keywords=["student", "education", "startup", "free trial", "credits", "beta", "discount"],
            )

            # Analyze with AI for deeper verification
            ai_analysis = await self._analyze_with_ai(
                opportunity,
                verification_result,
                eligibility_check,
            )

            verification = {
                "active": verification_result.success,
                "status_code": verification_result.status_code,
                "title": verification_result.title,
                "eligible": eligibility_check.get("eligible", False),
                "found_keywords": eligibility_check.get("found_keywords", []),
                "legitimacy_score": ai_analysis.get("legitimacy_score", 50),
                "risk_level": ai_analysis.get("risk_level", "medium"),
                "red_flags": ai_analysis.get("red_flags", []),
                "recommended_action": ai_analysis.get("recommended_action", "manual_review"),
                "screenshot_available": verification_result.screenshot is not None,
                "content_preview": verification_result.content[:500] if verification_result.content else None,
                "metadata": verification_result.metadata,
            }

            self.remember("verification", json.dumps(verification), {"source_url": source_url})

            self.log("info", f"Verification completed: {verification.get('recommended_action')}")

            return AgentResult(
                success=True,
                data={
                    "opportunity": opportunity,
                    "verification": verification,
                },
                metadata={"verification_method": "browser_automation"},
            )

        except Exception as e:
            self.log("error", f"Verification failed: {str(e)}")
            return AgentResult(success=False, data={}, error=str(e))

    async def _analyze_with_ai(self, opportunity: dict, verification_result, eligibility_check: dict) -> dict:
        """Use AI to analyze verification results."""
        try:
            system_prompt = """You are a verification agent for AI/SaaS access opportunities.
Analyze the verification results and provide:
1. Legitimacy score (0-100)
2. Risk level (low/medium/high)
3. Red flags (list any concerning elements)
4. Recommended action (apply, monitor, ignore, manual_review)"""

            user_prompt = f"""Analyze this verification:
Opportunity: {opportunity.get('title')}
URL: {opportunity.get('source_url')}
Page accessible: {verification_result.success}
Status code: {verification_result.status_code}
Page title: {verification_result.title}
Eligibility indicators found: {eligibility_check.get('found_keywords', [])}
Content preview: {verification_result.content[:300] if verification_result.content else 'N/A'}

Provide a JSON response with: legitimacy_score, risk_level, red_flags, recommended_action"""

            response = await self.ai_manager.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
            )

            return self._parse_verification(response["content"])

        except Exception as e:
            self.log("warning", f"AI analysis failed: {str(e)}")
            return {
                "legitimacy_score": 50,
                "risk_level": "medium",
                "red_flags": [],
                "recommended_action": "manual_review",
            }

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
