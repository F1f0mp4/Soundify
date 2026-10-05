"""Scheduler status endpoint."""

from fastapi import APIRouter

from soundify_api.api.deps import SchedulerDep, SettingsDep, SubscriptionServiceDep
from soundify_api.schemas.scheduler import SchedulerStatus, SubscriptionCounts

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("", response_model=SchedulerStatus)
def get_scheduler_status(
    service: SubscriptionServiceDep,
    scheduler: SchedulerDep,
    settings: SettingsDep,
) -> SchedulerStatus:
    """Get scheduler status (read-only)."""
    return SchedulerStatus(
        running=scheduler.is_running,
        enabled=scheduler.enabled,
        cron_expression=scheduler.cron_expression,
        timezone=settings.tz,
        next_run_at=scheduler.next_run_at,
        subscription_counts=SubscriptionCounts(
            total=service.count(),
            enabled=service.count(enabled=True),
        ),
    )
