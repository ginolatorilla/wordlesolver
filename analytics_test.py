from statistics import mean
import pytest
from assertpy import assert_that
from pytest_mock import MockerFixture

import analytics

POSSIBLE_GAME_RESPONSES = {
    'all wrong': 'wwwww',
    'all correct': 'ccccc',
    'all misplaced': 'mmmmm',
    'some wrong': 'wcccc',
    'some correct': 'cwwww',
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
        assert_that(predictions).is_length(3)
        for word in predictions:
            assert_that(word).does_not_contain_duplicates()
            assert_that(WORDBANK[word]).is_greater_than_or_equal_to(MEAN_RANK)


@pytest.mark.parametrize(
    'game_response',
    (pytest.param(response,
                  id=name) for (name,
                                response) in POSSIBLE_GAME_RESPONSES.items())
)
def test_Predictor_calibrate_should_remove_guessed_word_from_its_wordbank(
    predictor: analytics.Predictor,
    game_response: str
) -> None:
    predictor.wordbank['cares'] = 999
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
    predictor.wordbank['caves'] = 999
    predictor.wordbank['cares'] = 998
    predictor.calibrate('cares', game_response)
    assert_that(predictor.wordbank).does_not_contain('cares')
    assert_that(predictor.wordbank).does_not_contain('caves')


WORDBANK = {
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
