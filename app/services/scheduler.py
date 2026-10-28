"""Advanced job scheduling service using APScheduler."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from app.config import settings


class JobScheduler:
    """Advanced job scheduler for background tasks."""

    def __init__(self):
        jobstores = {
            "default": MemoryJobStore(),
        }
        executors = {
            "default": AsyncIOExecutor(),
        }
        job_defaults = {
            "coalesce": True,
            "max_instances": 3,
            "misfire_grace_time": 300,
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        self._running = False

    def start(self):
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            print("Job scheduler started")

    def shutdown(self):
        """Shutdown the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            print("Job scheduler shutdown")

    def add_interval_job(
        self,
        func: Callable,
        minutes: int = 0,
        seconds: int = 0,
        job_id: Optional[str] = None,
        **kwargs,
    ):
        """Add an interval-based job."""
        trigger = IntervalTrigger(minutes=minutes, seconds=seconds)
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs=kwargs,
        )

    def add_cron_job(
        self,
        func: Callable,
        hour: int,
        minute: int = 0,
        job_id: Optional[str] = None,
        **kwargs,
    ):
        """Add a cron-based job."""
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs=kwargs,
        )

    def remove_job(self, job_id: str):
        """Remove a job by ID."""
        try:
            self.scheduler.remove_job(job_id)
        except Exception as e:
            print(f"Error removing job {job_id}: {e}")

    def get_job(self, job_id: str):
        """Get a job by ID."""
        return self.scheduler.get_job(job_id)

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs()

    def pause_job(self, job_id: str):
        """Pause a job."""
        try:
            self.scheduler.pause_job(job_id)
        except Exception as e:
            print(f"Error pausing job {job_id}: {e}")

    def resume_job(self, job_id: str):
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
        except Exception as e:
            print(f"Error resuming job {job_id}: {e}")


# Global instance
_scheduler: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = JobScheduler()
    return _scheduler
