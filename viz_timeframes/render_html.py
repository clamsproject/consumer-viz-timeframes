"""
HTML mode: one page with a media player and a timeline for each track.

The page script only draws. This module computes everything the page shows:
the lane and color of each segment, the legend and the axis.
"""
import base64
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from viz_timeframes import TOOL_NAME, summary, tool_version
from viz_timeframes.extract import Segment, Track

TEMPLATE = Path(__file__).with_name('page.html')
LOGO = Path(__file__).with_name('clams-logo.png')
DATA_MARK = '/*__DATA__*/null'
LOGO_MARK = '__LOGO__'
# categorical colors of the page, one for each named label
COLOR_SLOTS = summary.MAX_NAMED
OTHER_COLOR = -1
# time between two marks of the axis, in seconds
AXIS_STEPS_S = (1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600,
                7200, 14400)
MAX_TICKS = 8
# no mark this close to the end, where its time would not fit
AXIS_END_MARGIN = 0.08


def assign_lanes(segments: List[Segment]) -> List[Tuple[int, bool]]:
    """
    Puts each segment in the first lane where it does not overlap the
    segments before it.

    :param segments: segments in order of start
    :returns: for each segment, its lane and whether it starts where the
        previous segment of the lane ends
    """
    ends: List[int] = []
    placed = []
    for segment in segments:
        lane = next((i for i, end in enumerate(ends)
                     if end <= segment.start_ms), len(ends))
        if lane == len(ends):
            ends.append(segment.end_ms)
            placed.append((lane, False))
        else:
            placed.append((lane, ends[lane] == segment.start_ms))
            ends[lane] = segment.end_ms
    return placed


def assign_colors(named: List[List[str]]) -> List[Dict[str, int]]:
    """
    Gives the named labels of each track a color slot. A label keeps one
    slot in all tracks when the other labels of its tracks allow it, so the
    same label has the same color across views. Slots go to labels in
    alphabetical order, so the same labels get the same colors in every
    MMIF.

    :param named: for each track, its named labels, at most
        ``COLOR_SLOTS``
    :returns: for each track, a map from its named labels to slots
    """
    neighbors = defaultdict(set)
    for labels in named:
        for label in labels:
            neighbors[label].update(labels)
    shared = {}
    for label in sorted(neighbors):
        taken = {shared[n] for n in neighbors[label] if n in shared}
        free = [slot for slot in range(COLOR_SLOTS) if slot not in taken]
        if free:
            shared[label] = free[0]
    colors = []
    for labels in named:
        slots = {label: shared[label] for label in labels if label in shared}
        used = set(slots.values())
        for label in sorted(labels):
            if label not in slots:
                slots[label] = next(slot for slot in range(COLOR_SLOTS)
                                    if slot not in used)
                used.add(slots[label])
        colors.append(slots)
    return colors


def axis_ticks(duration_ms: int) -> List[int]:
    """
    Finds the times of the axis marks: at most ``MAX_TICKS`` marks at a
    round step.

    :param duration_ms: duration of the timeline
    :returns: times in milliseconds
    """
    step_ms = next((step_s * 1000 for step_s in AXIS_STEPS_S
                    if step_s * 1000 * MAX_TICKS >= duration_ms),
                   -(-duration_ms // MAX_TICKS))
    last = duration_ms * (1 - AXIS_END_MARGIN)
    return [ms for ms in range(0, duration_ms, step_ms)
            if ms == 0 or ms <= last]


def _track_data(track: Track, named_colors: Dict[str, int],
                duration_ms: int) -> dict:
    rows = summary.legend(track, duration_ms)
    placed = assign_lanes(track.segments)
    colors = dict(named_colors)
    colors.update((row.label, OTHER_COLOR) for row in rows.others)
    others = None
    if rows.others:
        others = {
            'labels': [row.label for row in rows.others],
            'share': summary.share(sum(row.ms for row in rows.others),
                                   duration_ms),
            'count': summary.count_text(sum(row.count
                                            for row in rows.others))}
    return {
        'view_id': track.view_id,
        'app': track.app,
        'name': summary.app_name(track.app),
        'lanes': 1 + max(lane for lane, _ in placed),
        'colors': colors,
        'segments': [{'start_ms': s.start_ms, 'end_ms': s.end_ms,
                      'label': s.label, 'lane': lane, 'joined': joined}
                     for s, (lane, joined) in zip(track.segments, placed)],
        'legend': [{'label': row.label, 'color': colors[row.label],
                    'share': summary.share(row.ms, duration_ms),
                    'count': summary.count_text(row.count)}
                   for row in rows.named],
        'others': others,
        'gap': (summary.share(rows.gap_ms, duration_ms)
                if rows.gap_ms > 0 else None),
    }


def render(tracks: List[Track], duration_ms: int, kind: str,
           src: Optional[str], file_name: str,
           mmif_name: Optional[str] = None) -> str:
    """
    Creates the page.

    :param tracks: the tracks to show
    :param duration_ms: duration of the timeline
    :param kind: ``video`` or ``audio``
    :param src: reference to the media, None if not available
    :param file_name: file name of the media in the MMIF
    :param mmif_name: file name of the input MMIF, None if not known
    :returns: the HTML page
    """
    named = [summary.split_labels(summary.label_totals(t))[0]
             for t in tracks]
    data = {'tracks': [_track_data(t, c, duration_ms)
                       for t, c in zip(tracks, assign_colors(named))],
            'duration_ms': duration_ms, 'ticks': axis_ticks(duration_ms),
            'kind': kind, 'src': src, 'file_name': file_name,
            'mmif_name': mmif_name,
            'tool': {'name': TOOL_NAME, 'version': tool_version()}}
    logo = base64.b64encode(LOGO.read_bytes()).decode('ascii')
    page = TEMPLATE.read_text(encoding='utf8').replace(
        LOGO_MARK, f'data:image/png;base64,{logo}')
    # the data sits in a script element, which a closing tag would end
    payload = json.dumps(data).replace('</', '<\\/')
    return page.replace(DATA_MARK, payload)
