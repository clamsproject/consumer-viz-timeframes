"""
Finds the reference to the media file that the HTML page uses.
"""
import os
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote, urlparse

from mmif.serialize.annotation import Document

URL_SCHEMES = ('http', 'https')


def _file_name(document: Document) -> str:
    location = urlparse(document.location or '')
    return os.path.basename(location.path) or location.netloc


def _is_url(reference: str) -> bool:
    return '://' in reference


def _to_src(reference: str, warn: Callable[[str], None]) -> str:
    if _is_url(reference):
        return reference
    if not Path(reference).exists():
        warn(f'{reference} does not exist on this computer')
    if os.path.isabs(reference):
        return Path(reference).as_uri()
    return quote(reference)


def media_file_name(document: Document) -> str:
    """
    Gives the file name of the media in the MMIF.

    :param document: the media document
    :returns: the file name, can be empty
    """
    return _file_name(document)


def resolve_src(document: Document, document_location: Optional[str],
                warn: Callable[[str], None]) -> Optional[str]:
    """
    Finds the value of the ``src`` attribute of the media player.

    :param document: the media document
    :param document_location: full path or URL from the user
    :param warn: function that records a warning
    :returns: the reference, None if nothing is available
    """
    if document_location:
        return _to_src(document_location, warn)
    if document.location_scheme() in URL_SCHEMES:
        # the page refers to this URL, so the file is not downloaded here
        return document.location
    try:
        path = document.location_path()
    except ValueError as e:
        warn(f'cannot resolve the media location: {e}')
        return None
    if path is None:
        warn('the MMIF records no media location')
        return None
    return _to_src(path, warn)
