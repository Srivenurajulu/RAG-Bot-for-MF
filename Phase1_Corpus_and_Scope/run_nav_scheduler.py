#!/usr/bin/env python3
"""
Run NAV fetch on a schedule (daily after market hours when NAV is published).
Default: 7:30 PM IST (14:00 UTC). Set NAV_SCHEDULE_HOUR and NAV_SCHEDULE_MINUTE (IST) to override.
Run from repo root: python -m Phase1_Corpus_and_Scope.run_nav_scheduler
"""
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Run once at startup, then on schedule
def job():
    try:
        from Phase1_Corpus_and_Scope.fetch_nav import run
        run()
    except Exception as e:
        print(f"NAV fetch failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        print("Install apscheduler: pip install apscheduler", file=sys.stderr)
        sys.exit(1)
    # 7:30 PM IST = 14:00 UTC (IST = UTC+5:30)
    hour = int(os.environ.get("NAV_SCHEDULE_HOUR", 19))
    minute = int(os.environ.get("NAV_SCHEDULE_MINUTE", 30))
    # Always schedule in IST regardless of the machine's local timezone.
    ist = ZoneInfo("Asia/Kolkata")
    scheduler = BlockingScheduler(timezone=ist)
    scheduler.add_job(job, CronTrigger(hour=hour, minute=minute, timezone=ist))
    print(f"NAV scheduler: running fetch now, then daily at {hour:02d}:{minute:02d} IST. Ctrl+C to stop.")
    job()
    scheduler.start()
