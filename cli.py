#!/usr/bin/env python3
'''%(prog)s -- A command-line app that helps you win a Wordle game.

Copyright (c) 2021 Gino Latorilla
'''
import sys
from pathlib import Path
import logging
import argparse

try:
    from rich.logging import RichHandler
    PRETTY_FEATURE_ON = True
except ImportError:
    PRETTY_FEATURE_ON = False

import data

APP_NAME = Path(sys.argv[0]).stem
log = logging.getLogger(APP_NAME)


def main() -> int:
    parser = make_cl_argument_parser()
    program_options = parser.parse_args()
    setup_logger(program_options.verbosity, program_options.no_color)

    # TODO: Continue here, and use program_options.
    return 0


def make_cl_argument_parser() -> argparse.ArgumentParser:
    # TODO: Add/remove command line arguments in this dictionary.
    # The 'keys' are positional arguments to argparse.ArgumentParser.add_argument and
    # the 'values' are the keyword arguments.
    arguments_spec = {
        ('required',
         ): {
            'help': 'This is a required argument.'
        },
        (
            '-o',
            '--optional',
        ): {
            'help': 'This is an optional argument.',
            'default': 'default-value-for-optional'
        },
        (
            '-f',
            '--flag',
        ): {
            'help': 'This is a flag, an toggleable optional argument.',
            'action': 'store_true'
        },
        (
            '-v',
            '--verbose',
        ): {
            'help': 'Increase logging verbosity. Can be specified multiple times.',
            'action': 'count',
            'default': 0,
            'dest': 'verbosity'
        },
        (
            '--no-color',
            '--no-colour',
        ): {
            'help': 'Disable colouring of console output.',
            'action': 'store_true'
        },
    }

    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=type(
            'Formatter',
            (argparse.RawDescriptionHelpFormatter,
             argparse.ArgumentDefaultsHelpFormatter),
            {}
        )
    )
    for args, kwargs in arguments_spec.items():
        ap.add_argument(*args, **kwargs)  # type: ignore[arg-type]

    return ap


def setup_logger(verbosity: int, no_colour: bool) -> None:
    assert verbosity >= 0
    pretty = PRETTY_FEATURE_ON and not no_colour

    log_levels = {
        0: {
            'global': logging.WARNING,
            'local': logging.WARNING
        },
        1: {
            'global': logging.WARNING,
            'local': logging.INFO
        },
        2: {
            'global': logging.WARNING,
            'local': logging.DEBUG
        },
        3: {
            'global': logging.INFO,
            'local': logging.DEBUG
        },
    }.get(verbosity,
          {
              'global': logging.DEBUG,
              'local': logging.DEBUG
          })

    if pretty:
        log_format = {
            0: '{name}: {message}',
            1: '{name}: {message}',
            2: '{name}: {message}',
            3: '[pid={process}] {name}: {message}',
        }.get(verbosity,
              '[pid={process}] [tid={thread}] {name}({pathname}:{lineno}): {message}')
    else:
        log_format = {
            0: '[{levelname}] {name}: {message}',
            1: '[{levelname}] {name}: {message}',
            2: '<{asctime}> [{levelname}] {name}: {message}',
            3: '<{asctime}> [{levelname}] [pid={process}] {name}: {message}',
        }.get(
            verbosity,
            '<{asctime}> [{levelname}] [pid={process}] [tid={thread}] {name}({pathname}:{lineno}): {message}'
        )

    logging.basicConfig(
        level=log_levels['global'],
        style='{',
        format=log_format,
        handlers=[RichHandler(rich_tracebacks=True,
                              show_path=False)] if pretty else [logging.StreamHandler()]
    )
    log.setLevel(log_levels['local'])
    log.debug(f'Log level is {verbosity}.')
