"""
Shows the TimeFrame annotations of a MMIF as text or as an HTML page.
"""
import subprocess
from importlib import metadata
from pathlib import Path

# the distribution and the command that pyproject.toml installs
DISTRIBUTION = 'consumer-viz-timeframes'
TOOL_NAME = 'viz-timeframes'
SOURCE_TREE = Path(__file__).resolve().parent.parent


def tool_version() -> str:
    """
    Finds the version of this tool. In a git checkout of the source, this is
    the output of ``git describe``; otherwise, it is the version of the
    installed distribution, which comes from ``pyproject.toml``.

    :returns: the version, ``unknown`` if neither is available
    """
    if (SOURCE_TREE / '.git').exists():
        try:
            return subprocess.run(
                ['git', 'describe', '--tags', '--always', '--dirty'],
                cwd=SOURCE_TREE, capture_output=True, text=True,
                check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    try:
        return metadata.version(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return 'unknown'
