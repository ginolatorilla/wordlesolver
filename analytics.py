'''Functions for providing you gameplay guidance in Wordle.

Copyright (c) 2021 Gino Latorilla
'''

import logging
from collections import defaultdict, Counter
from itertools import islice, tee
from random import shuffle
from statistics import mean
from typing import Dict, List, Set, Pattern
import re

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
        self._target_word_has_repeating_letters = False
        self._wrong_letters = defaultdict(set)  # type: Dict[str, Set[int]]
        self._misplaced_letters = defaultdict(set)  # type: Dict[str,Set[int]]
        self._correct_letters = defaultdict(set)  # type: Dict[str, Set[int]]
        self._unique_letters = set()  # type: Set[str]

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
        self._predict_if_target_has_repeating_letters()

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
            letter = guess[position]

            if state == 'w':
                if letter in self._correct_letters:
                    log.debug(f'Repeat letter {letter} attempted but it only appears once in the target.')
                    self._unique_letters.add(letter)
                elif letter in self._misplaced_letters:
                    log.debug(f'Letter {letter} is already misplaced.')
                else:
                    self._wrong_letters[letter].add(position)

            elif state == 'c':
                if letter in self._wrong_letters:
                    log.debug(f'Removing wrong letter {letter} because we found it to be actually correct.')
                    del self._wrong_letters[letter]

                if letter in self._misplaced_letters:
                    log.debug(f'Removing {letter} from set of misplaced letters.')
                    del self._misplaced_letters[letter]

                self._correct_letters[letter].add(position)

            elif state == 'm':
                self._misplaced_letters[letter].add(position)

    def _predict_if_target_has_repeating_letters(self) -> bool:
        occurrence_counter = Counter({letter: len(indexes) for letter, indexes in self._correct_letters.items()})

        repeaters = [letter for letter, count in occurrence_counter.items() if count > 1]
        if repeaters:
            log.debug(f'Target word has repeating letters: {"".join(repeaters)}.')

        return bool(repeaters)

    def _reduce_wordbank(self, guess: str) -> None:

        def should_keep_word_for_the_next_round(word: str) -> bool:
            if word == guess:
                log.debug(f'🗑️ {word} is what you guessed with.')
                return False

            if self._target_word_has_repeating_letters:
                if not has_repeating_letters(word):
                    log.debug(f'🗑️ {word} does not have repeating letters.')
                    return False

            if has_repeating_letters_that_should_be_unique(word):
                log.debug(f'🗑️ {word} has repeating letters that should be unique: {", ".join(self._unique_letters)}')
                return False

            if self._wrong_letters:
                if has_wrong_letters(word):
                    log.debug(f'🗑️ {word} has wrong letters: {", ".join(self._wrong_letters)}.')
                    return False

            if self._correct_letters:
                if not has_all_correct_letters(word):
                    log.debug(
                        f'🗑️ {word} does not have all correct letters: {match_all_correct_letters.pattern[1:-1].replace(".", "_")}.'
                    )
                    return False

            if self._misplaced_letters:
                if has_any_misplaced_letters(word):
                    log.debug(f'🗑️ {word} has misplaced letters: {", ".join(self._misplaced_letters)}.')
                    return False

            log.debug(f'✔️ {word} looks good enough for the next round.')
            return True

        def has_repeating_letters(word: str) -> bool:
            if are_all_letters_unique := len(word) == len(set(word)):
                log.debug(f'{word} has unique letters.')
            else:
                count_letters = Counter(word)
                log.debug(
                    f'{word} has repeating letters: {", ".join(letter for letter, count in count_letters.items() if count > 1)}.'
                )

            return not are_all_letters_unique

        def has_repeating_letters_that_should_be_unique(word: str) -> bool:
            return any(word.count(letter) > 1 for letter in self._unique_letters)

        def has_wrong_letters(word: str) -> bool:
            return bool(set(self._wrong_letters).intersection(set(word)))

        def recompile_correct_letters_regex() -> Pattern[str]:
            pattern = ['.'] * 5

            for correct_letter, indexes in self._correct_letters.items():
                for i in indexes:
                    pattern[i] = correct_letter

            return re.compile(f'^{"".join(pattern)}$')

        match_all_correct_letters = recompile_correct_letters_regex()

        def has_all_correct_letters(word: str) -> bool:
            return match_all_correct_letters.match(word) is not None

        def recompile_misplaced_letters_regex() -> Pattern[str]:
            reverse_dict = defaultdict(set)  # type: Dict[int, Set[str]]

            for misplaced_letter, indexes in self._misplaced_letters.items():
                for i in indexes:
                    reverse_dict[i].add(misplaced_letter)

            pattern = set()  # type: Set[str]

            for index, misplaced_letters in reverse_dict.items():
                subpattern = ['.'] * 5
                subpattern[index] = f'[{"".join(misplaced_letters)}]'
                pattern.add(''.join(subpattern))

            return re.compile(f'^{"|".join(pattern)}$')

        match_any_misplaced_letter = recompile_misplaced_letters_regex()

        def has_any_misplaced_letters(word: str) -> bool:
            return match_any_misplaced_letter.match(word) is not None

        self.wordbank = {
            word: rank
            for (word,
                 rank) in self.wordbank.items() if should_keep_word_for_the_next_round(word)
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
