import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from multiprocessing import Array
from statistics import mean
from typing import Any, Dict, Iterable

import pytest
import rich
from assertpy import assert_that
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

import analytics
import data

pytestmark = pytest.mark.slow
sample_size = 100
first_round_threshold = 50

shared_process_state = Array('c', first_round_threshold * data.WORDLE_MAX_WORLD_LENGTH)
error_console = Console(file=sys.stderr)
targets = list(data.read_wordle_dictionary())[:sample_size]

global_progress = Progress(console=error_console)
overall_progress_id = global_progress.add_task('[bold cyan]Progress', total=first_round_threshold * len(targets))
global_progress.start()


@pytest.fixture
def global_shared_state() -> None:
    shared_process_state.value = b''


@pytest.mark.parametrize('target_word', targets)
def test_stability(target_word: str, global_shared_state: Any) -> None:
    test_results = {}  # type: Dict[int, Dict[str, Any]]

    with ProcessPoolExecutor() as executor:
        futures_to_test_id = {executor.submit(run_test, target_word): i for i in range(1, first_round_threshold + 1)}

        for future in as_completed(futures_to_test_id):
            global_progress.advance(overall_progress_id)
            test_id = futures_to_test_id[future]
            try:
                test_results[test_id] = future.result(timeout=1)
            except TimeoutError as e:
                test_results[test_id] = {'result': f'Error: {e}'}

    summary = Table('Pass', 'Fail', 'Failure Rate', 'Average Round Length', title='Summary')
    summary.add_row(
        str(passing := sum(r["result"] == "pass" for r in test_results.values())),
        str(failing := len(test_results.values()) - passing),
        f'{(failure_rate := round(100 * failing / len(test_results.values()), 2))}%',
        str(mean(len(r['guesses']) for r in test_results.values()))
    )
    rich.print(summary)

    round_distribution = Table(
        '1 Round',
        '2 Rounds',
        '3 Rounds',
        '4 Rounds',
        '5 Rounds',
        '6 Rounds',
        'Did not Finish',
        title='Rounds Distribution'
    )
    rounds_counter = Counter(len(r['guesses']) for r in test_results.values())
    round_distribution.add_row(*(str(rounds_counter[i]) for i in range(1, 8)))
    rich.print(round_distribution)

    report = Table(
        '#',
        'Rounds',
        'Guesses',
        'Responses',
        'Result',
        show_lines=True,
        title=f'Test Results for "{target_word}"'
    )
    for i, r in sorted(test_results.items()):
        guess_grid = Table.grid()
        for g in r['guesses']:
            guess_grid.add_row(g)

        response_grid = Table.grid()
        for re in r['responses']:
            response_grid.add_row(re)

        if r['result'] == 'pass':
            result = 'Victory'
        elif r['result'] == 'fail':
            result = 'Did not Finish'
        else:
            result = r['result']

        report.add_row(str(i), str(len(r['guesses'])), guess_grid, response_grid, result)
    rich.print(report)

    assert_that(failure_rate).is_close_to(0, 0.01)


def run_test(target: str) -> Dict[str, Any]:
    predictor = analytics.Predictor()
    guesses = []
    responses = []

    def encode_strings_to_shared_array(strings: Iterable[str]) -> None:
        shared_process_state.value = b''
        for word in strings:
            shared_process_state.value += bytes(word, 'utf-8')

    def decode_strings_from_shared_array(word_length: int = data.WORDLE_MAX_WORLD_LENGTH) -> Iterable[str]:
        return [
            shared_process_state.value[index:index + word_length].decode('utf-8')
            for index in range(0,
                               len(shared_process_state.value),
                               word_length)
        ]

    while True:
        try:
            if predictor.round == 1:
                with shared_process_state.get_lock():
                    starting_words = set(decode_strings_from_shared_array())
                    while (guess := predictor.predict_wordle()[0]) in starting_words:
                        # rich.print(f'Drop [red]{guess}[/]; already used by another game.')
                        pass
                    starting_words.add(guess)
                    encode_strings_to_shared_array(starting_words)
            else:
                guess = predictor.predict_wordle()[0]
            response = mimic_game_response(guess, target)
            guesses.append(guess)
            responses.append(response)
            predictor.calibrate(guess, response)
        except analytics.Victory:
            return {'guesses': guesses, 'responses': responses, 'result': 'pass'}
        except analytics.EndGameError:
            return {'guesses': guesses, 'responses': responses, 'result': 'fail'}
        except BaseException as e:
            return {'guesses': guesses, 'responses': responses, 'result': f'Error: {e}'}


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
