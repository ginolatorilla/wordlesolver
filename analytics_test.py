from statistics import mean
import pytest
from assertpy import assert_that
from pytest_mock import MockerFixture

import analytics


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


def test_Predictor_calibrate_should_remove_guessed_word_from_its_wordbank(
    predictor: analytics.Predictor,
    mocker: MockerFixture
) -> None:
    predictor.wordbank['cares'] = 999
    predictor.calibrate('cares', 'dont-care')
    assert_that(predictor.wordbank).does_not_contain('cares')


WORDBANK = {
    'sades': 4045,
    'sages': 4025,
    'cares': 4017,
    'saves': 4003,
    'bares': 3990,
    'canes': 3972,
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
