from statistics import mean

import pytest
from assertpy import assert_that
from pytest_mock import MockerFixture

import analytics

POSSIBLE_GAME_RESPONSES = {
    'all_wrong': 'wwwww',
    'all_correct': 'ccccc',
    'all_misplaced': 'mmmmm',
    'some_wrong': 'wcccc',
    'some_correct': 'cwwww',
    'mixed': 'wcmcw',
}


@pytest.fixture
def predictor(mocker: MockerFixture) -> analytics.Predictor:
    mocker.patch('data.read_wordle_dictionary', side_effect=WORDBANK.keys)
    mocker.patch('data.rank_word_popularity', side_effect=WORDBANK.get)
    mocker.patch('data.letter_frequency_distribution')
    return analytics.Predictor()


def test_Predictor_predict_wordle_should_give_random_popular_words_without_repeating_letters(
    predictor: analytics.Predictor,
    mocker: MockerFixture
) -> None:
    first_predictions = predictor.predict_wordle()
    second_predictions = predictor.predict_wordle()
    assert_that(first_predictions).is_not_equal_to(second_predictions)

    for predictions in (first_predictions, second_predictions):
        assert_that(predictions).is_length(predictor._output_size)
        for word in predictions:
            assert_that(word).does_not_contain_duplicates()
            assert_that(WORDBANK[word]).is_greater_than_or_equal_to(MEAN_RANK)


def test_Predictor_predict_wordle_should_give_random_popular_words_without_repeating_letters_if_previous_round_is_busted(
    predictor: analytics.Predictor,
    mocker: MockerFixture
) -> None:
    predictor.calibrate('infix', 'wwwww')
    prediction = predictor.predict_wordle()[0]
    assert_that(prediction).does_not_contain_duplicates()


@pytest.mark.parametrize(
    'game_response',
    (pytest.param(response,
                  id=name) for (name,
                                response) in POSSIBLE_GAME_RESPONSES.items() if name != 'all_correct')
)
def test_Predictor_calibrate_should_remove_guessed_word_from_its_wordbank(
    predictor: analytics.Predictor,
    game_response: str
) -> None:
    predictor.calibrate('cares', game_response)
    assert_that(predictor.wordbank).does_not_contain('cares')


@pytest.mark.parametrize(
    'game_response',
    (
        pytest.param(response,
                     id=name) for (name,
                                   response) in POSSIBLE_GAME_RESPONSES.items() if 'wrong' in name or name == 'mixed'
    )
)
def test_Predictor_calibrate_should_remove_words_with_wrong_letters_from_its_wordbank(
    predictor: analytics.Predictor,
    game_response: str
) -> None:
    predictor.calibrate('cares', game_response)
    assert_that(predictor.wordbank).does_not_contain('cares')
    assert_that(predictor.wordbank).does_not_contain('canes')


def test_Predictor_calibrate_should_remove_words_with_misplaced_letters(predictor: analytics.Predictor) -> None:
    predictor.calibrate('cases', 'mcccc')
    assert_that(predictor.wordbank).does_not_contain('cares')
    assert_that(predictor.wordbank).does_not_contain('canes')


def test_Predictor_calibrate_should_prioritise_words_with_correct_letters(predictor: analytics.Predictor) -> None:
    assert_that(predictor.round).is_equal_to(1)

    predictor.calibrate('harpy', 'cccww')
    predictions = predictor.predict_wordle()

    assert_that(predictor.round).is_equal_to(2)
    assert_that(predictions).starts_with('hares')


