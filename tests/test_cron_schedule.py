import pathlib
import sys
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.cron_schedule import CronExpressionError, next_cron_timestamp, normalize_cron_expression
from src.inspection_schedule import next_inspection_timestamp, schedule_description
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

    def test_next_inspection_timestamp_uses_cron_offset_window(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            cron_expression="0 0 0/4 * * ?",
            interval_min_seconds=60,
            interval_max_seconds=120,
        )
        after = datetime(2026, 5, 19, 10, 0, 0).timestamp()

        with patch("src.inspection_schedule.random.randint", return_value=-30):
            next_run = next_inspection_timestamp(settings, after=after)

        self.assertEqual(datetime.fromtimestamp(next_run), datetime(2026, 5, 19, 11, 59, 30))

    def test_next_inspection_timestamp_clamps_offset_window_to_future(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            cron_expression="0 0 0/4 * * ?",
            interval_min_seconds=8 * 60,
            interval_max_seconds=2 * 60,
        )
        after = datetime(2026, 5, 19, 11, 59, 30).timestamp()

        with patch("src.inspection_schedule.random.randint", return_value=-29) as randint_mock:
            next_run = next_inspection_timestamp(settings, after=after)

        randint_mock.assert_called_once_with(-29, 120)
        self.assertEqual(datetime.fromtimestamp(next_run), datetime(2026, 5, 19, 11, 59, 31))

    def test_schedule_description_describes_cron_offset_window(self):
        settings = Settings(
            cpa_endpoint="https://example.com",
            cpa_token="secret",
            cron_expression="0 0 0/4 * * ?",
            interval_min_seconds=8 * 60,
            interval_max_seconds=2 * 60,
        )

        self.assertEqual(schedule_description(settings), "Cron: 0 0 0/4 * * ?, 随机偏移窗口: -8分钟 / +2分钟")


if __name__ == "__main__":
    unittest.main()
