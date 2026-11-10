"""
Shows the TimeFrame annotations of a video or audio file as rows of text or
as an HTML page.
"""
from pathlib import Path

from mmif_consumer import Consumer, ConsumerError, run_cli
from viz_timeframes import extract, media, render_html, render_text

FORMATS = ('text', 'html')
HTML_SUFFIXES = ('.html', '.htm')


class TimeFramesViz(Consumer):

    description = __doc__

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--format', choices=FORMATS,
                            help='artifact format (default: html when OUT '
                                 'ends with .html, text otherwise)')
        parser.add_argument('--document', metavar='ID',
                            help='media document to show, when there are '
                                 'many')
        parser.add_argument('--duration', type=int, metavar='MS',
                            help='media duration, when the MMIF has none')
        parser.add_argument('--document-location', metavar='REF',
                            help='html: full path or URL of the media file')

    @classmethod
    def path_defaults(cls, in_path, out_path):
        defaults = {}
        if in_path:
            defaults['mmif_name'] = Path(in_path).name
        if out_path and Path(out_path).suffix.lower() in HTML_SUFFIXES:
            defaults['format'] = 'html'
        return defaults

    def _consume(self, mmif, format='text', document=None, duration=None,
                 document_location=None, mmif_name=None):
        if format not in FORMATS:
            raise ConsumerError(f'unknown format: {format}')
        media_doc = extract.select_media(mmif, document)
        tracks = extract.extract_tracks(mmif, media_doc, self.warn)
        total = extract.total_duration_ms(media_doc, tracks, duration,
                                          self.warn)
        if format == 'text':
            return render_text.render(tracks, total)
        src = media.resolve_src(media_doc, document_location, self.warn)
        return render_html.render(tracks, total,
                                  extract.media_kind(media_doc), src,
                                  media.media_file_name(media_doc),
                                  mmif_name)


def main(argv=None) -> int:
    """
    Runs the command line interface.

    :param argv: command line arguments, ``sys.argv`` if not given
    :returns: the exit status
    """
    return run_cli(TimeFramesViz, argv)
