'''Functions for providing you gameplay guidance in Wordle.

Copyright (c) 2021 Gino Latorilla
'''

from operator import contains
from statistics import mean
from typing import List
import data
from itertools import tee, islice
from random import shuffle
import re


class Predictor:

    def __init__(self) -> None:
        it1, it2, it3 = tee(data.read_wordle_dictionary(), 3)
        self.letter_frequency_distribution = data.letter_frequency_distribution(it1, data.WORDLE_MAX_WORLD_LENGTH)

        ranked_it = map(lambda word: data.rank_word_popularity(word, self.letter_frequency_distribution), it2)
        self.wordbank = {
            word: rank
            for word,
            rank in sorted(zip(it3,
                               ranked_it),
                           key=lambda pair: pair[1],
                           reverse=True)
        }

    def predict_wordle(self) -> List[str]:

        popularity_cutoff = int(mean(self.wordbank.values()))

        def unique_and_popular(word: str) -> bool:
            return len(word) == len(set(word)) and self.wordbank[word] >= popularity_cutoff

        top_50_results = [word for word in islice(filter(unique_and_popular, self.wordbank), 50)]
        shuffle(top_50_results)

        return top_50_results[:min(3, len(top_50_results))]

    def calibrate(self, guess: str, game_response: str) -> None:
        wrong_letters = ''.join(set(letter for letter, state in zip(guess, game_response) if state == 'w'))

        def contains_wrong_letters(word: str) -> bool:
            return any(letter in word for letter in wrong_letters)

        self.wordbank = {
            word: rank
            for word,
            rank in self.wordbank.items() if not (contains_wrong_letters(word) or guess == word)
        }
