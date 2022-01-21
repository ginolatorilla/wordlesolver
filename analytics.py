'''Functions for providing you gameplay guidance in Wordle.

Copyright (c) 2021 Gino Latorilla
'''

from calendar import c
import logging
from itertools import islice, tee
from random import shuffle
from statistics import mean
from typing import List, Dict

import data

log = logging.getLogger('wordlesolver')


class EndGameError(BaseException):
    pass


class Victory(BaseException):
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
        log.debug(f'word\trank')
        for word, rank in self.wordbank.items():
            log.debug(f'{word}\t{rank}')

        self.round = 1
        self.highest_rank = max(self.wordbank.values())
        self.output_size = output_size
        self.previous_result = ''

    def predict_wordle(self) -> List[str]:
        if self.round == 1 or self.previous_result == 'wwwww':
            popularity_cutoff = int(mean(self.wordbank.values()))

            def unique_and_popular(word: str) -> bool:
                return len(word) == len(set(word)) and self.wordbank[word] >= popularity_cutoff

            top_50_results = [word for word in islice(filter(unique_and_popular, self.wordbank), 50)]
            log.info('Here are the top 50 words for your first round:')
            log.info(' '.join(top_50_results))
            shuffle(top_50_results)

            return top_50_results[:min(self.output_size, len(top_50_results))]
        else:
            log.info('Here are the top 50 or so words for this round:')
            log.info(' '.join(islice(self.wordbank, 50)))

            return list(islice(self.wordbank, self.output_size))

    def calibrate(self, guess: str, game_response: str) -> None:
        self._screen_inputs(guess, game_response)

        misplaced_letters = {position: guess[position] for position, state in enumerate(game_response) if state == 'm'}
        correct_letters = {position: guess[position] for position, state in enumerate(game_response) if state == 'c'}
        wrong_letters = ''.join(
            set(
                letter for letter,
                state in zip(guess,
                             game_response) if state == 'w' and letter not in correct_letters.values()
            )
        )

        self._reduce_wordbank(wrong_letters, misplaced_letters, guess)
        self._promote_words(correct_letters, misplaced_letters)
        self._sort_words_by_highest_rank_first()
        self._refresh_current_game_state(game_response)

    def _screen_inputs(self, guess: str, game_response: str) -> None:
        if self.round > 6:
            raise EndGameError()

        if game_response == 'ccccc':
            raise Victory()

        if not all(letter in 'wmc' for letter in game_response):
            raise ValueError(f'Game response "{game_response}" must only contain "c", "m", or "w".')
        if len(game_response) != 5:
            raise ValueError(f'Game response "{game_response}" must be 5 characters long.')
        if guess not in self.wordbank:
            raise ValueError(f'Your guess "{guess}" is not a valid English word.')

    def _reduce_wordbank(self, wrong_letters: str, misplaced_letters: Dict[int, str], guess: str) -> None:

        def contains_wrong_letters(word: str) -> bool:
            if any(letter in word for letter in wrong_letters):
                log.debug(f'🗑️  {word} contains wrong letters {wrong_letters}. Dropped!')
                return True
            else:
                return False

        def contains_misplaced_letters(word: str) -> bool:
            if any(word[position] == misplaced_letter for position, misplaced_letter in misplaced_letters.items()):
                repr_misplaced_letters = ''.join(
                    l if p in misplaced_letters and l == guess[p] else '_' for p,
                    l in enumerate(word)
                )
                log.debug(f'🗑️  {word} has misplaced letters {repr_misplaced_letters}. Dropped!')

                return True
            else:
                return False

        self.wordbank = {
            word: rank
            for (word,
                 rank) in self.wordbank.items()
            if not (contains_wrong_letters(word) or contains_misplaced_letters(word) or guess == word)
        }

    def _promote_words(self, correct_letters: Dict[int, str], misplaced_letters: Dict[int, str]) -> None:

        def promote_words_with_correct_letters(word: str, rank: int) -> int:
            bonus = sum(1 for position,
                        correct_letter in correct_letters.items() if word[position] == correct_letter
                        ) + sum(1 for letter in misplaced_letters.values() if letter in word)

            if bonus:
                if len(word) > len(set(word)):
                    new_rank = round(self.highest_rank - bonus*rank/10)
                    log.debug(f'🥈 {word}: from {rank} → {new_rank} (has repeating letters)')
                else:
                    new_rank = round(self.highest_rank + bonus*rank/10)
                    log.debug(f'🥇 {word}: from {rank} → {new_rank}')
                return new_rank
            else:
                return rank

        for word in self.wordbank:
            self.wordbank[word] = promote_words_with_correct_letters(word, self.wordbank[word])

    def _sort_words_by_highest_rank_first(self) -> None:
        self.wordbank = {
            word: rank
            for word,
            rank in sorted(self.wordbank.items(),
                           key=lambda pair: pair[1],
                           reverse=True)
        }

    def _refresh_current_game_state(self, game_response: str) -> None:
        self.round += 1
        self.highest_rank = max(self.wordbank.values())
        self.previous_result = game_response
