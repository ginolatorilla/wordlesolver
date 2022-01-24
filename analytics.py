'''Functions for providing you gameplay guidance in Wordle.

Copyright (c) 2021 Gino Latorilla
'''

import logging
from collections import defaultdict
from itertools import islice, tee
from random import shuffle
from statistics import mean
from typing import Dict, List, Set

import data

log = logging.getLogger('wordlesolver')


class EndGameError(BaseException):
    pass


class Victory(BaseException):
    pass


class Predictor:

    def __init__(self, output_size: int = 3) -> None:
        self._prepare_wordbank()

        self.round = 1
        self._highest_rank = max(self.wordbank.values())
        self._output_size = output_size
        self._previous_result = ''
        self._wrong_letters = defaultdict(set)  # type: Dict[str, Set[int]]
        self._misplaced_letters = defaultdict(set)  # type: Dict[str,Set[int]]
        self._correct_letters = defaultdict(set)  # type: Dict[str, Set[int]]

    def predict_wordle(self) -> List[str]:
        if self.round == 1 or self._previous_result == 'wwwww':
            popularity_cutoff = int(mean(self.wordbank.values()))

            def unique_and_popular(word: str) -> bool:
                return len(word) == len(set(word)) and self.wordbank[word] >= popularity_cutoff

            top_50_results = [word for word in islice(filter(unique_and_popular, self.wordbank), 50)]
            log.info('Here are the top 50 words for your first round:')
            log.info(' '.join(top_50_results))
            shuffle(top_50_results)

            return top_50_results[:min(self._output_size, len(top_50_results))]
        else:
            log.info('Here are the top 50 or so words for this round:')
            log.info(' '.join(islice(self.wordbank, 50)))

            return list(islice(self.wordbank, self._output_size))

    def calibrate(self, guess: str, game_response: str) -> None:
        self._screen_inputs(guess, game_response)
        self._parse_game_response(guess, game_response)

        self._reduce_wordbank(guess)
        self._promote_words()
        self._sort_words_by_highest_rank_first()
        self._refresh_current_game_state(game_response)

    def _prepare_wordbank(self) -> None:
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

    def _parse_game_response(self, guess: str, game_response: str) -> None:
        for position, state in enumerate(game_response):
            if state == 'w':
                self._wrong_letters[guess[position]].add(position)
            elif state == 'c':
                self._correct_letters[guess[position]].add(position)
            elif state == 'm':
                self._misplaced_letters[guess[position]].add(position)

    def _reduce_wordbank(self, guess: str) -> None:

        def _render_correct_letters() -> str:
            mask = ['_'] * 5
            for letter, positions in self._correct_letters.items():
                for position in positions:
                    mask[position] = letter
            return ''.join(mask)

        render_correct_letters = _render_correct_letters()
        render_wrong_letters = ', '.join(self._wrong_letters)

        def contains_wrong_letters(word: str) -> bool:
            rendered_word_with_mask = ''.join('_' if letter not in self._wrong_letters else letter for letter in word)

            if any(letter in word and letter not in self._correct_letters for letter in self._wrong_letters):
                log.debug(
                    f'ℹ️  {word} contains wrong letters, but some letters were identified as correct earlier (possibly repeating): {render_wrong_letters}.'
                )
                return True
            elif any(
                letter in self._wrong_letters and position in self._wrong_letters[letter] for position,
                letter in enumerate(word)
            ):
                log.debug(f'ℹ️  {word} contains wrong letters: {render_wrong_letters}.')
                return True
            else:
                log.debug(f'ℹ️  {word} does not have wrong letters: {rendered_word_with_mask}.')
                return False

        def contains_letters_in_positions_that_are_for_correct_ones(word: str) -> bool:
            if all(mask == '_' or letter == mask for letter, mask in zip(word, render_correct_letters)):
                log.debug(f'ℹ️  {word} contains all correct letters: {render_correct_letters}.')
                return True
            else:
                log.debug(f'ℹ️  {word} does not contain enough correct letters: {render_correct_letters}.')
                return False

        def contains_letters_in_misplaced_positions(word: str) -> bool:
            rendered_word_with_mask = ''.join('_' if l not in self._misplaced_letters else l for l in word)
            if any(
                letter in self._misplaced_letters and position in self._misplaced_letters[letter] for position,
                letter in enumerate(word)
            ):
                log.debug(f'ℹ️  {word} contains misplaced letters: {rendered_word_with_mask}.')
                return True
            else:
                log.debug(f'ℹ️  {word} does not have misplaced letters: {rendered_word_with_mask}.')
                return False

        def should_be_kept_for_the_next_round(word: str) -> bool:
            if word == guess:
                log.debug(f'🗑️  {word} is what you guessed with. Dropped')
                return False

            if contains_wrong_letters(word):
                log.debug(f'🗑️  {word}: Dropped')
                return False

            if self._correct_letters:
                if not contains_letters_in_positions_that_are_for_correct_ones(word):
                    log.debug(f'🗑️  {word}: Dropped')
                    return False

            if contains_letters_in_misplaced_positions(word):
                log.debug(f'🗑️  {word}: Dropped')
                return False

            log.debug(f'✔️  {word} looks good enough for the next round.')
            return True

        self.wordbank = {
            word: rank
            for (word,
                 rank) in self.wordbank.items() if should_be_kept_for_the_next_round(word)
        }

    def _promote_words(self) -> None:

        def promote_words_with_correct_letters(word: str, rank: int) -> int:
            bonus = sum(
                1 for position,
                letter in enumerate(word)
                if letter in self._correct_letters and position in self._correct_letters[letter]
            ) + sum(1 for letter in word if letter in self._misplaced_letters)

            if bonus:
                if len(word) > len(set(word)) and not any(letter in self._misplaced_letters for letter in word):
                    new_rank = round(self._highest_rank - bonus*rank/10)
                    log.debug(f'🥈 {word}: from {rank} → {new_rank} (has repeating letters)')
                else:
                    new_rank = round(self._highest_rank + bonus*rank/10)
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
        self._highest_rank = max(self.wordbank.values() or [0])
        self._previous_result = game_response
