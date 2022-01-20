from textwrap import dedent

import pytest
from pytest_mock import MockerFixture
from assertpy import assert_that

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
    mocker.patch(
        'data.open',
        mocker.mock_open(
            read_data=dedent(
                '''\
                one's
                two
                three
                threê
                seven
                Thousand
                twelve
                '''
            )
        )
    )

    assert_that([word for word in data.read_wordle_dictionary()]).is_equal_to(['three', 'seven'])
