import pathlib
import sys
import unittest
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.cron_schedule import CronExpressionError, next_cron_timestamp, normalize_cron_expression


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


if __name__ == "__main__":
    unittest.main()
