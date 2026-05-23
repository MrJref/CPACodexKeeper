import pathlib
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.cron_schedule import CronExpressionError, next_cron_timestamp, normalize_cron_expression
from src.inspection_schedule import next_inspection_timestamp
from src.settings import Settings


class CronScheduleTests(unittest.TestCase):
    def test_next_cron_timestamp_handles_default_every_ten_minutes(self):
        after = datetime(2026, 5, 19, 10, 3, 12).timestamp()

        next_run = next_cron_timestamp("0 0/10 * * * ?", after=after)

        self.assertEqual(datetime.fromtimestamp(next_run), datetime(2026, 5, 19, 10, 10, 0))

    def test_next_cron_timestamp_handles_single_values(self):
        after = datetime(2026, 5, 19, 10, 3, 12).timestamp()

        next_run = next_cron_timestamp("30 4 10 * * ?", after=after)

        self.assertEqual(datetime.fromtimestamp(next_run), datetime(2026, 5, 19, 10, 4, 30))

    def test_normalize_cron_expression_rejects_non_six_field_cron(self):
        with self.assertRaises(CronExpressionError):
            normalize_cron_expression("*/10 * * * *")

    def test_next_inspection_timestamp_uses_random_interval_bounds(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            interval_min_seconds=60,
            interval_max_seconds=120,
        )

        with patch("src.inspection_schedule.random.randint", return_value=90):
            next_run = next_inspection_timestamp(settings, after=1000)

        self.assertEqual(next_run, 1090)


if __name__ == "__main__":
    unittest.main()
