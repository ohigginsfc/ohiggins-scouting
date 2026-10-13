import unittest
import warnings
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from scouting.comet_ingest.db_pipeline.engine import clean_df
from scouting.comet_ingest.db_pipeline.helpers import _normalize_bool_series, fix_unix_timestamptz
from scouting.comet_ingest.db_pipeline.specs import SPECS


class ContractTests(unittest.TestCase):
    def test_cleaner_sets_declared_nullable_dtypes_without_warnings(self):
        raw = pd.DataFrame([{'uid': 1.0, 'id': 2.0, 'clubId': 3.0, 'season': 2025}])
        with warnings.catch_warnings():
            warnings.simplefilter('error', FutureWarning)
            clean = clean_df(raw, SPECS['competidores'])
        self.assertEqual(str(clean.uid.dtype), 'Int64')
        self.assertEqual(str(clean.season.dtype), 'string')

    def test_float_boolean_flags(self):
        actual = _normalize_bool_series(pd.Series([1.0, None, 0.0]))
        self.assertEqual(actual.iloc[0], True)
        self.assertTrue(pd.isna(actual.iloc[1]))
        self.assertEqual(actual.iloc[2], False)

    def test_mixed_epochs_iso_and_duplicate_index(self):
        raw = pd.DataFrame({'time': [1700000000, 1700000000000, '/Date(1700000000000)/', '2023-11-14T22:13:20Z', None]}, index=[0, 0, 1, 2, 3])
        result = fix_unix_timestamptz(raw, 'time')
        self.assertTrue(result.time.iloc[:4].eq(pd.Timestamp('2023-11-14T22:13:20Z')).all())
        self.assertTrue(pd.isna(result.time.iloc[4]))

    def test_negative_millisecond_dates_before_1970(self):
        raw = pd.DataFrame({'time': [-63158400000, '/Date(-63158400000)/', -63158400, 1700000000]})
        result = fix_unix_timestamptz(raw, 'time')
        expected = pd.Timestamp('1968-01-01T00:00:00Z')
        self.assertTrue(result.time.iloc[:3].eq(expected).all())
        # Exercise the exact conversion that failed during live player upload.
        self.assertEqual(result.time.dt.to_pydatetime()[0].year, 1968)
        self.assertEqual(result.time.iloc[3], pd.Timestamp('2023-11-14T22:13:20Z'))

    def test_timezone_name_survives_cleaning(self):
        raw = pd.DataFrame([{'uid': 1, 'id': 2, 'matchId': 3, 'timezoneLocal': 'America/Santiago'}])
        result = clean_df(raw, SPECS['partidos_fases'])
        self.assertEqual(result.timezoneLocal.iloc[0], 'America/Santiago')

    def test_extreme_epochs_do_not_abort_valid_rows(self):
        raw = pd.DataFrame({'time': [1700000000000., 1.7976931348623157e308,
                                   -1.7976931348623157e308, float('inf'),
                                   float('-inf'), 253402300799000., None]})
        with np.errstate(over='raise', invalid='raise'):
            result = fix_unix_timestamptz(raw, 'time')
        self.assertEqual(result.time.iloc[0], pd.Timestamp('2023-11-14T22:13:20Z'))
        self.assertTrue(result.time.iloc[1:].isna().all())
        self.assertEqual(raw.time.iloc[1], 1.7976931348623157e308)

    def test_competidores_natural_key_deduplicates_latest(self):
        raw = pd.DataFrame([{'uid': 1, 'id': 2, 'clubId': 3, 'lastupdateddatetime': 1700000000}, {'uid': 4, 'id': 2, 'clubId': 3, 'lastupdateddatetime': 1800000000}])
        self.assertEqual(clean_df(raw, SPECS['competidores']).uid.tolist(), [4])

