"""Pruebas de reconstrucción teams.json y estados de ingestión."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from scouting.services.sofascore_teams_rebuild import (  # noqa: E402
    ensure_teams_json,
    teams_from_events,
)


def _sample_events():
    return [
        {
            "id": 1,
            "homeTeam": {"id": 10, "name": "Alpha", "slug": "alpha", "nameCode": "ALP"},
            "awayTeam": {"id": 20, "name": "Beta", "slug": "beta", "nameCode": "BET"},
            "status": {"type": "finished"},
        },
        {
            "id": 2,
            "homeTeam": {"id": 10, "name": "Alpha", "slug": "alpha", "nameCode": "ALP"},
            "awayTeam": {"id": 30, "name": "Gamma", "slug": "gamma", "nameCode": "GAM"},
            "status": {"type": "finished"},
        },
    ]


class TeamsRebuildTests(unittest.TestCase):
    def test_dedupe_by_team_id(self):
        teams = teams_from_events(_sample_events())
        self.assertEqual(len(teams), 3)
        self.assertEqual(teams[10]["name"], "Alpha")
        self.assertEqual(teams[20]["nameCode"], "BET")

    def test_ensure_teams_json_from_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            league_dir = Path(tmp)
            (league_dir / "events.json").write_text(
                json.dumps(_sample_events()), encoding="utf-8"
            )
            (league_dir / "checkpoint_raw.json").write_text("{}", encoding="utf-8")
            ok, reason, n = ensure_teams_json(league_dir)
            self.assertTrue(ok)
            self.assertEqual(n, 3)
            data = json.loads((league_dir / "teams.json").read_text(encoding="utf-8"))
            self.assertIn("10", data)
            self.assertEqual(data["10"]["name"], "Alpha")

    def test_ensure_teams_impossible(self):
        with tempfile.TemporaryDirectory() as tmp:
            league_dir = Path(tmp)
            (league_dir / "events.json").write_text("[]", encoding="utf-8")
            ok, reason, n = ensure_teams_json(league_dir)
            self.assertFalse(ok)
            self.assertEqual(n, 0)
            self.assertIn("No se pudo reconstruir", reason)
            self.assertFalse((league_dir / "teams.json").is_file())


class IngestionStatusSemanticsTests(unittest.TestCase):
    def _load_inc(self):
        if "sofascore_scraper" not in sys.modules:
            scraper = types.ModuleType("sofascore_scraper")
            scraper.compute_event_checksum = lambda e: f"chk-{e.get('id')}"
            scraper.is_event_finished = lambda e: (e.get("status") or {}).get("type") == "finished"
            scraper.event_datetime_utc = lambda e: None
            scraper.DEFAULT_DELAY_DETAILS = 0
            scraper.DEFAULT_DELAY_EVENTS = 0
            scraper.DEFAULT_DELAY_FALLBACK = 0
            scraper.DEFAULT_DELAY_INCIDENTS = 0
            scraper.DEFAULT_DELAY_LINEUP = 0
            scraper.ScraperConfig = object
            scraper.build_driver = lambda **kw: None
            scraper.get_all_events = lambda *a, **k: []
            scraper.init_fetch_context = lambda **kw: None
            scraper.load_checkpoint = lambda *a, **k: {}
            scraper.merge_events_by_id = lambda a, b: b or a
            scraper.process_finished_event = lambda *a, **k: ([], None)
            scraper.remove_event_from_checkpoint = lambda a, b: a
            scraper.append_entries_to_checkpoint = lambda a, b: a
            scraper.save_json = lambda *a, **k: None
            sys.modules["sofascore_scraper"] = scraper

        if "run_all_sofascore_pipeline" not in sys.modules:
            pipe = types.ModuleType("run_all_sofascore_pipeline")

            class LeagueConfig:
                def __init__(self, **kw):
                    self.__dict__.update(kw)

            pipe.LeagueConfig = LeagueConfig
            pipe.LEAGUES = []
            pipe.filter_leagues = lambda x: []
            pipe.import_league = lambda *a, **k: None
            pipe.league_output_dir = lambda root, lg: Path("/tmp")
            pipe.project_root = lambda: ROOT
            pipe.reaggregate_league_from_checkpoint = lambda *a, **k: (True, "ok")
            pipe.stage_league = lambda *a, **k: Path("/tmp")
            pipe.validate_sofascore_output = lambda *a, **k: (True, "ok")
            sys.modules["run_all_sofascore_pipeline"] = pipe

        path = SCRIPTS / "update_sofascore_incremental.py"
        name = "update_sofascore_incremental_teams"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_downloaded_not_redownloaded(self):
        inc = self._load_inc()
        events = [
            {"id": 1, "status": {"type": "finished"}, "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}},
        ]
        known = {1: {"processing_status": "downloaded", "checksum": "chk-1"}}
        candidates, stats = inc.classify_events(events, known, force_event_ids=None, since=None)
        self.assertEqual(candidates, [])
        self.assertEqual(stats.get("already_downloaded"), 1)

    def test_processed_still_skipped(self):
        inc = self._load_inc()
        events = [
            {"id": 1, "status": {"type": "finished"}, "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}},
        ]
        known = {1: {"processing_status": "processed", "checksum": "chk-1"}}
        candidates, stats = inc.classify_events(events, known, force_event_ids=None, since=None)
        self.assertEqual(stats["already_processed"], 1)
        self.assertEqual(candidates, [])

    def test_finalize_calls_ensure_teams_without_selenium(self):
        inc = self._load_inc()

        class League:
            country = "cl"
            division = "primera"
            competition = "Primera División Chile"
            output_slug = "cl_primera_2024"
            tournament_id = 11653
            season_id = 71131
            season = "2024"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            league_dir = root / "web_scraping_sofascore" / "sofascore_output" / "cl_primera_2024"
            league_dir.mkdir(parents=True)
            (league_dir / "checkpoint_raw.json").write_text("{}", encoding="utf-8")
            (league_dir / "events.json").write_text(json.dumps(_sample_events()), encoding="utf-8")
            (league_dir / "player_stats.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (league_dir / "player_stats.json").write_text("[]", encoding="utf-8")

            result = inc.LeagueIncrementalResult(league=League())
            with patch.object(inc, "league_output_dir", return_value=league_dir):
                with patch.object(inc, "reaggregate_league_from_checkpoint", return_value=(True, "ok")):
                    with patch.object(inc, "validate_sofascore_output", return_value=(True, "ok")):
                        with patch.object(inc, "stage_league", return_value=league_dir):
                            with patch.object(inc, "import_league"):
                                with patch.object(inc, "_mark_scope_import_outcome"):
                                    with patch.object(inc, "build_driver") as mock_driver:
                                        out = inc.finalize_league_from_checkpoint(
                                            root,
                                            League(),
                                            "2024",
                                            result,
                                            skip_import=False,
                                            use_replace=True,
                                            backup=False,
                                        )
            mock_driver.assert_not_called()
            self.assertTrue((league_dir / "teams.json").is_file())
            self.assertEqual(out.errors, 0)
            self.assertGreater(out.metrics_imported or 0, 0)

    def test_validation_failure_marks_not_completed(self):
        inc = self._load_inc()

        class League:
            country = "cl"
            division = "primera"
            competition = "Primera División Chile"
            output_slug = "cl_primera_2024"
            tournament_id = 11653
            season_id = 71131
            season = "2024"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            league_dir = root / "web_scraping_sofascore" / "sofascore_output" / "cl_primera_2024"
            league_dir.mkdir(parents=True)
            (league_dir / "checkpoint_raw.json").write_text("{}", encoding="utf-8")
            # sin events → teams impossible
            result = inc.LeagueIncrementalResult(league=League())
            marked = {}

            def fake_mark(league, season_year, *, ok, error_message):
                marked["ok"] = ok
                marked["error"] = error_message

            with patch.object(inc, "league_output_dir", return_value=league_dir):
                with patch.object(inc, "_mark_scope_import_outcome", side_effect=fake_mark):
                    out = inc.finalize_league_from_checkpoint(
                        root,
                        League(),
                        "2024",
                        result,
                        skip_import=False,
                        use_replace=True,
                        backup=False,
                    )
            self.assertGreaterEqual(out.errors, 1)
            self.assertFalse(marked.get("ok", True))
            self.assertIn("teams", (marked.get("error") or "").lower())


class RepairScopeIsolationTests(unittest.TestCase):
    def test_demote_filters_by_competition_season(self):
        from scouting.repositories import sofascore_event_ingestion_repository as repo

        conn = MagicMock()
        cur = MagicMock()
        cur.rowcount = 5
        conn.cursor.return_value.__enter__.return_value = cur

        n = repo.demote_processed_without_import(
            conn,
            country="cl",
            division="primera",
            competition="Primera División Chile",
            season=2024,
            error_message="repair",
        )
        self.assertEqual(n, 5)
        sql = cur.execute.call_args[0][0]
        params = cur.execute.call_args[0][1]
        self.assertIn("competition", sql.lower())
        self.assertIn(2024, params)
        self.assertIn("Primera División Chile", params)


if __name__ == "__main__":
    unittest.main()
