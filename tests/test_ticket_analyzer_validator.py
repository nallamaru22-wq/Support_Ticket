import os
import sys
import tempfile
import unittest
from unittest import mock
import json
from datetime import datetime, timedelta, UTC

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ticket_analyzer_validator as tav


class ExtraTests(unittest.TestCase):
    def make_csv(self, contents: str):
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
        tf.write(contents)
        tf.flush()
        tf.close()
        return tf.name

    def test_missing_required_field(self):
        # missing 'subject' column
        csv = """ticket_id,customer_id,description,priority,status,created_date,resolved_date,assigned_to
T1,C1,desc,High,Resolved,2024-10-01,2024-10-02,Agent
"""
        path = self.make_csv(csv)
        try:
            tickets, errors = tav.load_and_validate(path)
            self.assertTrue(errors)
            self.assertTrue(any('missing field' in e['errors'][0] for e in errors))
        finally:
            os.unlink(path)

    def test_invalid_priority_and_status(self):
        csv = """ticket_id,customer_id,subject,description,priority,status,created_date,resolved_date,assigned_to
T1,C1,subj,desc,BadPriority,BadStatus,2024-10-01,2024-10-02,Agent
"""
        path = self.make_csv(csv)
        try:
            tickets, errors = tav.load_and_validate(path)
            self.assertTrue(errors)
            errs = errors[0]['errors']
            self.assertTrue(any('invalid priority' in e for e in errs))
            self.assertTrue(any('invalid status' in e for e in errs))
        finally:
            os.unlink(path)

    @mock.patch('ticket_analyzer_validator.requests.get')
    def test_fetch_weather_timeout_and_bad_structure(self, mock_get):
        # Simulate timeout
        mock_get.side_effect = tav.requests.Timeout()
        res = tav.fetch_weather('fakekey', location='Nowhere', cache_file='nonexistent_cache.json', ttl=1)
        self.assertIsNone(res)

        # Simulate bad structure
        mock_resp = mock.Mock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'no_weather': True}
        mock_get.side_effect = None
        mock_get.return_value = mock_resp
        res2 = tav.fetch_weather('fakekey', location='Nowhere', cache_file='nonexistent_cache.json', ttl=1)
        self.assertIsNone(res2)

    def test_fetch_weather_uses_cache(self):
        # write a cache file with current ts
        data = {'weather': [{'description': 'sunny'}], 'main': {'temp': 20}, 'name': 'TestCity'}
        cache = {'ts': datetime.now(UTC).isoformat(), 'data': data}
        path = tempfile.NamedTemporaryFile(delete=False, suffix='.json').name
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(cache, fh)
        try:
            # Request the same location as present in the cache so the cache is used.
            res = tav.fetch_weather('fakekey', location='TestCity', cache_file=path, ttl=600)
            self.assertIsNotNone(res)
            self.assertEqual(res.get('name'), 'TestCity')
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()