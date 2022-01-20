'''This module has some stuff in it.
This module can do this and that, and many many more.
If you think there's no need to describe this in detail, just remove this line and the one before.

Copyright (c) 2021 Your Company's Name, or you
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


_PATH_TO_AMERICAN_ENGLISH_DICTIONARY = '/usr/share/dict/american-english'