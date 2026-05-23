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
    bounds = settings.random_interval_bounds()
    if bounds is None:
        return f"Cron: {settings.cron_expression}"
    min_seconds, max_seconds = bounds
    return f"随机间隔: {format_interval_seconds(min_seconds)} - {format_interval_seconds(max_seconds)}"


def next_inspection_timestamp(settings: Settings, *, after: float | None = None) -> float:
    bounds = settings.random_interval_bounds()
    if bounds is None:
        return next_cron_timestamp(settings.cron_expression, after=after)
    min_seconds, max_seconds = bounds
    base = time.time() if after is None else after
    return base + random.randint(min_seconds, max_seconds)
