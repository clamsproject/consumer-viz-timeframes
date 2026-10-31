"""
Reads TimeFrame annotations from a MMIF into plain data.
"""
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set, Tuple

from mmif import AnnotationTypes, DocumentTypes, Mmif
from mmif.serialize.annotation import Annotation, Document
from mmif.utils.timeunit_helper import convert

from mmif_consumer import ConsumerError

NO_LABEL = 'unlabeled'
DEFAULT_TIME_UNIT = 'milliseconds'
DURATION_PROPERTY = 'duration'
MEDIA_TYPES = (DocumentTypes.VideoDocument, DocumentTypes.AudioDocument)


@dataclass
class Segment:
    start_ms: int
    end_ms: int
    label: str


@dataclass
class Track:
    view_id: str
    app: str
    segments: List[Segment] = field(default_factory=list)


def _framed_document_ids(mmif: Mmif) -> Set[str]:
    views = mmif.get_all_views_contain(AnnotationTypes.TimeFrame)
    contained = [v.metadata.contains[AnnotationTypes.TimeFrame] for v in views]
    return {c.get('document') for c in contained}


def select_media(mmif: Mmif, document_id: Optional[str] = None) -> Document:
    """
    Finds the video or audio document to show. Without ``document_id``, this
    is the only media document that has TimeFrames.

    :param mmif: the input MMIF
    :param document_id: ID of the document, required for several candidates
    :returns: the media document
    :raises ConsumerError: if the selection is not possible
    """
    media = [d for doc_type in MEDIA_TYPES
             for d in mmif.get_documents_by_type(doc_type)]
    if document_id is not None:
        media = [d for d in media if d.id == document_id]
    if not media:
        raise ConsumerError('the MMIF has no matching video or audio document')
    framed = _framed_document_ids(mmif)
    # views with no `document` value can belong to any media document
    if None not in framed:
        media = [d for d in media if d.id in framed] or media
    if len(media) > 1:
        ids = ', '.join(d.id for d in media)
        raise ConsumerError(f'several media documents ({ids}), use --document')
    return media[0]


def media_kind(document: Document) -> str:
    """
    Gives the name of the HTML element that plays a document.

    :param document: the media document
    :returns: ``video`` or ``audio``
    """
    is_audio = document.at_type == DocumentTypes.AudioDocument
    return 'audio' if is_audio else 'video'


def _time_unit(mmif: Mmif, frame: Annotation) -> str:
    """
    Finds the unit of the time values that belong to a TimeFrame. The values
    of a TimeFrame with ``targets`` are in the unit of the target view.
    """
    anchor = frame
    if 'start' not in frame.properties and frame.get('targets'):
        anchor = mmif[frame.get('targets')[0]]
    for contained in mmif[anchor.parent].metadata.contains.values():
        unit = contained.get('timeUnit')
        if unit:
            return unit
    return DEFAULT_TIME_UNIT


def _times_ms(mmif: Mmif, frame: Annotation) -> Tuple[int, int]:
    unit = _time_unit(mmif, frame)
    start = mmif.get_start(frame)
    end = mmif.get_end(frame)
    # the fps value is not used in conversions between time units
    return (round(convert(start, unit, DEFAULT_TIME_UNIT, 1)),
            round(convert(end, unit, DEFAULT_TIME_UNIT, 1)))


def extract_tracks(mmif: Mmif, document: Document,
                   warn: Callable[[str], None]) -> List[Track]:
    """
    Creates one track per view with TimeFrames on the given document.

    :param mmif: the input MMIF
    :param document: the media document
    :param warn: function that records a warning
    :returns: tracks with their segments in time order
    :raises ConsumerError: if no view has TimeFrames for the document
    """
    tracks = []
    for view in mmif.get_all_views_contain(AnnotationTypes.TimeFrame):
        contained = view.metadata.contains[AnnotationTypes.TimeFrame]
        if contained.get('document', document.id) != document.id:
            continue
        track = Track(view.id, view.metadata.app)
        for frame in view.get_annotations(AnnotationTypes.TimeFrame):
            try:
                start_ms, end_ms = _times_ms(mmif, frame)
            except (KeyError, ValueError, IndexError) as e:
                warn(f'skipped {frame.id} of {view.id}: no usable times ({e})')
                continue
            if end_ms <= start_ms:
                warn(f'skipped {frame.id} of {view.id}: end is before start')
                continue
            label = frame.get('label') or frame.get('frameType') or NO_LABEL
            track.segments.append(Segment(start_ms, end_ms, str(label)))
        track.segments.sort(key=lambda s: s.start_ms)
        if track.segments:
            tracks.append(track)
    if not tracks:
        raise ConsumerError(f'no TimeFrames for document {document.id}')
    return tracks


def total_duration_ms(document: Document, tracks: List[Track],
                      duration: Optional[int],
                      warn: Callable[[str], None]) -> int:
    """
    Finds the duration of the timeline.

    :param document: the media document
    :param tracks: the tracks of the document
    :param duration: duration in ms that the user gives
    :param warn: function that records a warning
    :returns: duration in ms
    """
    last_end = max(s.end_ms for t in tracks for s in t.segments)
    if duration is not None:
        return max(int(duration), last_end)
    recorded = document.get(DURATION_PROPERTY)
    if recorded is not None:
        return max(int(recorded), last_end)
    warn('the MMIF records no media duration, the timeline ends at the last '
         'TimeFrame (use --duration to set it)')
    return last_end
