'''Functions for getting English words suitable for Wordle

Copyright (c) 2021 Gino Latorilla
'''
from email.generator import Generator
import logging
from typing import Iterator


def read_wamerican() -> Iterator[str]:
    with open(_PATH_TO_AMERICAN_ENGLISH_DICTIONARY) as fp:
        for line in fp:
            yield line.rstrip()


def read_wordle_dictionary() -> Iterator[str]:
    for word in read_wamerican():
        if len(word) == 5 and word.isalpha() and word.islower():
            yield word
        else:
            logging.debug(f'"{word}" is not a suitable word for Wordle, so I will drop it.')


_PATH_TO_AMERICAN_ENGLISH_DICTIONARY = '/usr/share/dict/american-english'