def test_Predictor_calibrate_should_prioritise_words_with_correct_and_misplaced_letters(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('soles', 'cmmcc')
    predictions = predictor.predict_wordle()

    assert_that(predictions).starts_with('sloes')


@pytest.mark.parametrize(
    'game_response',
    (
        pytest.param(response,
                     id=name) for (name,
                                   response) in {
                                       'empty': '',
                                       'short': 'ccc',
                                       'long': 'cccccc',
                                       'invalid letters': 'vwxyz'
                                   }.items()
    )
)
def test_Predictor_calibrate_should_raise_error_with_invalid_game_response(
    predictor: analytics.Predictor,
    game_response: str
) -> None:
    with pytest.raises(ValueError):
        predictor.calibrate('cares', game_response)


@pytest.mark.parametrize('guess', {'jacks', 'cover', 'proxy'})
def test_Predictor_calibrate_should_raise_error_with_unknown_guesswords(
    predictor: analytics.Predictor,
    guess: str
) -> None:
    with pytest.raises(ValueError):
        predictor.calibrate(guess, 'ccccw')


def test_Predictor_calibrate_should_raise_error_after_6th_round(predictor: analytics.Predictor) -> None:
    for _ in range(6):
        predictor.calibrate('soles', 'wwwww')
        predictor.wordbank['soles'] = 0

    with pytest.raises(analytics.EndGameError):
        predictor.calibrate('oxbow', 'ccccw')


def test_Predictor_calibrate_should_raise_victory_if_all_letters_are_correct(predictor: analytics.Predictor) -> None:
    with pytest.raises(analytics.Victory):
        predictor.calibrate('oxbow', 'ccccc')


def test_Predictor_calibrate_should_keep_words_with_correct_letters_if_a_repeat_is_in_wrong_position(
    predictor: analytics.Predictor
) -> None:
    predictor.wordbank = {
        'crick': 1,
        'prick': 2,
    }
    predictor.calibrate('crick', 'wcccc')
    assert_that(predictor.wordbank).contains('prick')


def test_Predictor_calibrate_should_prioritise_words_with_repeating_letters_less_often(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('bares', 'ccmcc')
    for prediction in predictor.predict_wordle():
        assert_that(prediction).does_not_contain_duplicates()


def test_Predictor_calibrate_should_drop_words_with_repeating_letters_if_one_is_correct_and_the_other_isnt(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('soles', 'wwwcc')

    for prediction in predictor.predict_wordle():
        assert_that(prediction).matches('^[^s][^o][^l]es$')


def test_Predictor_calibrate_should_discard_wrong_letter_if_its_correct_earlier(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('sades', 'ccwcw')
    assert_that(predictor.predict_wordle()).contains('saver')


def test_Predictor_calibrate_should_discard_wrong_letter_if_its_misplaced_earlier(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('sades', 'mcwcw')

    # Even if last 's' is "wrong", it can still satisfy the misplaced first 's'.
    # The game can respond like this because it sees the first occurence of 's' before its other
    # repetitions.
    assert_that(predictor.predict_wordle()).contains('cases')


def test_Predictor_calibrate_should_evict_misplaced_letter_if_it_becomes_correct(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('cares', 'mmmmm')
    predictor.calibrate('shake', 'cwcwc')

    assert_that(predictor.predict_wordle()).contains('scare')
    # TODO: discard words that do not have misplaced letters that may be correct
    # assert_that(predictor.predict_wordle()).does_not_contain('offal')


def test_Predictor_calibrate_should_predict_target_with_repeating_letters_if_it_is_often_correct(
    predictor: analytics.Predictor
) -> None:
    predictor.calibrate('saves', 'cwwcc')
    assert_that(predictor.predict_wordle()[0]).contains_duplicates()


WORDBANK = {
    'soles': 4155,
    'sades': 4045,
    'sages': 4025,
    'cares': 4017,
    'saves': 4003,
    'bares': 3990,
    'canes': 3972,
    'mares': 3876,
    'boles': 3869,
    'sises': 3863,
    'sloes': 3863,
    'rares': 3861,
    'fores': 3854,
    'pones': 3848,
    'tones': 3846,
    'wares': 3836,
    'hares': 3834,
    'cases': 3832,
    'manes': 3831,
    'poles': 3831,
    'bakes': 3695,
    'saver': 2780,
    'shake': 2061,
    'harpy': 1947,
    'scare': 1945,
    'offal': 583,
    'abuzz': 552,
    'affix': 523,
    'unzip': 499,
    'inbox': 498,
    'ethic': 479,
    'infix': 466,
    'oxbow': 428,
}

MEAN_RANK = int(mean(WORDBANK.values()))
