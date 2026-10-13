import json
import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from scouting.comet_ingest.db_pipeline.audit import Relation, audit_relations, audit_standings, audit_snapshot
from scouting.comet_ingest.db_pipeline.engine import clean_df
from scouting.comet_ingest.db_pipeline.specs import TableSpec
from scouting.comet_ingest.db_pipeline.specs import SPECS


class SnapshotAuditTests(unittest.TestCase):
    def test_counts_missing_rows_and_unique_parents_without_identities(self):
        relation = Relation('events', ('person',), 'people', ('id',))
        frames = {'events': pd.DataFrame({'person': [1, 999888777, 999888777, None]}),
                  'people': pd.DataFrame({'id': [1]})}
        result = audit_relations(frames, [relation])[0]
        self.assertEqual(result['missing_rows'], 2)
        self.assertEqual(result['missing_identities'], 1)
        self.assertEqual(result['null_reference_rows'], 1)
        self.assertNotIn('999888777', json.dumps(result))

    def test_composite_reference_requires_same_competition_and_club(self):
        relation = Relation('matches', ('competition', 'home'), 'entries', ('id', 'club'))
        frames = {'matches': pd.DataFrame({'competition': [1, 2], 'home': [7, 7]}),
                  'entries': pd.DataFrame({'id': [1], 'club': [7]})}
        result = audit_relations(frames, [relation])[0]
        self.assertEqual(result['missing_rows'], 1)

    def test_missing_table_is_unavailable_not_zero(self):
        relation = Relation('events', ('person',), 'people', ('id',))
        result = audit_relations({}, [relation])[0]
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNone(result['missing_rows'])

    def test_missing_column_is_unavailable(self):
        relation = Relation('events', ('person',), 'people', ('id',))
        frames = {'events': pd.DataFrame({'other': []}), 'people': pd.DataFrame({'id': []})}
        self.assertEqual(audit_relations(frames, [relation])[0]['status'], 'unavailable')

    def test_empty_parent_catalog_does_not_skip_references(self):
        relation = Relation('events', ('person',), 'people', ('id',))
        frames = {'events': pd.DataFrame({'person': [1]}), 'people': pd.DataFrame({'id': []})}
        self.assertEqual(audit_relations(frames, [relation])[0]['missing_rows'], 1)

    def test_nullable_composite_matches_postgresql_match_simple(self):
        relation = Relation('events', ('a', 'b'), 'parents', ('a', 'b'))
        frames = {'events': pd.DataFrame({'a': [1], 'b': [None]}), 'parents': pd.DataFrame({'a': [], 'b': []})}
        result = audit_relations(frames, [relation])[0]
        self.assertEqual(result['missing_rows'], 0)
        self.assertEqual(result['null_reference_rows'], 1)

    def test_standings_conflict_is_order_independent_and_source_is_unchanged(self):
        raw = pd.DataFrame({'id': [1, 1], 'season': ['2025', '2025'], 'clubId': [2, 2],
                            'type': ['Tabla oficial', 'Tabla no oficial'], 'points': [3, 6]})
        original = raw.copy(deep=True)
        result = audit_standings(raw, ['points'])
        self.assertEqual(result, audit_standings(raw.iloc[::-1], ['points']))
        self.assertEqual(result['multiple_version_groups'], 1)
        self.assertEqual(result['conflicting_groups'], 1)
        assert_frame_equal(raw, original)

    def test_identical_metrics_do_not_hide_multiple_versions(self):
        raw = pd.DataFrame({'id': [1, 1], 'season': ['2025'] * 2, 'clubId': [2, 2],
                            'type': ['Tabla oficial', 'Tabla no oficial'], 'points': [3, 3]})
        result = audit_standings(raw, ['points'])
        self.assertEqual(result['conflicting_groups'], 0)
        self.assertEqual(result['status'], 'review_required')

    def test_missing_standings_type_is_unavailable(self):
        self.assertEqual(audit_standings(pd.DataFrame(), [])['status'], 'unavailable')

    def test_cleaning_accounts_for_invalid_and_duplicate_rows(self):
        spec = TableSpec(table='sample', cols=['id'], int_cols=['id'], required=['id'], pk=['id'])
        raw = pd.DataFrame({'id': [1, 1, 'invalid', None, 2]})
        result = clean_df(raw, spec)
        self.assertEqual(result.attrs['cleaning'], {'source_rows': 5, 'preclean_removed_rows': 0,
                         'invalid_required_rows': 2, 'deduplicated_rows': 1, 'output_rows': 2})
        self.assertEqual(len(raw), 5)

    def test_partial_snapshot_cannot_pass(self):
        self.assertEqual(audit_snapshot({}, None, [])['status'], 'incomplete')

    def test_empty_snapshot_with_all_columns_cannot_pass(self):
        frames = {name: pd.DataFrame(columns=spec.cols) for name, spec in SPECS.items()}
        standings = pd.DataFrame(columns=['id', 'season', 'clubId', 'type'])
        result = audit_snapshot(frames, standings, [])
        self.assertEqual(result['status'], 'review_required')
        self.assertIn('jugadores', result['empty_core_tables'])
