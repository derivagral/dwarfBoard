import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dwarfboard_etl.leaderboard import build_leaderboard_rows, run_leaderboard_pipeline


class LeaderboardPipelineTests(unittest.TestCase):
    def test_build_leaderboard_rows_supports_live_payload_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "s1.json").write_text(
                json.dumps(
                    {
                        "seasonId": "s1",
                        "leaderboards": [
                            {
                                "name": "Asharita (Drake)",
                                "build": {
                                    "stance": "Sword",
                                    "equipmentMods": {
                                        "goblet": "Burning Shield: bonus",
                                        "weapon": "Burning Shield: bonus",
                                        "horn": "Burning Shield: bonus",
                                    },
                                },
                                "level": "1160",
                                "raptureLevel": "434",
                                "dungeons": {"Zul": 12, "Bridge of Demigods": 1, "Dark Drythus": 2},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows([tmp_path / "s1.json"], interval_minutes=60)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["account"], "Asharita")
        self.assertEqual(row["character"], "Drake")
        self.assertEqual(row["rupture_level"], 434)
        self.assertEqual(row["build_score"], 1160)
        self.assertEqual(row["stance"], "Sword")
        self.assertEqual(row["skill_name"], "Burning Shield")
        self.assertEqual(row["skill_modifier_count"], 3)
        self.assertTrue(row["first_clear_zul"])
        self.assertTrue(row["first_clear_bridge"])
        self.assertTrue(row["first_clear_dark"])

    def test_build_leaderboard_rows_estimates_seen_time_and_flags(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "s1.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "Asharita",
                                "character": "Drake",
                                "class": "BS",
                                "stance": "Sword",
                                "rupture": 36,
                                "score": 1160,
                                "first_clear_zul": True,
                                "build": {
                                    "equipmentMods": {
                                        "goblet": "Skill A: modifier",
                                        "weapon": "Skill A: modifier",
                                        "horn": "Skill B: modifier",
                                        "belt": "Skill B: modifier",
                                    }
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (tmp_path / "s2.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "Asharita",
                                "character": "Drake",
                                "class": "BS",
                                "stance": "Sword",
                                "rupture": 75,
                                "score": 1200,
                                "first_clear_bridge": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows([tmp_path / "s1.json", tmp_path / "s2.json"], interval_minutes=10)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["seen_minutes_estimate"], 20)
        self.assertEqual(row["snapshots_seen"], 2)
        self.assertAlmostEqual(row["seen_time_per_rupture"], 0.27)
        self.assertEqual(row["skill_name"], "2+")
        self.assertEqual(row["skill_modifier_count"], 2)
        self.assertTrue(row["first_clear_zul"])
        self.assertTrue(row["first_clear_bridge"])
        self.assertTrue(row["cleared_r75"])
        self.assertFalse(row["cleared_r100"])

    def test_run_leaderboard_pipeline_writes_output_csv(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshots_dir = tmp_path / "raw"
            snapshots_dir.mkdir(parents=True)

            (snapshots_dir / "leaderboard_1.json").write_text(
                json.dumps({"entries": [{"account": "A", "character": "C", "rupture": 18, "score": 700}]}),
                encoding="utf-8",
            )
            (snapshots_dir / "leaderboard_1.meta.json").write_text("{}", encoding="utf-8")
            (snapshots_dir / "latest.json").write_text("{}", encoding="utf-8")

            output = tmp_path / "leaderboard.csv"
            rows = run_leaderboard_pipeline(snapshots_dir, output, interval_minutes=60)

            self.assertEqual(len(rows), 1)
            with output.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                csv_rows = list(reader)

            self.assertEqual(len(csv_rows), 1)
            self.assertEqual(csv_rows[0]["account"], "A")
            self.assertEqual(csv_rows[0]["seen_minutes_estimate"], "60")
            self.assertIn("skill_name", csv_rows[0])


if __name__ == "__main__":
    unittest.main()
