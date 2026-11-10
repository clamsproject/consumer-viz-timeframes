"""
Text mode: the timeline of each track as rows of characters.

A character stands for 10 s, a group of characters for one minute, and a
row for 10 minutes. A character shows the label with the most time in its
10 s: in upper case when the label covers at least half of that time, in
lower case when it covers less. A dot marks 10 s with no TimeFrame.
"""
import string
import textwrap
from bisect import bisect_right
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from viz_timeframes.extract import Track

SPAN_MS = 10000
# characters in a group and in a row, separated by a space between groups
GROUP_CHARS = 6
ROW_CHARS = 60
GROUP_MS = SPAN_MS * GROUP_CHARS
ROW_MS = SPAN_MS * ROW_CHARS
HOUR_MS = 3600000
GAP_CHAR = '.'
GAP_NAME = 'no TimeFrame'
# shared by the labels that get no letter of their own
OTHER_CHAR = '*'
LETTERS = string.ascii_uppercase
# labels with a letter of their own, so that a legend stays short
MAX_NAMED = 10
LEGEND_SEPARATOR = '   '


def label_totals(track: Track) -> Dict[str, int]:
    """
    Sums the time of each label of a track.

    :param track: the track
    :returns: map from labels to milliseconds
    """
    totals = defaultdict(int)
    for segment in track.segments:
        totals[segment.label] += segment.end_ms - segment.start_ms
    return totals


def assign_chars(totals: Dict[str, int]) -> Dict[str, str]:
    """
    Gives each label of a track a character. The ``MAX_NAMED`` labels with
    the most time get one letter each, and the others share
    ``OTHER_CHAR``. A label gets its first letter if that is free, else
    another letter of the label, else the first free letter. Labels get
    their letters in alphabetical order, so that the same labels get the
    same letters in every MMIF.

    :param totals: map from labels to their time
    :returns: map from labels to characters
    """
    ranked = sorted(totals, key=lambda label: (-totals[label], label))
    chars = {label: OTHER_CHAR for label in ranked[MAX_NAMED:]}
    used = set()
    for label in sorted(ranked[:MAX_NAMED]):
        own = [c for c in label.upper() if c in LETTERS]
        char = next(c for c in own + list(LETTERS) if c not in used)
        chars[label] = char
        used.add(char)
    return chars


def _spans(duration_ms: int) -> List[Tuple[int, int]]:
    # the last span ends with the timeline, so it can be shorter
    return [(start, min(start + SPAN_MS, duration_ms))
            for start in range(0, duration_ms, SPAN_MS)]


def _span_coverage(track: Track, chars: Dict[str, str],
                   spans: List[Tuple[int, int]]) -> List[Dict[str, int]]:
    """
    Sums, for each span, the time of each character in it.
    """
    starts = [start for start, _ in spans]
    coverage = [defaultdict(int) for _ in spans]
    for segment in track.segments:
        first = max(0, bisect_right(starts, segment.start_ms) - 1)
        for i in range(first, len(spans)):
            start, end = spans[i]
            if start >= segment.end_ms:
                break
            overlap = min(end, segment.end_ms) - max(start, segment.start_ms)
            if overlap > 0:
                coverage[i][chars[segment.label]] += overlap
    return coverage


def render_chars(track: Track, chars: Dict[str, str],
                 duration_ms: int) -> str:
    """
    Creates the characters of a track, one for every ``SPAN_MS``.

    :param track: the track
    :param chars: map from labels to characters
    :param duration_ms: duration of the timeline
    :returns: the characters
    """
    spans = _spans(duration_ms)
    cells = []
    for (start, end), by_char in zip(spans,
                                     _span_coverage(track, chars, spans)):
        if not by_char:
            cells.append(GAP_CHAR)
            continue
        char = max(by_char, key=by_char.get)
        cells.append(char if 2 * by_char[char] >= end - start
                     else char.lower())
    return ''.join(cells)


def _clock(ms: int, hours: bool) -> str:
    seconds = ms // 1000
    if hours:
        return (f'{seconds // 3600}:{seconds // 60 % 60:02d}'
                f':{seconds % 60:02d}')
    return f'{seconds // 60}:{seconds % 60:02d}'


def _row_label_size(duration_ms: int) -> int:
    last_row_ms = (duration_ms - 1) // ROW_MS * ROW_MS
    return len(_clock(last_row_ms, duration_ms >= HOUR_MS))


