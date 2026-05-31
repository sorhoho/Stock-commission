from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


def create_scheduler(schedule_monthly_payouts_fn, cron_expression: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        schedule_monthly_payouts_fn,
        CronTrigger.from_crontab(cron_expression),
        id="monthly_payout_cycle",
        replace_existing=True,
    )
    return scheduler
