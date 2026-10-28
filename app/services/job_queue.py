"""SQLite-based job queue for subagent task scheduling and execution."""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from app.db import get_connection


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    RESEARCH = "research"
    VERIFY = "verify"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    MONITOR = "monitor"


class AgentType(Enum):
    RESEARCHER = "researcher"
    WORKER = "worker"
    ANALYZER = "analyzer"
    COORDINATOR = "coordinator"


@dataclass
class Job:
    id: str
    job_type: JobType
    agent_type: AgentType
    payload: dict
    status: JobStatus
    priority: int
    retry_count: int
    max_retries: int
    result: Optional[dict]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


class JobQueue:
    """Manages job queue with priority scheduling and retry logic."""

    def __init__(self):
        self._handlers: dict[JobType, Callable] = {}

    def register_handler(self, job_type: JobType, handler: Callable):
        """Register a handler function for a specific job type."""
        self._handlers[job_type] = handler

    def enqueue(
        self,
        job_type: JobType,
        agent_type: AgentType,
        payload: dict,
        priority: int = 5,
        max_retries: int = 3,
    ) -> str:
        """Add a job to the queue."""
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = _now()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO agent_jobs (id, job_type, agent_type, payload, status, priority, retry_count, max_retries, result, error_message, started_at, completed_at, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    job_type.value,
                    agent_type.value,
                    json.dumps(payload),
                    JobStatus.PENDING.value,
                    priority,
                    0,
                    max_retries,
                    None,
                    None,
                    None,
                    None,
                    now,
                    now,
                ),
            )
        return job_id

    def dequeue(self, agent_type: Optional[AgentType] = None) -> Optional[Job]:
        """Get the next pending job for an agent type (highest priority first)."""
        with get_connection() as conn:
            query = "SELECT * FROM agent_jobs WHERE status = ?"
            params: tuple = (JobStatus.PENDING.value,)
            if agent_type:
                query += " AND agent_type = ?"
                params = (JobStatus.PENDING.value, agent_type.value)
            query += " ORDER BY priority ASC, created_at ASC LIMIT 1"
            row = conn.execute(query, params).fetchone()
            if row:
                return self._row_to_job(row)
        return None

    def mark_running(self, job_id: str):
        """Mark a job as running."""
        now = _now()
        with get_connection() as conn:
            conn.execute(
                "UPDATE agent_jobs SET status = ?, started_at = ?, updated_at = ? WHERE id = ?",
                (JobStatus.RUNNING.value, now, now, job_id),
            )

    def mark_completed(self, job_id: str, result: dict):
        """Mark a job as completed with result."""
        now = _now()
        with get_connection() as conn:
            conn.execute(
                "UPDATE agent_jobs SET status = ?, result = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                (JobStatus.COMPLETED.value, json.dumps(result), now, now, job_id),
            )

    def mark_failed(self, job_id: str, error_message: str, retry: bool = True):
        """Mark a job as failed, optionally retrying."""
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return
            job = self._row_to_job(row)
            now = _now()
            if retry and job.retry_count < job.max_retries:
                conn.execute(
                    "UPDATE agent_jobs SET status = ?, retry_count = retry_count + 1, error_message = ?, updated_at = ? WHERE id = ?",
                    (JobStatus.PENDING.value, error_message, now, job_id),
                )
            else:
                conn.execute(
                    "UPDATE agent_jobs SET status = ?, error_message = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                    (JobStatus.FAILED.value, error_message, now, now, job_id),
                )

    def cancel(self, job_id: str):
        """Cancel a job."""
        now = _now()
        with get_connection() as conn:
            conn.execute(
                "UPDATE agent_jobs SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                (JobStatus.CANCELLED.value, now, now, job_id),
            )

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM agent_jobs WHERE id = ?", (job_id,)).fetchone()
            if row:
                return self._row_to_job(row)
        return None

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        agent_type: Optional[AgentType] = None,
        job_type: Optional[JobType] = None,
        limit: int = 50,
    ) -> list[Job]:
        """List jobs with optional filters."""
        with get_connection() as conn:
            query = "SELECT * FROM agent_jobs WHERE 1=1"
            params: list = []
            if status:
                query += " AND status = ?"
                params.append(status.value)
            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type.value)
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type.value)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            jobs = []
            for row in conn.execute(query, params):
                jobs.append(self._row_to_job(row))
            return jobs

    def get_stats(self) -> dict:
        """Get queue statistics."""
        with get_connection() as conn:
            stats = {}
            for status in JobStatus:
                count = conn.execute("SELECT COUNT(*) FROM agent_jobs WHERE status = ?", (status.value,)).fetchone()[0]
                stats[status.value] = count
            total = conn.execute("SELECT COUNT(*) FROM agent_jobs").fetchone()[0]
            stats["total"] = total
            return stats

    def purge_old_jobs(self, days: int = 7):
        """Remove completed/failed jobs older than specified days."""
        cutoff = (datetime.now(timezone.utc).replace(microsecond=0) - timezone.timedelta(days=days)).isoformat()
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM agent_jobs WHERE status IN (?, ?) AND completed_at < ?",
                (JobStatus.COMPLETED.value, JobStatus.FAILED.value, cutoff),
            )

    def _row_to_job(self, row) -> Job:
        return Job(
            id=row["id"],
            job_type=JobType(row["job_type"]),
            agent_type=AgentType(row["agent_type"]),
            payload=json.loads(row["payload"]),
            status=JobStatus(row["status"]),
            priority=row["priority"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            result=json.loads(row["result"]) if row["result"] else None,
            error_message=row["error_message"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "agent_type": self.agent_type.value,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobExecutor:
    """Executes jobs from the queue using registered handlers."""

    def __init__(self, queue: JobQueue):
        self.queue = queue
        self.running = False

    async def execute_next(self, agent_type: Optional[AgentType] = None) -> Optional[Job]:
        """Execute the next pending job."""
        job = self.queue.dequeue(agent_type)
        if not job:
            return None

        handler = self._handlers.get(job.job_type)
        if not handler:
            self.queue.mark_failed(job.id, f"No handler registered for job type: {job.job_type}")
            return job

        self.queue.mark_running(job.id)
        try:
            result = await handler(job.payload)
            self.queue.mark_completed(job.id, result)
        except Exception as e:
            self.queue.mark_failed(job.id, str(e))
        return job

    async def execute_loop(self, agent_type: Optional[AgentType] = None, max_jobs: int = 10):
        """Execute multiple jobs in a loop."""
        executed = 0
        while executed < max_jobs:
            job = await self.execute_next(agent_type)
            if not job:
                break
            executed += 1
        return executed


def _now():
    return datetime.now(timezone.utc).isoformat()


_global_queue: Optional[JobQueue] = None
_global_executor: Optional[JobExecutor] = None


def get_job_queue() -> JobQueue:
    global _global_queue
    if _global_queue is None:
        _global_queue = JobQueue()
    return _global_queue


def get_job_executor() -> JobExecutor:
    global _global_executor
    if _global_executor is None:
        _global_executor = JobExecutor(get_job_queue())
    return _global_executor
