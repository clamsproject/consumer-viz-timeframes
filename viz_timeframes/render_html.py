"""
HTML mode: one page with a media player and a timeline.
"""
import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from viz_timeframes.extract import Track

TEMPLATE = Path(__file__).with_name('page.html')
DATA_MARK = '/*__DATA__*/null'


def render(tracks: List[Track], duration_ms: int, kind: str,
           src: Optional[str], file_name: str) -> str:
    """
    Creates the page.

    :param tracks: the tracks to show
    :param duration_ms: duration of the timeline
    :param kind: ``video`` or ``audio``
    :param src: reference to the media, None if not available
    :param file_name: file name of the media in the MMIF
    :returns: the HTML page
    """
    data = {'tracks': [asdict(t) for t in tracks], 'duration_ms': duration_ms,
            'kind': kind, 'src': src, 'file_name': file_name}
    # the data sits in a script element, which a closing tag would end
    payload = json.dumps(data).replace('</', '<\\/')
    return TEMPLATE.read_text(encoding='utf8').replace(DATA_MARK, payload)
