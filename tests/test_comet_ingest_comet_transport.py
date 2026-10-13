import base64
import json
import os
import traceback
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import pandas as pd
import requests
from scouting.comet_ingest.api import CometAPI, Endpoint, safe_slug


def response(payload=None, status=200, headers=None):
    result = Mock(status_code=status, headers=headers or {})
    result.json.return_value = payload
    return result


class CometTests(unittest.TestCase):
    def test_pacing_is_shared_between_reports_and_pages(self):
        api = CometAPI(verbose=False, page_size=1, sleep_between_pages=3)
        with patch('scouting.comet_ingest.api.requests.get', side_effect=[response([{'id': 1}]), response([]), response([])]), patch('scouting.comet_ingest.api.time.sleep') as sleep:
            api.fetch_report('synthetic-one')
            api.fetch_report('synthetic-two')
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [3, 3])

    def test_429_without_header_uses_long_bounded_backoff(self):
        api = self.api()
        self.assertEqual([api._retry_delay(response(status=429), i) for i in range(6)],
                         [30, 60, 120, 120, 120, 120])
        for value in ('NaN', 'inf', '-1', 'invalid'):
            self.assertEqual(api._retry_delay(response(status=429, headers={'Retry-After': value}), 0), 30)

    def api(self, **kwargs):
        return CometAPI(verbose=False, sleep_between_pages=0, **kwargs)


    def test_supported_payloads(self):
        for payload in ([{"id": 1}], {"results": [{"id": 1}]},
                        {"results": {"items": [{"id": 1}]}}, {"items": [{"id": 1}]}):
            with self.subTest(payload=payload), patch('scouting.comet_ingest.api.requests.get', return_value=response(payload)):
                frame = self.api().fetch_report('synthetic')
                self.assertEqual(frame.id.tolist(), [1])


    def test_valid_empty(self):
        with patch('scouting.comet_ingest.api.requests.get', return_value=response([])):
            self.assertTrue(self.api().fetch_report('synthetic').empty)


    def test_invalid_contract_never_becomes_empty(self):
        for payload in ({"error": "private"}, {"results": {}}, None, [1], [{}], {"results": None}):
            with self.subTest(payload=payload), patch('scouting.comet_ingest.api.requests.get', return_value=response(payload)):
                with self.assertRaisesRegex(RuntimeError, 'contrato'):
                    self.api().fetch_report('synthetic')


    def test_pagination(self):
        with patch('scouting.comet_ingest.api.requests.get', side_effect=[response([{"id": 1}, {"id": 2}]), response([{"id": 3}])]) as get:
            self.assertEqual(self.api(page_size=2).fetch_report('synthetic').id.tolist(), [1, 2, 3])
            self.assertIn('/1/2/', get.call_args.args[0])


    def test_page_limit_fails(self):
        with patch('scouting.comet_ingest.api.requests.get', return_value=response([{"id": 1}])):
            with self.assertRaisesRegex(RuntimeError, 'incompleta'):
                self.api(page_size=1, max_pages=1).fetch_report('synthetic')


    def test_exact_multiple_requires_empty_page(self):
        with patch('scouting.comet_ingest.api.requests.get', side_effect=[response([{"id": 1}]), response([])]):
            self.assertEqual(len(self.api(page_size=1, max_pages=2).fetch_report('synthetic')), 1)


    def test_429_respects_retry_after(self):
        with patch('scouting.comet_ingest.api.requests.get', side_effect=[response(status=429, headers={'Retry-After': '9'}), response([{'id': 1}])]) as get, patch('scouting.comet_ingest.api.time.sleep') as sleep:
            self.assertEqual(len(self.api().fetch_report('synthetic')), 1)
            self.assertEqual(get.call_count, 2)
            sleep.assert_called_once_with(9)


    def test_retry_after_date(self):
        header = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30))
        delay = self.api()._retry_delay(response(headers={'Retry-After': header}), 0)
        self.assertTrue(28 <= delay <= 30)


    def test_retry_after_over_budget_does_not_retry_early(self):
        with patch('scouting.comet_ingest.api.requests.get', return_value=response(status=429, headers={'Retry-After': '999'})) as get, patch('scouting.comet_ingest.api.time.sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'espera'):
                self.api().fetch_report('synthetic')
            self.assertEqual(get.call_count, 1)
            sleep.assert_not_called()


    def test_transient_failures_have_bounded_attempts(self):
        for status in (429, 500, 502, 503, 504):
            with self.subTest(status=status), patch('scouting.comet_ingest.api.requests.get', return_value=response(status=status)) as get, patch('scouting.comet_ingest.api.time.sleep'):
                with self.assertRaisesRegex(RuntimeError, 'agotados'):
                    self.api(max_retries=2).fetch_report('synthetic')
                self.assertEqual(get.call_count, 3)


    def test_authentication_failure_is_not_retried(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status), patch('scouting.comet_ingest.api.requests.get', return_value=response(status=status)) as get:
                with self.assertRaisesRegex(RuntimeError, f'HTTP {status}'):
                    self.api().fetch_report('synthetic')
                self.assertEqual(get.call_count, 1)


    def test_connection_failure_traceback_contains_no_secret(self):
        key = 'PRIVATE_VALUE'
        with patch('scouting.comet_ingest.api.requests.get', side_effect=requests.ConnectionError('API_KEY=PRIVATE_VALUE')), patch('scouting.comet_ingest.api.time.sleep'):
            try:
                self.api(max_retries=1).fetch_report(key)
            except RuntimeError:
                self.assertNotIn('PRIVATE_VALUE', traceback.format_exc())
            else:
                self.fail('Expected failure')


    def test_invalid_json_hides_response(self):
        key = 'PRIVATE_VALUE'
        bad = response()
        bad.json.side_effect = ValueError('PRIVATE_VALUE')
        with patch('scouting.comet_ingest.api.requests.get', return_value=bad):
            try:
                self.api().fetch_report(key)
            except RuntimeError:
                self.assertNotIn('PRIVATE_VALUE', traceback.format_exc())
            else:
                self.fail('Expected failure')


    def test_invalid_limits(self):
        for values in ({'max_pages': 0}, {'page_size': -1}, {'max_retries': -1}):
            with self.assertRaises(ValueError):
                self.api(**values)
