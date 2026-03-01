import tempfile
from pathlib import Path
from zena_mode.analysis import analyze_and_write_report
import security


def test_analyze_and_write_report(tmp_path, monkeypatch):
    """Test analyze and write report."""
    f = tmp_path / 'sample.py'
    f.write_text('''
import subprocess
def bar():
    global x
    x = 1
def foo():
    eval('1+1')
''')

    # Bypass path validation in test environment
    monkeypatch.setattr(security, 'validate_path', lambda p: True)
    report = analyze_and_write_report([str(f)], job_id='test123')
    assert report['job_id'] == 'test123'
    assert len(report['files']) == 1
    issues = report['files'][0]['issues']
    # Expect at least one issue for subprocess or eval
    assert any('subprocess' in i.get('message','') or 'eval' in i.get('message','') or 'uses eval' in i.get('message','') for i in issues)
