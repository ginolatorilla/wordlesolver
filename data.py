'''Functions for getting English words suitable for Wordle

Copyright (c) 2021 Gino Latorilla
'''
import logging
import string
from collections import Counter
from typing import Dict, Iterable, Iterator, List


def read_wamerican() -> Iterator[str]:
    with open(_PATH_TO_AMERICAN_ENGLISH_DICTIONARY) as fp:
        for line in fp:
            yield line.rstrip()


def read_wordle_dictionary() -> Iterator[str]:
    for word in read_wamerican():
        if len(word) == WORDLE_MAX_WORLD_LENGTH and word.isalpha() and word.islower() and word.isascii():
            yield word
        else:
            logging.debug(f'"{word}" is not a suitable word for Wordle, so I will drop it.')


def letter_frequency_distribution(iterable: Iterable[str], max_word_length: int) -> Dict[str, List[int]]:
    counter = Counter((letter, position) for word in iterable for position, letter in enumerate(word))

    distribution = {}  # type: Dict[str, List[int]]
    for letter in string.ascii_lowercase:
        distribution[letter] = [0] * max_word_length

    for (letter, position), count in counter.items():
        current = distribution[letter]
        update = [0] * max_word_length
        update[position] = count
        distribution[letter] = [i + j for i, j in zip(current, update)]

    return distribution


def rank_word_popularity(word: str, frequency_table: Dict[str, List[int]]) -> int:
    score = 0
    for position, letter in enumerate(word):
        letter_score = frequency_table[letter][position]
        score += max(1, letter_score)

    return score


WORDLE_MAX_WORLD_LENGTH = 5
_PATH_TO_AMERICAN_ENGLISH_DICTIONARY = '/usr/share/dict/american-english'
