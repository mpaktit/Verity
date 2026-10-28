"""Agent orchestration engine that spawns, monitors, and coordinates subagents."""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.services.agents import AgentFactory, AgentResult
from app.services.job_queue import AgentType, JobQueue, JobType, get_job_queue


class OrchestrationStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class OrchestrationConfig:
    max_concurrent_agents: int = 3
    researcher_interval_seconds: int = 3600
    worker_interval_seconds: int = 300
    analyzer_interval_seconds: int = 7200
    auto_restart_failed: bool = True
    log_level: str = "info"


@dataclass
class AgentInstance:
    agent_id: str
    agent_type: AgentType
    status: str
    current_job_id: Optional[str]
    jobs_completed: int
    jobs_failed: int
    created_at: str
    last_activity_at: str


class AgentOrchestrator:
    """Central orchestration engine for managing subagents."""

    def __init__(self, config: Optional[OrchestrationConfig] = None):
        self.config = config or OrchestrationConfig()
        self.queue = get_job_queue()
        self.agents: dict[str, AgentInstance] = {}
        self.status = OrchestrationStatus.IDLE
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        """Start the orchestration engine."""
        if self.status == OrchestrationStatus.RUNNING:
            return

        self.status = OrchestrationStatus.RUNNING
        self._running = True

        self._tasks = [
            asyncio.create_task(self._researcher_loop()),
            asyncio.create_task(self._worker_loop()),
            asyncio.create_task(self._analyzer_loop()),
            asyncio.create_task(self._monitor_loop()),
        ]

        self._log("info", "Orchestrator started")

    async def stop(self):
        """Stop the orchestration engine."""
        if self.status == OrchestrationStatus.STOPPED:
            return

        self._running = False
        self.status = OrchestrationStatus.STOPPED

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._log("info", "Orchestrator stopped")

    async def pause(self):
        """Pause the orchestration engine."""
        self.status = OrchestrationStatus.PAUSED
        self._log("info", "Orchestrator paused")

    async def resume(self):
        """Resume the orchestration engine."""
        if self.status == OrchestrationStatus.PAUSED:
            self.status = OrchestrationStatus.RUNNING
            self._log("info", "Orchestrator resumed")

    async def _researcher_loop(self):
        """Main loop for researcher agents."""
        while self._running:
            if self.status != OrchestrationStatus.RUNNING:
                await asyncio.sleep(5)
                continue

            try:
                await self._spawn_research_job()
            except Exception as e:
                self._log("error", f"Researcher loop error: {str(e)}")

            await asyncio.sleep(self.config.researcher_interval_seconds)

    async def _worker_loop(self):
        """Main loop for worker agents."""
        while self._running:
            if self.status != OrchestrationStatus.RUNNING:
                await asyncio.sleep(5)
                continue

            try:
                await self._process_worker_jobs()
            except Exception as e:
                self._log("error", f"Worker loop error: {str(e)}")

            await asyncio.sleep(self.config.worker_interval_seconds)

    async def _analyzer_loop(self):
        """Main loop for analyzer agents."""
        while self._running:
            if self.status != OrchestrationStatus.RUNNING:
                await asyncio.sleep(5)
                continue

            try:
                await self._spawn_analysis_job()
            except Exception as e:
                self._log("error", f"Analyzer loop error: {str(e)}")

            await asyncio.sleep(self.config.analyzer_interval_seconds)

    async def _monitor_loop(self):
        """Monitoring loop for agent health."""
        while self._running:
            if self.status != OrchestrationStatus.RUNNING:
                await asyncio.sleep(5)
                continue

            try:
                await self._monitor_agents()
            except Exception as e:
                self._log("error", f"Monitor loop error: {str(e)}")

            await asyncio.sleep(30)

    async def _spawn_research_job(self):
        """Spawn a research job for each platform."""
        platforms = ["twitter", "reddit", "github", "producthunt", "hackernews"]
        keywords = ["free trial", "credits", "student", "startup", "beta access"]

        for platform in platforms:
            job_id = self.queue.enqueue(
                job_type=JobType.RESEARCH,
                agent_type=AgentType.RESEARCHER,
                payload={
                    "platform": platform,
                    "keywords": keywords,
                    "depth": "shallow",
                },
                priority=3,
            )
            self._log("info", f"Enqueued research job for {platform}: {job_id}")

    async def _process_worker_jobs(self):
        """Process pending worker jobs."""
        job = self.queue.dequeue(AgentType.WORKER)
        if not job:
            return

        agent = AgentFactory.create_agent(AgentType.WORKER)
        agent_instance = self._get_or_create_agent_instance(agent.agent_id, AgentType.WORKER)

        self.queue.mark_running(job.id)
        agent_instance.current_job_id = job.id
        agent_instance.last_activity_at = _now()

        try:
            result = await agent.execute(job.payload)
            if result.success:
                self.queue.mark_completed(job.id, result.data)
                agent_instance.jobs_completed += 1
                self._log("info", f"Worker job completed: {job.id}")
            else:
                self.queue.mark_failed(job.id, result.error)
                agent_instance.jobs_failed += 1
                self._log("error", f"Worker job failed: {job.id} - {result.error}")
        except Exception as e:
            self.queue.mark_failed(job.id, str(e))
            agent_instance.jobs_failed += 1
            self._log("error", f"Worker job exception: {job.id} - {str(e)}")
        finally:
            agent_instance.current_job_id = None

    async def _spawn_analysis_job(self):
        """Spawn an analysis job."""
        job_id = self.queue.enqueue(
            job_type=JobType.ANALYZE,
            agent_type=AgentType.ANALYZER,
            payload={
                "type": "opportunities",
                "time_range": "7d",
            },
            priority=2,
        )
        self._log("info", f"Enqueued analysis job: {job_id}")

    async def _monitor_agents(self):
        """Monitor agent health and performance."""
        stats = self.queue.get_stats()
        self._log("info", f"Queue stats: {stats}")

        for agent_id, instance in self.agents.items():
            if instance.status == "running" and instance.current_job_id:
                job = self.queue.get_job(instance.current_job_id)
                if job and job.status.value == "running":
                    elapsed = _elapsed_minutes(instance.last_activity_at)
                    if elapsed > 10:
                        self._log("warning", f"Agent {agent_id} stuck on job {instance.current_job_id} for {elapsed} minutes")

    def _get_or_create_agent_instance(self, agent_id: str, agent_type: AgentType) -> AgentInstance:
        """Get or create an agent instance record."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentInstance(
                agent_id=agent_id,
                agent_type=agent_type,
                status="idle",
                current_job_id=None,
                jobs_completed=0,
                jobs_failed=0,
                created_at=_now(),
                last_activity_at=_now(),
            )
        return self.agents[agent_id]

    def get_status(self) -> dict:
        """Get orchestration status."""
        queue_stats = self.queue.get_stats()
        return {
            "status": self.status.value,
            "config": {
                "max_concurrent_agents": self.config.max_concurrent_agents,
                "researcher_interval": self.config.researcher_interval_seconds,
                "worker_interval": self.config.worker_interval_seconds,
            },
            "queue": queue_stats,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "agent_type": a.agent_type.value,
                    "status": a.status,
                    "current_job": a.current_job_id,
                    "jobs_completed": a.jobs_completed,
                    "jobs_failed": a.jobs_failed,
                }
                for a in self.agents.values()
            ],
        }

    def trigger_research(self, platform: Optional[str] = None):
        """Manually trigger research on a platform."""
        keywords = ["free trial", "credits", "student", "startup"]
        platforms = [platform] if platform else ["twitter", "reddit", "github", "producthunt"]

        for plat in platforms:
            job_id = self.queue.enqueue(
                job_type=JobType.RESEARCH,
                agent_type=AgentType.RESEARCHER,
                payload={
                    "platform": plat,
                    "keywords": keywords,
                    "depth": "deep",
                },
                priority=5,
            )
            self._log("info", f"Manual research triggered for {plat}: {job_id}")

        return {"jobs_created": len(platforms)}

    def _log(self, level: str, message: str):
        """Internal logging."""
        if level == "error" or self.config.log_level == "debug" or (self.config.log_level == "info" and level in ["info", "warning"]):
            print(f"[Orchestrator] {level.upper()}: {message}")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _elapsed_minutes(timestamp: str) -> float:
    """Calculate elapsed minutes since timestamp."""
    try:
        dt = datetime.fromisoformat(timestamp)
        elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
        return elapsed / 60
    except Exception:
        return 0.0


_global_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = AgentOrchestrator()
    return _global_orchestrator
