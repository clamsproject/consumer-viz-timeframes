import io
import json
import re
from pathlib import Path

import pytest

from viz_timeframes.consumer import main

EXAMPLES = Path(__file__).resolve().parent.parent / 'examples'
DEMO = EXAMPLES / 'language-demo.mmif'
DOCTYPE = '<!doctype html>'


@pytest.fixture
def out_dir(tmp_path):
    return tmp_path


def test_text_goes_to_stdout(capsys):
    assert main([str(DEMO)]) == 0
    out = capsys.readouterr().out
    assert 'v_0 (demo-language-id/v1)' in out
    assert '0:00 |EESS' in out


def test_input_from_stdin(capsys, monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO(DEMO.read_text()))
    assert main([]) == 0
    assert '0:00 |EESS' in capsys.readouterr().out


@pytest.mark.parametrize('name, html', [
    ('page.html', True), ('page.HTM', True), ('rows.txt', False),
    ('rows', False)])
def test_format_follows_the_output_extension(out_dir, name, html):
    out = out_dir / name
    assert main([str(DEMO), '-o', str(out)]) == 0
    assert out.read_text().startswith(DOCTYPE) == html


def test_format_option_wins_over_the_extension(out_dir):
    out = out_dir / 'page.html'
    assert main([str(DEMO), '-o', str(out), '--format', 'text']) == 0
    assert not out.read_text().startswith(DOCTYPE)


def test_config_wins_over_the_extension_and_loses_to_options(out_dir):
    config = out_dir / 'config.json'
    config.write_text(json.dumps({'format': 'html'}))
    out = out_dir / 'rows.txt'
    assert main([str(DEMO), '-o', str(out), '-c', str(config)]) == 0
    assert out.read_text().startswith(DOCTYPE)
    assert main([str(DEMO), '-o', str(out), '-c', str(config),
                 '--format', 'text']) == 0
    assert not out.read_text().startswith(DOCTYPE)


def test_warnings_go_to_stderr(out_dir, capsys):
    # the demo video is not on this computer
    assert main([str(DEMO), '-o', str(out_dir / 'page.html')]) == 0
    assert 'Warning: /data/demo.mp4 does not exist' in capsys.readouterr().err


def test_errors_give_a_non_zero_status_and_no_artifact(out_dir, capsys):
    out = out_dir / 'rows.txt'
    assert main([str(out_dir / 'missing.mmif'), '-o', str(out)]) == 1
    assert capsys.readouterr().err.startswith('Error: ')
    assert not out.exists()


def page_data(path):
    found = re.search(r'const DATA = (\{.*?\});\n', path.read_text(), re.S)
    return json.loads(found.group(1))


def test_page_names_the_input_mmif(out_dir, monkeypatch):
    out = out_dir / 'page.html'
    assert main([str(DEMO), '-o', str(out)]) == 0
    assert page_data(out)['mmif_name'] == 'language-demo.mmif'
    monkeypatch.setattr('sys.stdin', io.StringIO(DEMO.read_text()))
    assert main(['-o', str(out)]) == 0
    assert page_data(out)['mmif_name'] is None
