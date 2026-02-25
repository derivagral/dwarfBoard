import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dwarfboard_etl.pipeline import EventRecord, run_pipeline, transform_events


class PipelineTests(unittest.TestCase):
    def test_transform_events_aggregates_counts_and_unique_users(self) -> None:
        rows = transform_events(
            [
                EventRecord(user_id="u1", timestamp="2026-01-01T10:00:00Z", event_type="view"),
                EventRecord(user_id="u2", timestamp="2026-01-01T11:00:00+00:00", event_type="view"),
                EventRecord(user_id="u1", timestamp="2026-01-01T12:00:00+00:00", event_type="view"),
                EventRecord(user_id="u1", timestamp="2026-01-01T12:30:00+00:00", event_type="signup"),
            ]
        )

        self.assertEqual(
            rows,
            [
                {"event_date": "2026-01-01", "event_type": "signup", "event_count": 1, "unique_users": 1},
                {"event_date": "2026-01-01", "event_type": "view", "event_count": 3, "unique_users": 2},
            ],
        )

    def test_run_pipeline_writes_output_csv(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            events = tmp_path / "events.csv"
            output = tmp_path / "daily_metrics.csv"
            events.write_text(
                "user_id,timestamp,event_type\n"
                "u1,2026-01-01T00:05:00Z,view\n"
                "u2,2026-01-01T00:15:00Z,view\n",
                encoding="utf-8",
            )

            rows = run_pipeline(events, output)

            self.assertEqual(len(rows), 1)
            written = output.read_text(encoding="utf-8")
            self.assertIn("event_date,event_type,event_count,unique_users", written)
            self.assertIn("2026-01-01,view,2,2", written)


if __name__ == "__main__":
    unittest.main()
