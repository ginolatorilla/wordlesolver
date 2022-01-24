from collections import Counter
from statistics import mean

import pytest
from assertpy import assert_that
from rich.console import Console
from rich.table import Table

import analytics

pytestmark = pytest.mark.slow


def test_stability() -> None:
    target = 'proxy'
    test_results = []
    trials = 100

    for i in range(trials):
        if i % 100 == 0:
            print()
        predictor = analytics.Predictor()
        guesses = []
        responses = []
        while True:
            try:
                guess = predictor.predict_wordle()[0]
                response = mimic_game_response(guess, target)
                guesses.append(guess)
                responses.append(response)
                predictor.calibrate(guess, response)
            except analytics.Victory:
                print('.', end='', flush=True)
                test_results.append({'guesses': guesses, 'responses': responses, 'result': 'pass'})
                break
            except analytics.EndGameError:
                print('x', end='', flush=True)
                test_results.append({'guesses': guesses, 'responses': responses, 'result': 'fail'})
                break
            except BaseException:
                print('!', end='', flush=True)
                test_results.append({'guesses': guesses, 'responses': responses, 'result': 'fail'})
                break
    print()

    console = Console()
    summary = Table('Pass', 'Fail', 'Failure Rate', 'Average Round Length', title='Summary')
    summary.add_row(
        str(passing := sum(r["result"] == "pass" for r in test_results)),
        str(failing := len(test_results) - passing),
        f'{(failure_rate := round(100 * failing / len(test_results), 2))}%',
        str(mean(len(r['guesses']) for r in test_results))
    )
    console.print(summary)

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
    rounds_counter = Counter(len(r['guesses']) for r in test_results)
    round_distribution.add_row(*(str(rounds_counter[i]) for i in range(1, 8)))
    console.print(round_distribution)

    failure_report = Table('#', 'Rounds', 'Guesses', 'Responses', title='Failed Games Report', show_lines=True)
    for i, r in enumerate(test_results):
        if r['result'] == 'pass':
            continue

        guess_grid = Table.grid()
        for g in r['guesses']:
            guess_grid.add_row(g)

        response_grid = Table.grid()
        for re in r['responses']:
            response_grid.add_row(re)

        failure_report.add_row(str(i + 1), str(len(r['guesses'])), guess_grid, response_grid)
    console.print(failure_report)

    assert_that(failure_rate).is_close_to(0, 0.01)


def mimic_game_response(guess: str, target: str) -> str:
    target_letters_counter = Counter(target)

    def responsecode(position: int, guess_letter: str, target_letter: str) -> str:
        if guess_letter == target_letter:
            return 'c'
        elif guess_letter != target_letter and guess_letter not in target:
            return 'w'
        elif guess_letter != target_letter and guess_letter in target_letters_counter:
            target_letters_counter[guess_letter] -= 1
            if target_letters_counter[guess_letter] <= 0:
                del target_letters_counter[guess_letter]
            return 'm'
        else:
            return 'w'

    return ''.join(responsecode(p, gl, target[p]) for p, gl in enumerate(guess))
