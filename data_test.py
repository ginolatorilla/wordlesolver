import string
from textwrap import dedent

from assertpy import assert_that
from pytest_mock import MockerFixture

import data


def test_read_english_dictionary_should_return_iterator_to_wamerican_package(mocker: MockerFixture) -> None:
    mocker.patch(
        'data.open',
        mocker.mock_open(read_data=dedent('''\
            one
            two
            three
            '''))
    )

    assert_that([word for word in data.read_wamerican()]).is_equal_to(['one', 'two', 'three'])


def test_read_wordle_dictionary_should_return_iterator_to_5_letter_english_words(mocker: MockerFixture) -> None:
    mocker.patch('data.open', mocker.mock_open(read_data=WORD_LIST))
    assert_that([word for word in data.read_wordle_dictionary()]).is_equal_to(['three', 'seven'])


def test_frequency_table_should_return_dict_of_letter_distribution_structs(mocker: MockerFixture) -> None:
    mocker.patch('data.open', mocker.mock_open(read_data=WORD_LIST))

    assert_that(data.letter_frequency_distribution(data.read_wordle_dictionary(),
                                                   data.WORDLE_MAX_WORLD_LENGTH)).is_equal_to(LETTER_FREQ_TABLE)


def test_rank_word_popularity_should_return_score_if_word_has_many_common_words() -> None:
    assert_that(data.rank_word_popularity('three', LETTER_FREQ_TABLE)).is_equal_to(1 + 1 + 1 + 2 + 1)
    assert_that(data.rank_word_popularity('vents', LETTER_FREQ_TABLE)).is_equal_to(1 + 1 + 1 + 1 + 1)


WORD_LIST = dedent('''\
    one's
    two
    three
    threê
    seven
    Thousand
    twelve
    ''')

# yapf: disable
LETTER_FREQ_TABLE = {
    **{letter: [0] * data.WORDLE_MAX_WORLD_LENGTH for letter in string.ascii_lowercase},
    **{
        'e': [0, 1, 0, 2, 1],
        'h': [0, 1, 0, 0, 0],
        'n': [0, 0, 0, 0, 1],
        'r': [0, 0, 1, 0, 0],
        's': [1, 0, 0, 0, 0],
        't': [1, 0, 0, 0, 0],
        'v': [0, 0, 1, 0, 0],
    }
}
# yapf: enable
