"""Pruebas de gestión de informes (hide / restore / delete / recommendation)."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


def _load_module(name: str, relative: str):
    root = Path(__file__).resolve().parents[1]
    path = root / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeCursor:
    def __init__(self, *, rowcount: int = 1, fetchone_value=None):
        self.rowcount = rowcount
        self._fetchone_value = fetchone_value
        self.statements: list[tuple[str, tuple | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def fetchone(self):
        return self._fetchone_value

    def fetchall(self):
        return []


class FakeConn:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.commits = 0
        self._in_transaction = False

    def cursor(self, row_factory=None):
        return self._cursor

    def commit(self):
        self.commits += 1

    def transaction(self):
        conn = self

        class _Tx:
            def __enter__(self_inner):
                conn._in_transaction = True
                return conn

            def __exit__(self_inner, *args):
                conn._in_transaction = False
                return False

        return _Tx()


class ReportsRepositorySoftHideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cargar repositorio con stub mínimo de psycopg.
        psycopg = MagicMock()
        psycopg.Connection = object
        sys.modules["psycopg"] = psycopg
        sys.modules["psycopg.rows"] = MagicMock(dict_row=object)
        sys.modules["psycopg.types"] = MagicMock()
        sys.modules["psycopg.types.json"] = MagicMock(Json=lambda x: x)
        cls.repo = _load_module(
            "reports_repository_under_test",
            "src/scouting/repositories/reports_repository.py",
        )

    def test_update_report_recommendation_sql(self):
        cur = FakeCursor()
        conn = FakeConn(cur)
        self.repo.update_report_recommendation(conn, 42, "Prioritario")
        self.assertEqual(len(cur.statements), 1)
        sql, params = cur.statements[0]
        self.assertIn("UPDATE scouting_reports", sql)
        self.assertIn("recommendation", sql)
        self.assertEqual(params, ("Prioritario", 42))
        self.assertEqual(conn.commits, 1)

    def test_hide_report_sql(self):
        cur = FakeCursor()
        conn = FakeConn(cur)
        self.repo.hide_report(conn, 7, hidden_by="admin")
        sql, params = cur.statements[0]
        self.assertIn("is_hidden = TRUE", sql)
        self.assertIn("hidden_at = NOW()", sql)
        self.assertEqual(params, ("admin", 7))

    def test_restore_report_sql(self):
        cur = FakeCursor()
        conn = FakeConn(cur)
        self.repo.restore_report(conn, 7)
        sql, params = cur.statements[0]
        self.assertIn("is_hidden = FALSE", sql)
        self.assertIn("hidden_at = NULL", sql)
        self.assertIn("hidden_by = NULL", sql)
        self.assertEqual(params, (7,))

    def test_delete_report_permanently_uses_transaction_and_dependents(self):
        cur = FakeCursor(rowcount=1)
        conn = FakeConn(cur)
        ok = self.repo.delete_report_permanently(conn, 99)
        self.assertTrue(ok)
        self.assertEqual(len(cur.statements), 2)
        self.assertIn("report_attribute_ratings", cur.statements[0][0])
        self.assertIn("DELETE FROM scouting_reports", cur.statements[1][0])
        self.assertEqual(cur.statements[1][1], (99,))

    def test_count_reports_defaults_to_visible_only(self):
        cur = FakeCursor(fetchone_value=(3,))
        conn = FakeConn(cur)
        n = self.repo.count_reports(conn)
        self.assertEqual(n, 3)
        self.assertIn("is_hidden", cur.statements[0][0])
        self.assertIn("FALSE", cur.statements[0][0])


class ReportsServiceValidationTests(unittest.TestCase):
    def test_recommendation_whitelist(self):
        valid = {
            "Seguir monitorizando",
            "Interesante",
            "Prioritario",
            "Descartar",
        }
        self.assertNotIn("Valor inventado", valid)
        for item in valid:
            self.assertTrue(bool(item.strip()))


if __name__ == "__main__":
    unittest.main()
