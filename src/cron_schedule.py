import time as time_module
from dataclasses import dataclass
from datetime import datetime, time, timedelta


class CronExpressionError(ValueError):
    pass


@dataclass(frozen=True)
class CronSchedule:
    expression: str
    seconds: set[int]
    minutes: set[int]
    hours: set[int]
    days: set[int]
    months: set[int]
    weekdays: set[int]
    day_is_any: bool
    weekday_is_any: bool


def normalize_cron_expression(expression: str) -> str:
    normalized = " ".join((expression or "").strip().split())
    parse_cron_expression(normalized)
    return normalized


def next_cron_timestamp(expression: str, *, after: float | None = None) -> float:
    schedule = parse_cron_expression(expression)
    start = datetime.fromtimestamp(time_module.time() if after is None else after).replace(microsecond=0) + timedelta(seconds=1)
    start_date = start.date()

    for day_offset in range(366 * 5):
        date = start_date + timedelta(days=day_offset)
        if not _date_matches(schedule, date):
            continue
        for hour in sorted(schedule.hours):
            for minute in sorted(schedule.minutes):
                for second in sorted(schedule.seconds):
                    candidate = datetime.combine(date, time(hour, minute, second))
                    if candidate >= start:
                        return candidate.timestamp()
    raise CronExpressionError("cron expression has no matching time in the next 5 years")


def parse_cron_expression(expression: str) -> CronSchedule:
    parts = (expression or "").strip().split()
    if len(parts) != 6:
        raise CronExpressionError("cron expression must contain 6 fields: second minute hour day month weekday")

    seconds, _ = _parse_field(parts[0], 0, 59, "second")
    minutes, _ = _parse_field(parts[1], 0, 59, "minute")
    hours, _ = _parse_field(parts[2], 0, 23, "hour")
    days, day_is_any = _parse_field(parts[3], 1, 31, "day", allow_question=True)
    months, _ = _parse_field(parts[4], 1, 12, "month")
    weekdays, weekday_is_any = _parse_field(parts[5], 0, 7, "weekday", allow_question=True)

    return CronSchedule(
        expression=" ".join(parts),
        seconds=seconds,
        minutes=minutes,
        hours=hours,
        days=days,
        months=months,
        weekdays=weekdays,
        day_is_any=day_is_any,
        weekday_is_any=weekday_is_any,
    )


def _parse_field(
    value: str,
    minimum: int,
    maximum: int,
    name: str,
    *,
    allow_question: bool = False,
) -> tuple[set[int], bool]:
    if not value:
        raise CronExpressionError(f"{name} field is empty")
    if value == "?":
        if not allow_question:
            raise CronExpressionError(f"{name} field does not allow '?'")
        return set(range(minimum, maximum + 1)), True

    result: set[int] = set()
    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            raise CronExpressionError(f"{name} field contains an empty item")
        result.update(_parse_token(token, minimum, maximum, name, allow_question=allow_question))

    if not result:
        raise CronExpressionError(f"{name} field has no values")
    return result, False


def _parse_token(token: str, minimum: int, maximum: int, name: str, *, allow_question: bool) -> set[int]:
    if "/" in token:
        base, raw_step = token.split("/", 1)
        try:
            step = int(raw_step)
        except ValueError as exc:
            raise CronExpressionError(f"{name} step must be an integer") from exc
        if step <= 0:
            raise CronExpressionError(f"{name} step must be positive")
        start, end = _parse_range_base(base, minimum, maximum, name, allow_question=allow_question, single_as_range=True)
        return set(range(start, end + 1, step))

    start, end = _parse_range_base(token, minimum, maximum, name, allow_question=allow_question, single_as_range=False)
    return set(range(start, end + 1))


def _parse_range_base(
    token: str,
    minimum: int,
    maximum: int,
    name: str,
    *,
    allow_question: bool,
    single_as_range: bool,
) -> tuple[int, int]:
    if token == "*":
        return minimum, maximum
    if token == "?":
        if not allow_question:
            raise CronExpressionError(f"{name} field does not allow '?'")
        return minimum, maximum
    if "-" in token:
        raw_start, raw_end = token.split("-", 1)
        start = _parse_number(raw_start, minimum, maximum, name)
        end = _parse_number(raw_end, minimum, maximum, name)
        if start > end:
            raise CronExpressionError(f"{name} range start must be <= end")
        return start, end

    start = _parse_number(token, minimum, maximum, name)
    return start, maximum if single_as_range else start


def _parse_number(value: str, minimum: int, maximum: int, name: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise CronExpressionError(f"{name} value must be an integer") from exc
    if number < minimum or number > maximum:
        raise CronExpressionError(f"{name} value must be between {minimum} and {maximum}")
    return number


def _date_matches(schedule: CronSchedule, date) -> bool:
    if date.month not in schedule.months or date.day not in schedule.days:
        return False
    if schedule.weekday_is_any:
        return True
    # Accept common cron weekday numbering: 0/7 = Sunday, 1 = Monday, ... 6 = Saturday.
    cron_weekday = (date.weekday() + 1) % 7
    return cron_weekday in schedule.weekdays or (cron_weekday == 0 and 7 in schedule.weekdays)
