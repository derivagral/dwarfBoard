import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from dwarfboard_etl.leaderboard import build_leaderboard_rows, reconcile_variant_transitions, run_leaderboard_pipeline


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
                                "zone": "Dark Drythus",
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
        self.assertTrue(row["first_clear_dark_drythus"])
        self.assertFalse(row["first_clear_dark_bridge"])
        self.assertFalse(row["first_clear_dark_olympus"])
        self.assertEqual(row["zone"], "Dark Drythus")

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


    def test_reconcile_variant_transitions_moves_solo_to_fellowship(self) -> None:
        solo_rows = [
            {"account": "A", "character": "C", "rupture_level": 50},
            {"account": "B", "character": "D", "rupture_level": 30},
        ]
        fellowship_rows = [
            {"account": "A", "character": "C", "rupture_level": 75},
        ]
        variant_rows = {
            "solo": solo_rows,
            "fellowship": fellowship_rows,
            "hardcore_solo": [],
            "hardcore_fellowship": [],
        }

        result = reconcile_variant_transitions(variant_rows)

        # Player A/C should be removed from solo (promoted to fellowship)
        solo_accounts = [(r["account"], r["character"]) for r in result["solo"]]
        self.assertNotIn(("A", "C"), solo_accounts)
        self.assertIn(("B", "D"), solo_accounts)

        # Fellowship should keep A/C with variant_history showing both
        self.assertEqual(len(result["fellowship"]), 1)
        self.assertEqual(result["fellowship"][0]["variant_history"], ["fellowship", "solo"])

        # Solo-only player B/D should have solo-only history
        self.assertEqual(result["solo"][0]["variant_history"], ["solo"])


if __name__ == "__main__":
    unittest.main()
