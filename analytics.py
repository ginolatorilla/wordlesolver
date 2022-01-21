'''Functions for providing you gameplay guidance in Wordle.

Copyright (c) 2021 Gino Latorilla
'''

from statistics import mean
from typing import List
import data
from itertools import tee, islice
from random import shuffle
import logging

log = logging.getLogger('wordlesolver')


class EndGameError(BaseException):
    pass


class Predictor:

    def __init__(self, output_size: int = 3) -> None:
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

        log.info(f'Wordbank prepared with {len(self.wordbank)} words.')

        self.round = 1
        self.highest_rank = max(self.wordbank.values())
        self.output_size = output_size

    def predict_wordle(self) -> List[str]:
        if self.round == 1:
            popularity_cutoff = int(mean(self.wordbank.values()))

            def unique_and_popular(word: str) -> bool:
                return len(word) == len(set(word)) and self.wordbank[word] >= popularity_cutoff

            top_50_results = [word for word in islice(filter(unique_and_popular, self.wordbank), 50)]
            shuffle(top_50_results)

            return top_50_results[:min(self.output_size, len(top_50_results))]
        else:
            return list(islice(self.wordbank, self.output_size))

    def calibrate(self, guess: str, game_response: str) -> None:
        if self.round > 6:
            raise EndGameError()

        if not all(letter in 'wmc' for letter in game_response):
            raise ValueError(f'{game_response=} must only contain "c", "m", or "w".')
        if len(game_response) != 5:
            raise ValueError(f'{game_response=} must be 5 characters long.')
        if guess not in self.wordbank:
            raise ValueError(f'{guess=} is not a valid English word.')

        wrong_letters = ''.join(set(letter for letter, state in zip(guess, game_response) if state == 'w'))
        misplaced_letters = {position: guess[position] for position, state in enumerate(game_response) if state == 'm'}
        correct_letters = {position: guess[position] for position, state in enumerate(game_response) if state == 'c'}

        def contains_wrong_letters(word: str) -> bool:
            return any(letter in word for letter in wrong_letters)

        def contains_misplaced_letters(word: str) -> bool:
            return any(word[position] == misplaced_letter for position, misplaced_letter in misplaced_letters.items())

        def promote_words_with_correct_letters(word: str, rank: int) -> int:
            bonus = sum(1 for position, correct_letter in correct_letters.items() if word[position] == correct_letter)
            bonus += sum(1 for letter in misplaced_letters.values() if letter in word)
            if bonus:
                return round(self.highest_rank + bonus*rank/10)
            else:
                return rank

        wordbank = {
            word: promote_words_with_correct_letters(word,
                                                     rank)
            for (word,
                 rank) in self.wordbank.items()
            if not (contains_wrong_letters(word) or contains_misplaced_letters(word) or guess == word)
        }

        self.wordbank = {word: rank for word, rank in sorted(wordbank.items(), key=lambda pair: pair[1], reverse=True)}
        self.highest_rank = max(self.wordbank.values())
        self.round += 1
