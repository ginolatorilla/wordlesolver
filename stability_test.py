from http.client import responses
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from multiprocessing import Array
from statistics import mean
from typing import Any, Dict, Iterable, Set, List, Collection, Union
from dataclasses import dataclass

import pytest
import rich
from assertpy import assert_that
from rich.console import Console
from rich.progress import Progress, track
from rich.table import Table

import analytics
import data

pytestmark = pytest.mark.slow
# sample_size = 10
first_round_threshold = 50

error_console = Console(file=sys.stderr)
targets = list(data.read_wordle_dictionary())
shared_process_state = {
    word: Array('c',
                first_round_threshold * data.WORDLE_MAX_WORLD_LENGTH)
    for word in track(targets,
                      description='Preparing shared state',
                      console=error_console)
}


@dataclass
class _TestResult:
    game_id: int
    target_word: str
    success: bool
    caught_error: Union[BaseException, None]
    guesses: List[str]
    responses: List[str]

    def __hash__(self) -> int:
        return hash(self.game_id)


def test_stability() -> None:
    intermediate_test_results = set({})  # type: Set[_TestResult]

    with ProcessPoolExecutor() as executor:
        futures_to_game_args = {
            executor.submit(simulate_game,
                            *(game_args := (i + 1,
                                            target_word))): game_args
            for target_word in targets for i in range(first_round_threshold)
        }

        for future in track(
            as_completed(futures_to_game_args),
            total=len(futures_to_game_args),
            console=error_console
        ):
            test_id, target_word = futures_to_game_args[future]
            try:
                intermediate_test_results.add(r := future.result(timeout=1))
                if not r.success:
                    rich.print(':x:', end='')
            except TimeoutError as e:
                intermediate_test_results.add(_TestResult(test_id, target_word, False, e, [], []))

    summary = get_test_summary(intermediate_test_results)
    print_report(sorted(intermediate_test_results, key=lambda tr: tr.game_id), summary)
    assert_that(summary['failure_rate']).is_close_to(0, 0.01)


def simulate_game(game_id: int, target_word: str) -> _TestResult:
    predictor = analytics.Predictor()
    guesses = []
    responses = []

    while True:
        try:
            if predictor.round == 1:
                with shared_process_state[target_word].get_lock():
                    starting_words = set(get_used_starting_words(target_word))
                    while (guess := predictor.predict_wordle()[0]) in starting_words:
                        pass
                    starting_words.add(guess)
                    store_used_starting_words(target_word, starting_words)
            else:
                guess = predictor.predict_wordle()[0]

            response = mimic_game_response(guess, target_word)
            guesses.append(guess)
            responses.append(response)
            predictor.calibrate(guess, response)

        except analytics.Victory:
            return _TestResult(game_id, target_word, True, None, guesses, responses)
        except analytics.EndGameError:
            return _TestResult(game_id, target_word, False, None, guesses, responses)
        except BaseException as e:
            return _TestResult(game_id, target_word, False, e, guesses, responses)


def store_used_starting_words(key: str, strings: Iterable[str]) -> None:
    shared_process_state[key].value = b''
    for word in strings:
        shared_process_state[key].value += bytes(word, 'utf-8')


def get_used_starting_words(key: str, word_length: int = data.WORDLE_MAX_WORLD_LENGTH) -> Set[str]:
    return {
        shared_process_state[key].value[index:index + word_length].decode('utf-8')
        for index in range(0,
                           len(shared_process_state[key].value),
                           word_length)
    }


def mimic_game_response(guess: str, target: str) -> str:
    target_letters_counter = Counter(target)

    def responsecode(position: int, guess_letter: str, target_letter: str) -> str:
        result = ''
        if guess_letter == target_letter:
            result = 'c'
        elif guess_letter != target_letter and guess_letter not in target:
            result = 'w'
        elif guess_letter != target_letter and guess_letter in target_letters_counter:
            result = 'm'
        else:
            result = 'w'

        target_letters_counter[guess_letter] -= 1
        if target_letters_counter[guess_letter] <= 0:
            del target_letters_counter[guess_letter]
        return result

    return ''.join(responsecode(p, gl, target[p]) for p, gl in enumerate(guess))


def get_test_summary(test_results: Collection[_TestResult]) -> Dict[str, float]:
    return {
        'pass': (npass := sum(1 if r.success else 0 for r in test_results)),
        'fail': (nfail := len(test_results) - npass),
        'failure_rate': 100 * nfail / len(test_results),
        'average_round_length': mean(len(r.guesses) for r in test_results)
    }


def print_report(test_results: Collection[_TestResult], test_summary: Dict[str, float]) -> None:
    summary = Table('Pass', 'Fail', 'Failure Rate', 'Average Round Length', title='Summary')
    summary.add_row(*(str(v) for v in test_summary.values()))
    rich.print(summary)

    round_distribution = Table(*(f'{i + 1} Round' for i in range(6)), 'Did not Finish', title='Rounds Distribution')
    rounds_counter = Counter(len(r.guesses) for r in test_results)
    round_distribution.add_row(*(str(rounds_counter[i]) for i in range(1, 8)))
    rich.print(round_distribution)

    report = Table('Game #', 'Target Word', 'Rounds', 'Guesses', 'Responses', 'Result', show_lines=True)

    for r in sorted(test_results, key=lambda r: r.game_id):
        guess_grid = Table.grid()
        for g in r.guesses:
            guess_grid.add_row(g)

        response_grid = Table.grid()
        for re in r.responses:
            response_grid.add_row(re)

        result = 'Victory' if r.success else 'Did not Finish'
        if r.caught_error:
            result = f'Uncaught Exception: {r.caught_error}'

        report.add_row(str(r.game_id), r.target_word, str(len(r.guesses)), guess_grid, response_grid, result)

    rich.print(report)
