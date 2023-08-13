'''Functions for getting English words suitable for Wordle

Copyright (c) 2022 Gino Latorilla
'''
import string
from collections import Counter
from typing import Dict, Iterable, Iterator, List


def read_wamerican() -> Iterator[str]:
    '''Iterator over words in /usr/share/dict/american-english'''
    with open(_PATH_TO_AMERICAN_ENGLISH_DICTIONARY) as fp:
        for line in fp:
            yield line.rstrip()


def read_wordle_dictionary() -> Iterator[str]:
    '''Like data.read_wamerican(), but yields words suitable in Wordle.
    Such words are lowercase, non-name, and consists of letters from a to z.
    '''
    for word in read_wamerican():
        if len(word) == WORDLE_MAX_WORLD_LENGTH and word.isalpha() and word.islower() and word.isascii():
            yield word


def letter_frequency_distribution(iterable: Iterable[str], max_word_length: int) -> Dict[str, List[int]]:
    '''Calculates the letter frequency distribution across all words in an iterable.
    This assumes that you are providing an iterator of fixed-length words of length 'max_word_length'.

    Returns a dictionary with an alphabet letters as keys and a list of how often a letter appears as the 1st, 2nd,
    3rd, etc. For example, 's' appears as the last letter 1002 times among the given words:
    
        { 's': [ 992, 15, 654, 614, 1002], ... }
    '''
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
    '''Calculates how much a word contains frequently-appearing letters using information
    from data.letter_frequency_distribution(). Rankings may be used for sorting algorithms.

    For example, 'eerie', which contains a lot of frequently occuring 'e's, ranks higher than 'proxy'.

    Caveat emptor: this is a workaround for computing word popularity. Calculations by this function may not be a
    reliable substitute for word popularity, which varies across time and requires an online data source.
    '''
    score = 0
    for position, letter in enumerate(word):
        letter_score = frequency_table[letter][position]
        score += max(1, letter_score)

    return score


WORDLE_MAX_WORLD_LENGTH = 5
_PATH_TO_AMERICAN_ENGLISH_DICTIONARY = '/usr/share/dict/words'
