"""
Text mode: one segmented bar per track.
"""
import shutil
import string
from collections import defaultdict
from typing import Dict, List

from viz_timeframes.extract import Track

GAP_CHAR = 'X'
GAP_NAME = 'no label'
# every cell takes two characters, and the bar has three more
CELL_SIZE = 2
BAR_OVERHEAD = 3


def default_width() -> int:
    """
    Finds the number of cells that fit the terminal.

    :returns: number of cells
    """
    columns = shutil.get_terminal_size((80, 24)).columns
    return max(1, (columns - BAR_OVERHEAD) // CELL_SIZE)


def assign_chars(labels: List[str]) -> Dict[str, str]:
    """
    Gives each label one unique character.

    :param labels: labels in the order of priority
    :returns: map from labels to characters
    """
    chars = {}
    used = {GAP_CHAR}
    for label in labels:
        for char in label.upper() + string.ascii_uppercase:
            if char.isalnum() and char not in used:
                chars[label] = char
                used.add(char)
                break
        else:
            chars[label] = '?'
    return chars


def _coverage(track: Track, start: float, end: float) -> Dict[str, float]:
    covered = defaultdict(float)
    for segment in track.segments:
        overlap = min(end, segment.end_ms) - max(start, segment.start_ms)
        if overlap > 0:
            covered[segment.label] += overlap
    return covered


def render_bar(track: Track, chars: Dict[str, str], duration_ms: int,
               width: int) -> str:
    """
    Creates the bar of a track. A cell shows the label that covers the most
    time in the cell, so that a short segment stays visible at any width.

    :param track: the track
    :param chars: map from labels to characters
    :param duration_ms: duration of the timeline
    :param width: number of cells
    :returns: the bar
    """
    cell_ms = duration_ms / width
    cells = []
    for i in range(width):
        covered = _coverage(track, i * cell_ms, (i + 1) * cell_ms)
        best = max(covered, key=covered.get, default=None)
        cells.append(chars[best] if best else GAP_CHAR)
    return '|-' + ''.join(c + '-' for c in cells) + '|'


def render_legend(track: Track, chars: Dict[str, str],
                  duration_ms: int) -> str:
    """
    Creates the legend of a track, with the share of each label.

    :param track: the track
    :param chars: map from labels to characters
    :param duration_ms: duration of the timeline
    :returns: the legend
    """
    totals = _coverage(track, 0, duration_ms)
    gap = duration_ms - sum(totals.values())
    parts = [f'{chars[label]}: {label} ({ms / duration_ms:.0%})'
             for label, ms in sorted(totals.items(), key=lambda x: -x[1])]
    if gap > 0:
        parts.append(f'{GAP_CHAR}: {GAP_NAME} ({gap / duration_ms:.0%})')
    return '   '.join(parts)


def render(tracks: List[Track], duration_ms: int, width: int = None) -> str:
    """
    Creates the text artifact.

    :param tracks: the tracks to show
    :param duration_ms: duration of the timeline
    :param width: number of cells, fits the terminal if not given
    :returns: the text
    """
    labels = list(dict.fromkeys(s.label for t in tracks for s in t.segments))
    chars = assign_chars(labels)
    width = int(width) if width else default_width()
    blocks = []
    for track in tracks:
        blocks.append(f'{track.view_id} ({track.app})\n'
                      f'{render_bar(track, chars, duration_ms, width)}\n'
                      f'{render_legend(track, chars, duration_ms)}\n')
    return '\n'.join(blocks)