def _columns(duration_ms: int) -> int:
    # the row label, ` |`, the characters with the spaces between groups,
    # and `|`
    spaces = ROW_CHARS // GROUP_CHARS - 1
    return _row_label_size(duration_ms) + 2 + ROW_CHARS + spaces + 1


def _grouped(cells: str) -> str:
    return ' '.join(cells[i:i + GROUP_CHARS]
                    for i in range(0, len(cells), GROUP_CHARS))


def render_rows(cells: str, duration_ms: int) -> List[str]:
    """
    Splits the characters of a track into rows of ``ROW_CHARS`` in groups
    of ``GROUP_CHARS``, each row with the time where it starts.

    :param cells: the characters
    :param duration_ms: duration of the timeline
    :returns: the rows
    """
    hours = duration_ms >= HOUR_MS
    size = _row_label_size(duration_ms)
    return [f'{_clock(i * SPAN_MS, hours):>{size}} |'
            f'{_grouped(cells[i:i + ROW_CHARS])}|'
            for i in range(0, len(cells), ROW_CHARS)]


def _covered_ms(track: Track, duration_ms: int) -> int:
    """
    Finds the time that at least one TimeFrame of a track covers.
    """
    covered, reach = 0, 0
    for segment in track.segments:
        start = max(segment.start_ms, reach)
        end = min(segment.end_ms, duration_ms)
        if end > start:
            covered += end - start
            reach = end
    return covered


def _share(ms: int, duration_ms: int) -> str:
    if 0 < 200 * ms < duration_ms:
        return '<1%'
    return f'{ms / duration_ms:.0%}'


def _count(n: int) -> str:
    return f'{n} TimeFrame' + ('' if n == 1 else 's')


def _wrap(parts: List[str], columns: int) -> str:
    lines = []
    for part in parts:
        line = (lines[-1] + LEGEND_SEPARATOR + part) if lines else part
        if lines and len(line) <= columns:
            lines[-1] = line
        else:
            lines.append(part)
    return '\n'.join(lines)


def render_legend(track: Track, chars: Dict[str, str], duration_ms: int,
                  columns: int) -> str:
    """
    Creates the legend of a track: the character, time share and number of
    TimeFrames of each label, and the time share with no TimeFrame.

    :param track: the track
    :param chars: map from labels to characters
    :param duration_ms: duration of the timeline
    :param columns: maximum length of a line
    :returns: the legend
    """
    totals = label_totals(track)
    counts = Counter(segment.label for segment in track.segments)
    parts = []
    others = []
    for label in sorted(totals, key=lambda label: (-totals[label], label)):
        if chars[label] == OTHER_CHAR:
            others.append(label)
            continue
        parts.append(f'{chars[label]}: {label} ('
                     f'{_share(totals[label], duration_ms)}, '
                     f'{_count(counts[label])})')
    if others:
        other_ms = sum(totals[label] for label in others)
        parts.append(f'{OTHER_CHAR}: {len(others)} other labels ('
                     f'{_share(other_ms, duration_ms)}, '
                     f'{_count(sum(counts[label] for label in others))})')
    gap_ms = duration_ms - _covered_ms(track, duration_ms)
    if gap_ms > 0:
        parts.append(f'{GAP_CHAR}: {GAP_NAME} '
                     f'({_share(gap_ms, duration_ms)})')
    return _wrap(parts, columns)


def render_header(duration_ms: int) -> str:
    """
    Creates the text that explains the rows.

    :param duration_ms: duration of the timeline
    :returns: the text
    """
    return (f'Duration {_clock(duration_ms, duration_ms >= HOUR_MS)}. '
            f'A row is {ROW_MS // 60000} minutes, a group '
            f'{GROUP_MS // 60000} minute, and a character {SPAN_MS // 1000} '
            f's. A character shows the label with the most time in it, in '
            f'lower case when that label covers less than half of it.')


def render(tracks: List[Track], duration_ms: int) -> str:
    """
    Creates the text artifact.

    :param tracks: the tracks to show
    :param duration_ms: duration of the timeline
    :returns: the text
    """
    columns = _columns(duration_ms)
    blocks = [textwrap.fill(render_header(duration_ms), columns)]
    for track in tracks:
        chars = assign_chars(label_totals(track))
        cells = render_chars(track, chars, duration_ms)
        blocks.append('\n'.join(
            [f'{track.view_id} ({track.app})']
            + render_rows(cells, duration_ms)
            + [render_legend(track, chars, duration_ms, columns)]))
    return '\n\n'.join(blocks) + '\n'
