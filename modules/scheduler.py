"""APScheduler 자동 실행 스케줄러 (FR-04)"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler = AsyncIOScheduler()
_job_id = "daily_briefing"


def start(run_briefing_fn, schedule_time: str):
    """스케줄러를 시작하고 일일 브리핑 작업을 등록."""
    hour, minute = schedule_time.split(":")
    if _scheduler.running:
        _scheduler.remove_all_jobs()
    _scheduler.add_job(
        run_briefing_fn,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
        id=_job_id,
        replace_existing=True,
    )
    if not _scheduler.running:
        _scheduler.start()
    print(f"[scheduler] 매일 {schedule_time} 자동 실행 등록 완료")


def update_schedule(run_briefing_fn, schedule_time: str):
    """설정 변경 시 스케줄 즉시 반영."""
    hour, minute = schedule_time.split(":")
    _scheduler.reschedule_job(
        _job_id,
        trigger=CronTrigger(hour=int(hour), minute=int(minute)),
    )
    print(f"[scheduler] 스케줄 변경 → {schedule_time}")


def get_next_run() -> str | None:
    job = _scheduler.get_job(_job_id)
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M")
    return None
