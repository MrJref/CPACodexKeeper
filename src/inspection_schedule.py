import random
import time

from .cron_schedule import next_cron_timestamp
from .settings import Settings


def format_interval_seconds(seconds: int) -> str:
    if seconds % 86400 == 0:
        return f"{seconds // 86400}天"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}小时"
    if seconds % 60 == 0:
        return f"{seconds // 60}分钟"
    return f"{seconds}秒"


def schedule_description(settings: Settings) -> str:
    bounds = settings.cron_offset_bounds()
    if bounds is None:
        return f"Cron: {settings.cron_expression}"
    left_seconds, right_seconds = bounds
    return (
        f"Cron: {settings.cron_expression}, "
        f"随机偏移窗口: -{format_interval_seconds(left_seconds)} / +{format_interval_seconds(right_seconds)}"
    )


def next_inspection_timestamp(settings: Settings, *, after: float | None = None) -> float:
    bounds = settings.cron_offset_bounds()
    if bounds is None:
        return next_cron_timestamp(settings.cron_expression, after=after)
    left_seconds, right_seconds = bounds
    base = time.time() if after is None else after
    cron_after = base - right_seconds - 1

    while True:
        cron_run_at = next_cron_timestamp(settings.cron_expression, after=cron_after)
        minimum_offset = max(-left_seconds, int(base - cron_run_at) + 1)
        if minimum_offset <= right_seconds:
            return cron_run_at + random.randint(minimum_offset, right_seconds)
        cron_after = cron_run_at
