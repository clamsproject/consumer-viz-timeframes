import json
import re
import subprocess

import pytest

import viz_timeframes
from viz_timeframes import render_html, summary
from viz_timeframes.extract import Segment, Track

MINUTE = 60000


def track(view_id, *frames, app='http://apps.clams.ai/test/v1'):
    return Track(view_id, app, [Segment(*f) for f in frames])


def page_data(tracks, duration_ms=10 * MINUTE):
    page = render_html.render(tracks, duration_ms, 'video', None, 'a.mp4')
    found = re.search(r'const DATA = (\{.*?\});\n', page, re.S)
    return json.loads(found.group(1).replace('<\\/', '</'))


def test_overlapping_segments_go_to_other_lanes():
    segments = [Segment(0, 10, 'a'), Segment(5, 15, 'b'),
                Segment(10, 20, 'c'), Segment(20, 30, 'd')]
    assert render_html.assign_lanes(segments) == [
        (0, False), (1, False), (0, True), (0, True)]


def test_a_label_keeps_its_color_across_views():
    colors = render_html.assign_colors([['es', 'en'], ['en', 'fr']])
    assert colors[0]['en'] == colors[1]['en']
    assert len(set(colors[0].values())) == 2
    assert len(set(colors[1].values())) == 2


def test_colors_stay_distinct_in_a_view_when_they_cannot_be_shared():
    slots = render_html.COLOR_SLOTS
    first = [f'a{i}' for i in range(slots)]
    second = [f'b{i}' for i in range(slots - 1)] + ['a0']
    third = [f'b{i}' for i in range(slots - 1)] + ['a1']
    for view in render_html.assign_colors([first, second, third]):
        assert len(set(view.values())) == len(view)


def test_axis_marks_are_at_a_round_step():
    assert render_html.axis_ticks(30 * MINUTE + 23000) == [
        m * 5 * MINUTE for m in range(6)]
    # no mark right before the end, where its time would not fit
    assert render_html.axis_ticks(10 * MINUTE + 10000)[-1] == 8 * MINUTE


def test_page_data_has_lanes_colors_and_legend():
    t = track('v_0', (0, 2 * MINUTE, 'es'), (2 * MINUTE, 3 * MINUTE, 'en'),
              (3 * MINUTE, 4 * MINUTE, 'es'))
    data = page_data([t])['tracks'][0]
    assert data['name'] == 'test/v1'
    assert data['lanes'] == 1
    assert [s['joined'] for s in data['segments']] == [False, True, True]
    assert [e['label'] for e in data['legend']] == ['es', 'en']
    assert data['legend'][0]['share'] == '30%'
    assert data['legend'][0]['count'] == '2 TimeFrames'
    assert data['gap'] == '60%'
    assert data['others'] is None


def test_labels_beyond_the_limit_share_the_other_color():
    n = summary.MAX_NAMED + 3
    t = track('v_0', *((i * 1000, (i + 1) * 1000 - (i * 10), f'speaker_{i}')
                       for i in range(n)))
    data = page_data([t])['tracks'][0]
    assert len(data['legend']) == summary.MAX_NAMED
    assert len(data['others']['labels']) == 3
    for label in data['others']['labels']:
        assert data['colors'][label] == render_html.OTHER_COLOR
    named = [data['colors'][e['label']] for e in data['legend']]
    assert sorted(named) == list(range(render_html.COLOR_SLOTS))


def test_labels_cannot_close_the_script_element():
    t = track('v_0', (0, 1000, '</script><b>'))
    data = page_data([t])
    assert data['tracks'][0]['segments'][0]['label'] == '</script><b>'


def test_page_has_the_logo_and_the_tool():
    t = track('v_0', (0, 1000, '__LOGO__'))
    page = render_html.render([t], MINUTE, 'video', None, 'a.mp4', 'a.mmif')
    # the favicon and the header
    assert page.count('data:image/png;base64,') == 2
    data = page_data([t])
    assert data['tracks'][0]['segments'][0]['label'] == '__LOGO__'
    assert data['tool'] == {'name': 'viz-timeframes',
                            'version': viz_timeframes.tool_version()}


@pytest.mark.skipif(not (viz_timeframes.SOURCE_TREE / '.git').exists(),
                    reason='not a git checkout')
def test_version_in_a_checkout_comes_from_git():
    described = subprocess.run(
        ['git', 'describe', '--tags', '--always', '--dirty'],
        cwd=viz_timeframes.SOURCE_TREE, capture_output=True, text=True)
    assert viz_timeframes.tool_version() == described.stdout.strip()
