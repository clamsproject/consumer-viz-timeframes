#!/usr/bin/env python3
"""
Writes synthetic MMIF files for a two-minute video and for an audio track
extracted from it. All annotations are invented and exist only to show the
output of the consumer.
"""
import sys

from mmif import AnnotationTypes, Document, DocumentTypes, Mmif

APP = 'http://apps.clams.ai/demo-{}/v1'
LANGUAGES = [(0, 18000, 'en'), (18000, 44000, 'es'), (52000, 86000, 'es'),
             (86000, 120000, 'en')]
SCENES = [(1000, 7000, 'slate'), (30000, 38000, 'chyron'),
          (70000, 75000, 'chyron'), (108000, 119000, 'credits')]


def add_view(mmif, name, frames, document='m1'):
    view = mmif.new_view()
    view.metadata.app = APP.format(name)
    view.new_contain(AnnotationTypes.TimeFrame, document=document,
                     timeUnit='milliseconds')
    for start, end, label in frames:
        view.new_annotation(AnnotationTypes.TimeFrame, start=start, end=end,
                            label=label)


def add_document(mmif, doc_id, doc_type, mime, location):
    document = Document()
    document.at_type = doc_type
    document.id = doc_id
    document.properties.mime = mime
    document.location = location
    document.properties['duration'] = 120000
    mmif.add_document(document)


def new_mmif():
    mmif = Mmif(validate=False)
    mmif.metadata.mmif = 'http://mmif.clams.ai/1.0.5'
    add_document(mmif, 'm1', DocumentTypes.VideoDocument, 'video/mp4',
                 'file:///data/demo.mp4')
    return mmif


def write(mmif, path):
    with open(path, 'w', encoding='utf8') as f:
        f.write(mmif.serialize(pretty=True))


def main(video_path, audio_path):
    mmif = new_mmif()
    add_view(mmif, 'language-id', LANGUAGES)
    add_view(mmif, 'scene-detection', SCENES)
    write(mmif, video_path)

    mmif = new_mmif()
    add_document(mmif, 'm2', DocumentTypes.AudioDocument, 'audio/mp4',
                 'file:///data/demo.m4a')
    add_view(mmif, 'language-id', LANGUAGES, document='m2')
    write(mmif, audio_path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
