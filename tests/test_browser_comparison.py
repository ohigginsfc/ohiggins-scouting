import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('browser_comparison',ROOT/'scripts/compare_sofascore_browsers.py')
comparison=importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def test_403_cannot_be_success():
    assert comparison.summarize_response({'status':403,'body':'{}'},'calendar')=={'http_status':403,'valid':False}


def test_html_or_empty_calendar_cannot_be_success():
    for body in ('<html>Sofascore</html>','{"events":[]}','{"error":{"code":403}}'):
        assert not comparison.summarize_response({'status':200,'body':body},'calendar')['valid']


def test_original_extraction_does_not_execute_module_top_level(tmp_path):
    source=tmp_path/'original.py'
    source.write_text('raise RuntimeError("module executed")\ndef build_driver(headless=True):\n    return headless\n')
    build,sha=comparison.original_builder(source)
    assert build(headless=False) is False and len(sha)==64
