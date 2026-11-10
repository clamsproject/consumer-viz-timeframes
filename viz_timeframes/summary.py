"""
Numbers about a track that both artifact formats show: the time and number
of TimeFrames of each label, and the time with no TimeFrame.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from viz_timeframes.extract import Track

# labels shown on their own; the others are shown as one group
MAX_NAMED = 8
CLAMS_APP_PREFIXES = ('http://apps.clams.ai/', 'https://apps.clams.ai/')


@dataclass
class LabelRow:
    label: str
    ms: int
    count: int


@dataclass
class Legend:
    # in order of time, the most first
    named: List[LabelRow]
    others: List[LabelRow]
    gap_ms: int


def app_name(app: str) -> str:
    """
    Shortens the app URL of a CLAMS app to its name and version.

    :param app: the app of a view
    :returns: for example ``whisper-wrapper/v15``, or the app as it is
    """
    for prefix in CLAMS_APP_PREFIXES:
        if app.startswith(prefix):
            return app[len(prefix):]
    return app


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


def split_labels(totals: Dict[str, int]) -> Tuple[List[str], List[str]]:
    """
    Separates the ``MAX_NAMED`` labels with the most time from the others.

    :param totals: map from labels to their time
    :returns: both lists in order of time, the most first
    """
    ranked = sorted(totals, key=lambda label: (-totals[label], label))
    return ranked[:MAX_NAMED], ranked[MAX_NAMED:]


def covered_ms(track: Track, duration_ms: int) -> int:
    """
    Finds the time that at least one TimeFrame of a track covers.

    :param track: the track, with segments in order of start
    :param duration_ms: duration of the timeline
    :returns: milliseconds
    """
    covered, reach = 0, 0
    for segment in track.segments:
        start = max(segment.start_ms, reach)
        end = min(segment.end_ms, duration_ms)
        if end > start:
            covered += end - start
            reach = end
    return covered


def legend(track: Track, duration_ms: int) -> Legend:
    """
    Collects the numbers of the legend of a track.

    :param track: the track
    :param duration_ms: duration of the timeline
    :returns: the legend
    """
    totals = label_totals(track)
    counts = Counter(segment.label for segment in track.segments)
    named, others = split_labels(totals)
    return Legend([LabelRow(lb, totals[lb], counts[lb]) for lb in named],
                  [LabelRow(lb, totals[lb], counts[lb]) for lb in others],
                  duration_ms - covered_ms(track, duration_ms))


def share(ms: int, duration_ms: int) -> str:
    """
    Formats a share of the timeline, with ``<1%`` for a small share that
    is not zero.

    :param ms: the time
    :param duration_ms: duration of the timeline
    :returns: for example ``43%``
    """
    if 0 < 200 * ms < duration_ms:
        return '<1%'
    return f'{ms / duration_ms:.0%}'


def count_text(n: int) -> str:
    """
    Formats a number of TimeFrames.

    :param n: the number
    :returns: for example ``2 TimeFrames``
    """
    return f'{n} TimeFrame' + ('' if n == 1 else 's')
