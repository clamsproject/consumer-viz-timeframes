import pytest
from mmif import AnnotationTypes, Document, DocumentTypes, Mmif

from mmif_consumer import ConsumerError
from viz_timeframes import extract


def new_mmif(*doc_ids, duration=60000):
    mmif = Mmif(validate=False)
    mmif.metadata.mmif = 'http://mmif.clams.ai/1.0.5'
    for doc_id in doc_ids:
        document = Document()
        document.at_type = DocumentTypes.VideoDocument
        document.id = doc_id
        document.properties.mime = 'video/mp4'
        document.location = f'file:///data/{doc_id}.mp4'
        if duration is not None:
            document.properties['duration'] = duration
        mmif.add_document(document)
    return mmif


def add_view(mmif, document='m1', unit='milliseconds'):
    view = mmif.new_view()
    view.metadata.app = 'http://apps.clams.ai/test/v1'
    view.new_contain(AnnotationTypes.TimeFrame, document=document,
                     timeUnit=unit)
    return view


def collect(mmif, doc_id='m1'):
    warnings = []
    tracks = extract.extract_tracks(mmif, mmif[doc_id], warnings.append)
    return tracks, warnings


def test_times_are_converted_to_milliseconds():
    mmif = new_mmif('m1')
    view = add_view(mmif, unit='seconds')
    view.new_annotation(AnnotationTypes.TimeFrame, start=1.5, end=3,
                        label='en')
    tracks, _ = collect(mmif)
    assert tracks[0].segments == [extract.Segment(1500, 3000, 'en')]


def test_times_come_from_targets():
    mmif = new_mmif('m1')
    view = add_view(mmif)
    view.new_contain(AnnotationTypes.TimePoint, document='m1',
                     timeUnit='milliseconds')
    first = view.new_annotation(AnnotationTypes.TimePoint, timePoint=1000)
    last = view.new_annotation(AnnotationTypes.TimePoint, timePoint=2000)
    view.new_annotation(AnnotationTypes.TimeFrame, label='slate',
                        targets=[first.id, last.id])
    tracks, warnings = collect(mmif)
    assert warnings == []
    assert tracks[0].segments == [extract.Segment(1000, 2000, 'slate')]


def test_frames_without_label_are_unlabeled():
    mmif = new_mmif('m1')
    view = add_view(mmif)
    view.new_annotation(AnnotationTypes.TimeFrame, start=0, end=10)
    tracks, _ = collect(mmif)
    assert tracks[0].segments[0].label == extract.NO_LABEL


def test_frames_without_usable_times_are_skipped_with_a_warning():
    mmif = new_mmif('m1')
    view = add_view(mmif)
    view.new_annotation(AnnotationTypes.TimeFrame, start=20, end=10)
    view.new_annotation(AnnotationTypes.TimeFrame, start=0, end=10)
    tracks, warnings = collect(mmif)
    assert len(tracks[0].segments) == 1
    assert len(warnings) == 1


def test_views_of_other_documents_are_not_tracks():
    mmif = new_mmif('m1', 'm2')
    add_view(mmif, 'm1').new_annotation(AnnotationTypes.TimeFrame,
                                        start=0, end=10)
    add_view(mmif, 'm2').new_annotation(AnnotationTypes.TimeFrame,
                                        start=0, end=10)
    tracks, _ = collect(mmif, 'm2')
    assert [t.view_id for t in tracks] == ['v_1']


def test_media_selection_needs_an_id_for_several_candidates():
    mmif = new_mmif('m1', 'm2')
    add_view(mmif, 'm1')
    add_view(mmif, 'm2')
    with pytest.raises(ConsumerError, match='--document'):
        extract.select_media(mmif)
    assert extract.select_media(mmif, 'm2').id == 'm2'


def test_media_selection_takes_the_only_document_with_timeframes():
    mmif = new_mmif('m1', 'm2')
    add_view(mmif, 'm2')
    assert extract.select_media(mmif).id == 'm2'


def test_duration_from_the_option_then_the_mmif_then_the_last_frame():
    tracks = [extract.Track('v_0', 'app',
                            [extract.Segment(0, 70000, 'en')])]
    warnings = []
    recorded = new_mmif('m1', duration=90000)['m1']
    missing = new_mmif('m1', duration=None)['m1']
    assert extract.total_duration_ms(recorded, tracks, 80000,
                                     warnings.append) == 80000
    assert extract.total_duration_ms(recorded, tracks, None,
                                     warnings.append) == 90000
    assert warnings == []
    assert extract.total_duration_ms(missing, tracks, None,
                                     warnings.append) == 70000
    assert len(warnings) == 1
