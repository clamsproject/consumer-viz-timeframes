#!/usr/bin/env python3
"""
Entry point of the consumer contract: :func:`consume` and the command line.
The installed command ``viz-timeframes`` runs the same command line.
"""
import sys

from mmif import Mmif

from viz_timeframes.consumer import TimeFramesViz, main


def consume(mmif: Mmif, **params):
    """
    Creates the artifact for a MMIF.

    :param mmif: the input MMIF
    :param params: options, see the command line help
    :returns: the artifact
    """
    return TimeFramesViz().consume(mmif, **params)


if __name__ == '__main__':
    sys.exit(main())
