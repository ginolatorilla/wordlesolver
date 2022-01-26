#!/usr/bin/env python3
'''%(prog)s -- A command-line app that helps you win a Wordle game.

Copyright (c) 2021 Gino Latorilla
'''
import argparse
import logging
import readline
import sys
from collections import defaultdict
from itertools import chain, repeat
from pathlib import Path
from typing import Dict, Iterable, List, Set

import rich
from rich.columns import Columns
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

import analytics
import data

APP_NAME = Path(sys.argv[0]).stem
log = logging.getLogger(APP_NAME)


def main() -> int:
    try:
        parser = make_cl_argument_parser()
        program_options = parser.parse_args()
        setup_logger(program_options.verbosity)

        predictor = analytics.Predictor(output_size=program_options.num_suggestions)
        MAX_ROUNDS = 6

        def pretty_round_counter() -> str:
            blanks = '○ ' * max(0, MAX_ROUNDS - predictor.round - 1)
            cold = '[grey50]●[/] ' * max(0, predictor.round - 1)
            hot_colour = ('green', 'green', 'green', 'yellow', 'yellow', 'red')
            return cold + f'[{hot_colour[predictor.round - 1]}]●[/] ' + blanks.rstrip()

        def pretty_game_board(guesses: Iterable[str], responses: Iterable[str]) -> Panel:

            def prettify_letter(letter: str, state: str) -> str:
                return f"[bold grey100 on { {'w': 'grey50', 'c': 'green', 'm': 'yellow'}[state] }] {letter} "

            # yapf: disable
            pretty_guesses = [
                ''.join(prettify_letter(letter, state) for letter, state in zip(guess, response))
                for guess, response, _ in zip(chain(guesses, repeat(' '*data.WORDLE_MAX_WORLD_LENGTH)), chain(responses, repeat('w' * data.WORDLE_MAX_WORLD_LENGTH)), range(MAX_ROUNDS))
            ]
            # yapf: enable
            return Panel.fit('\n'.join(pretty_guesses))

        def tabulate_predictor_letters(predictor: analytics.Predictor) -> Table:

            def reverse_dict(dictionary: Dict[str, Set[int]]) -> Dict[int, str]:
                reverse = defaultdict(str)  # type: Dict[int, str]
                for letter, indexes in dictionary.items():
                    for i in indexes:
                        reverse[i] += letter
                return reverse

            table = Table('Class', '1st', '2nd', '3rd', '4th', '5th', title='Predictor Letters')
            for row_name, data_source in {
                'Correct Letters': reverse_dict(predictor._correct_letters),
                'Wrong Letters': reverse_dict(predictor._wrong_letters),
                'Misplaced Letters': reverse_dict(predictor._misplaced_letters),
            }.items():
                table.add_row(
                    row_name,
                    *(data_source.get(position,
                                      '') for position in range(data.WORDLE_MAX_WORLD_LENGTH))
                )
            return table

        guesses = []  # type: List[str]
        responses = []  # type: List[str]

        while True:
            rich.print(f'[bold][blue]WordleSolver[/] - Round [blue]{predictor.round} - {pretty_round_counter()}')
            if guesses and responses:
                rich.print(pretty_game_board(guesses, responses))

            suggestions = predictor.predict_wordle()
            if not suggestions:
                rich.print(
                    '😩 I ran out of words. Either your game has no solution or the Wordle is not in my vocabulary.',
                    file=sys.stderr
                )
                return 1

            log.info(f'Wordbank has {len(predictor.wordbank)} words.')
            if program_options.verbosity:
                rich.print(tabulate_predictor_letters(predictor))

            rich.print('Here are my suggestions:')
            rich.print(
                Columns(
                    [f'[{"bold " if position == 0 else ""}blue]{word}' for position,
                     word in enumerate(suggestions)],
                    width=data.WORDLE_MAX_WORLD_LENGTH + 1,
                    equal=True
                ),
                ''
            )

            guess = ''
            game_response = ''

            while True:
                if not guess:
                    guess = rich.get_console().input('What was your guess? ')

                if not game_response:
                    game_response = rich.get_console().input('What was the result? ')

                try:
                    predictor.calibrate(guess, game_response)
                    guesses.append(guess)
                    responses.append(game_response)
                    break
                except ValueError as e:
                    rich.print(f'⚠️ {e.args[0]}', file=sys.stderr)
                    if 'response' in e.args[0]:
                        game_response = ''
                    else:
                        guess = ''
                except analytics.EndGameError:
                    rich.print('😔 You [red]lost[/]. The game has already ended.', file=sys.stderr)
                    return 1
                except analytics.Victory:
                    rich.print('🎉 [bold]You [green]won!')
                    return 0
                finally:
                    rich.print()

    except KeyboardInterrupt:
        rich.print('👋 Bye!')
        return 0


def make_cl_argument_parser() -> argparse.ArgumentParser:
    arguments_spec = {
        (
            '-n',
            '--num-suggestions',
        ): {
            'type': int,
            'help': 'Number of suggestions to present.',
            'default': 3
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


def setup_logger(verbosity: int) -> None:
    assert verbosity >= 0
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

    log_format = {
        0: '{name}: {message}',
        1: '{name}: {message}',
        2: '{name}: {message}',
        3: '[pid={process}] {name}: {message}',
    }.get(verbosity,
          '[pid={process}] [tid={thread}] {name}({pathname}:{lineno}): {message}')

    logging.basicConfig(
        level=log_levels['global'],
        style='{',
        format=log_format,
        handlers=[RichHandler(rich_tracebacks=True,
                              show_path=False)]
    )
    log.setLevel(log_levels['local'])
    log.debug(f'Log level is {verbosity}.')
