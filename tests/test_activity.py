"""Behavior tests: completeness, faithful rendering, determinism and failed-refresh retention."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_activity as fetch
import generate_activity_svg as render


def fixture():
    start = date(2025, 10, 24)
    days = [{'date': (start + timedelta(days=i)).isoformat(), 'count': i % 5, 'level': i % 5} for i in range(365)]
    return {'schema_version': 1, 'login': 'example', 'start': days[0]['date'], 'end': days[-1]['date'],
            'calendar_total': sum(d['count'] for d in days), 'days': days,
            'monthly': [{'start': a.isoformat(), 'end': b.isoformat(), 'commits': 0, 'prs': 0, 'issues': 0, 'reviews': 0}
                        for a, b in fetch.periods(start, start + timedelta(days=364))],
            'stats': {'public_repositories': 0, 'original_repository_stars': 0, 'visible_commit_contributions': 0,
                      'prs_opened': 0, 'prs_merged': 0, 'external_prs_opened': 0}, 'milestones': []}


class ActivityTests(unittest.TestCase):
    def test_schema_window_and_intensity_contract(self):
        for mutation in ('schema', 'window', 'intensity', 'publication'):
            with self.subTest(mutation=mutation):
                data = fixture()
                if mutation == 'schema': data['schema_version'] = 2
                if mutation == 'window': data['start'] = '2025-10-25'
                if mutation == 'intensity': data['days'][0]['level'] = 1
                if mutation == 'publication': data['updated_on'] = '2025-01-01'
                with self.assertRaises(AssertionError): fetch.validate(data)

    def test_missing_duplicate_dates_rejected(self):
        for mutation in ('missing', 'duplicate', 'negative', 'total'):
            with self.subTest(mutation=mutation):
                data = fixture()
                if mutation == 'missing': data['days'].pop()
                if mutation == 'duplicate': data['days'][1] = deepcopy(data['days'][0])
                if mutation == 'negative': data['days'][0]['count'] = -1
                if mutation == 'total': data['calendar_total'] += 1
                with self.assertRaises(AssertionError): fetch.validate(data)

    def test_months_cover_leap_year_and_partial_boundaries(self):
        windows = list(fetch.periods(date(2024, 1, 17), date(2024, 3, 8)))
        self.assertEqual(windows, [(date(2024, 1, 17), date(2024, 1, 31)), (date(2024, 2, 1), date(2024, 2, 29)), (date(2024, 3, 1), date(2024, 3, 8))])

    def test_deterministic_svg_and_exact_daily_values_in_both_themes(self):
        data = fixture()
        with tempfile.TemporaryDirectory() as directory:
            first = render.generate(data, Path(directory))
            second = render.generate(data, Path(directory))
            self.assertEqual(first, second)
            for name, svg in first.items():
                if name.endswith('.svg'):
                    root = ET.fromstring(svg)
                    if name.startswith('calendar'):
                        observed = [(n.attrib['data-date'], int(n.attrib['data-count']), int(n.attrib['data-level'])) for n in root.iter() if 'data-date' in n.attrib]
                        self.assertEqual(observed, [(d['date'], d['count'], d['level']) for d in data['days']])

    def test_zero_activity_graph_is_valid(self):
        data = fixture()
        for d in data['days']: d.update(count=0, level=0)
        data['calendar_total'] = 0
        ET.fromstring(render.trend(data, render.PALETTES['light']))
        fetch.validate(data)

    def test_failed_fetch_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'activity.json'
            output.write_text('previous valid snapshot')
            with patch.dict('os.environ', {'GH_TOKEN': 'test-only-token'}), patch.object(sys, 'argv', ['fetch_activity.py', '--output', str(output)]), patch.object(fetch, 'fetch', side_effect=RuntimeError('API unavailable')):
                with self.assertRaises(RuntimeError): fetch.main()
            self.assertEqual(output.read_text(), 'previous valid snapshot')

    def test_unchanged_fetch_preserves_publication_date_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'activity.json'
            data = fixture()
            previous = {**data, 'updated_on': data['end']}
            before = json.dumps(previous, indent=2, ensure_ascii=False) + '\n'
            output.write_text(before, encoding='utf-8', newline='\n')
            with patch.dict('os.environ', {'GH_TOKEN': 'test-only-token'}), patch.object(sys, 'argv', ['fetch_activity.py', '--output', str(output)]), patch.object(fetch, 'fetch', return_value=data):
                fetch.main()
            self.assertEqual(output.read_text(encoding='utf-8'), before)


if __name__ == '__main__':
    unittest.main()
