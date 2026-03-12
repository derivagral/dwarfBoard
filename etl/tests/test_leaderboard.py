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
        self.assertEqual(row["stance"], "sword")
        self.assertEqual(row["skill_name"], "Burning Shield")
        self.assertEqual(row["skill_modifier_count"], 3)
        self.assertEqual(row["zone"], "Dark Drythus")
        # All 3 dungeons from the API should be tracked dynamically
        self.assertEqual(row["dungeons"]["zul"], 12)
        self.assertEqual(row["dungeons"]["bridge of demigods"], 1)
        self.assertEqual(row["dungeons"]["dark drythus"], 2)
        self.assertEqual(len(row["dungeons"]), 3)

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
                                "dungeons": {"Zul": 5},
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
                                "dungeons": {"Zul": 10, "Bridge of Demigods": 3},
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
        # Dungeons should be merged: max count across snapshots
        self.assertEqual(row["dungeons"]["zul"], 10)
        self.assertEqual(row["dungeons"]["bridge of demigods"], 3)
        self.assertTrue(row["cleared_r75"])
        self.assertFalse(row["cleared_r100"])

    def test_build_leaderboard_rows_handles_legacy_first_clear_flags(self) -> None:
        """Legacy first_clear_* flat booleans should be converted to dungeons entries."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "s1.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "A",
                                "character": "C",
                                "rupture": 50,
                                "score": 800,
                                "first_clear_zul": True,
                                "first_clear_bridge": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows([tmp_path / "s1.json"], interval_minutes=60)

        row = rows[0]
        self.assertEqual(row["dungeons"]["zul"], 1)
        self.assertEqual(row["dungeons"]["bridge"], 1)

    def test_build_leaderboard_rows_tracks_all_dungeons(self) -> None:
        """All 18 dungeon types from the API should be tracked."""
        all_dungeons = {
            "The Ancient Catacombs": 1219,
            "Grave Digger": 639,
            "Elysia": 3401,
            "Harmon Olympus": 1,
            "Bridge of Demigods": 60,
            "Archeon": 13,
            "The Elven Capital": 14650,
            "Echoes of Eternity": 21,
            "Zul": 6508,
            "Skorch": 2100,
            "Dark Drythus": 14,
            "Dark Olympus": 7,
            "Dark Bridge": 27,
            "Dark Archeon": 21,
            "Dark Zul": 21,
            "Dark Skorch": 406,
            "Underground Enclave": 4960,
            "The Hour Glass": 2,
        }
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "s1.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "BigPlayer",
                                "character": "Main",
                                "rupture": 200,
                                "score": 1100,
                                "dungeons": all_dungeons,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows([tmp_path / "s1.json"], interval_minutes=60)

        row = rows[0]
        self.assertEqual(len(row["dungeons"]), 18)
        self.assertEqual(row["dungeons"]["the elven capital"], 14650)
        self.assertEqual(row["dungeons"]["dark skorch"], 406)
        self.assertEqual(row["dungeons"]["the hour glass"], 2)

    def test_dungeons_ordered_by_first_seen(self) -> None:
        """Dungeon output should be sorted by first-seen snapshot timestamp."""
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "leaderboard_20260301T100000Z_aaa.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "A",
                                "character": "C",
                                "rupture": 50,
                                "score": 800,
                                "dungeons": {"Zul": 5},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (tmp_path / "leaderboard_20260302T100000Z_bbb.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "account": "A",
                                "character": "C",
                                "rupture": 60,
                                "score": 850,
                                "dungeons": {"Zul": 10, "Skorch": 3},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows(
                [
                    tmp_path / "leaderboard_20260301T100000Z_aaa.json",
                    tmp_path / "leaderboard_20260302T100000Z_bbb.json",
                ],
                interval_minutes=10,
            )

        row = rows[0]
        # Zul seen first, Skorch second
        dungeon_keys = list(row["dungeons"].keys())
        self.assertEqual(dungeon_keys, ["zul", "skorch"])
        self.assertEqual(row["dungeon_first_seen"]["zul"], "20260301T100000Z")
        self.assertEqual(row["dungeon_first_seen"]["skorch"], "20260302T100000Z")


    def test_build_leaderboard_rows_normalizes_stance_buckets(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "s1.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {"account": "A", "character": "Bow", "stance": "Bow", "rupture": 1, "score": 1},
                            {"account": "B", "character": "Wand", "stance": "wand", "rupture": 1, "score": 1},
                            {"account": "C", "character": "Maul", "stance": "Polearm", "rupture": 1, "score": 1},
                            {"account": "D", "character": "Spear", "stance": "Spear", "rupture": 1, "score": 1},
                            {"account": "E", "character": "Sword", "stance": "Dual", "rupture": 1, "score": 1},
                            {"account": "F", "character": "Axe", "stance": "2h", "rupture": 1, "score": 1},
                            {"account": "G", "character": "Fists", "stance": "Common", "rupture": 1, "score": 1},
                            {"account": "H", "character": "Scythe", "stance": "Scythe", "rupture": 1, "score": 1},
                            {"account": "I", "character": "Unknown", "stance": "Laser", "rupture": 1, "score": 1},
                            {"account": "J", "character": "Magic", "stance": "Magic", "rupture": 1, "score": 1},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            rows = build_leaderboard_rows([tmp_path / "s1.json"], interval_minutes=60)

        stance_by_char = {row["character"]: row["stance"] for row in rows}
        self.assertEqual(stance_by_char["Bow"], "bow")
        self.assertEqual(stance_by_char["Wand"], "magery")
        self.assertEqual(stance_by_char["Maul"], "maul")
        self.assertEqual(stance_by_char["Spear"], "spear")
        self.assertEqual(stance_by_char["Sword"], "sword")
        self.assertEqual(stance_by_char["Axe"], "axe")
        self.assertEqual(stance_by_char["Fists"], "fists")
        self.assertEqual(stance_by_char["Scythe"], "scythe")
        self.assertEqual(stance_by_char["Unknown"], "unknown")
        self.assertEqual(stance_by_char["Magic"], "magery")

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
            self.assertIn("dungeons", csv_rows[0])
            self.assertIn("dungeon_first_seen", csv_rows[0])

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
