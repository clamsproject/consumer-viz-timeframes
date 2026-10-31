"""
Shared parts of MMIF consumers: a base class and a command line runner.

This package imports only the standard library and ``mmif``, so that it can
move to another distribution as one directory.
"""
import abc
import argparse
import json
import sys
from pathlib import Path
from typing import List, Union

from mmif import Mmif

Artifact = Union[str, bytes]


class ConsumerError(Exception):
    """
    The consumer cannot create the artifact from the given input.
    """


class Consumer(abc.ABC):
    """
    Base class of a consumer. A subclass implements :meth:`_consume`.
    """

    description = ''

    def __init__(self):
        self.warnings: List[str] = []

    @classmethod
    def add_arguments(cls, parser: argparse.ArgumentParser) -> None:
        """
        Adds the options of a consumer. All options must have the default
        value ``None``, and the consumer sets the effective default values.

        :param parser: the parser of the command line runner
        """

    def warn(self, message: str) -> None:
        """
        Records a problem that does not stop the creation of the artifact.

        :param message: one-line description of the problem
        """
        self.warnings.append(message)

    def consume(self, source: Union[Mmif, str], **params) -> Artifact:
        """
        Creates the artifact.

        :param source: a MMIF object, or a MMIF JSON string
        :param params: options of the consumer
        :returns: the artifact
        """
        mmif = source if isinstance(source, Mmif) else Mmif(source)
        return self._consume(mmif, **params)

    @abc.abstractmethod
    def _consume(self, mmif: Mmif, **params) -> Artifact:
        """
        Creates the artifact. This method does not write files.

        :param mmif: the input MMIF
        :param params: options of the consumer
        :returns: the artifact
        :raises ConsumerError: if the input does not meet the requirements
        """


def _read_config(path: str) -> dict:
    config = json.loads(Path(path).read_text(encoding='utf8'))
    if not isinstance(config, dict):
        raise ConsumerError(f'{path} must contain a JSON object')
    return config


def run_cli(consumer_class, argv=None) -> int:
    """
    Runs a consumer with the command line interface of the consumer contract.

    :param consumer_class: subclass of :class:`Consumer`
    :param argv: command line arguments, ``sys.argv`` if not given
    :returns: the exit status
    """
    parser = argparse.ArgumentParser(description=consumer_class.description)
    parser.add_argument('IN_MMIF', nargs='?', default='-',
                        help='input MMIF path, STDIN if `-` or not provided')
    parser.add_argument('-o', '--output', metavar='OUT',
                        help='output path, STDOUT if not provided')
    parser.add_argument('-c', '--config', metavar='CONFIG',
                        help='JSON file with options of the consumer')
    consumer_class.add_arguments(parser)
    args = vars(parser.parse_args(argv))
    in_path, out_path = args.pop('IN_MMIF'), args.pop('output')
    config_path = args.pop('config')

    consumer = consumer_class()
    try:
        params = _read_config(config_path) if config_path else {}
        params.update({k: v for k, v in args.items() if v is not None})
        if in_path == '-':
            source = sys.stdin.read()
        else:
            source = Path(in_path).read_text(encoding='utf8')
        artifact = consumer.consume(source, **params)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1
    finally:
        for warning in consumer.warnings:
            print(f'Warning: {warning}', file=sys.stderr)

    if isinstance(artifact, str):
        artifact = artifact.encode('utf8')
    if out_path:
        Path(out_path).write_bytes(artifact)
    else:
        sys.stdout.buffer.write(artifact)
    return 0
