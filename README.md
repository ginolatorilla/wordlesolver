# Wordle Solver

Wordle Solver is a command-line app that helps you win a [Wordle](https://powerlanguage.co.uk/wordle) game.

## Installation

1. Make sure you have **Python 3.8** installed.
2. `pip install .`

## Quick Start

Just call `wordlesolver` and that's it:

```sh
wordlesolver
WordleSolver - Round 1 - ● ○ ○ ○ ○ ○
Here are my suggestions:
tares   lanes  mores

What was your guess? tares
What was the result? wcwww

WordleSolver - Round 2 - ● ● ○ ○ ○ ○
╭─────────────────╮
│  t  a  r  e  s  │
│                 │
│                 │
│                 │
│                 │
│                 │
╰─────────────────╯
Here are my suggestions:
daily   gaily  candy

What was your guess? 
```

The game will interactively ask you what word you guessed with, and how the game responded.

The response string is 5 letters long and consisting only of either *w*, *m*, or *c*.

- **w** means your letter is wrong and the game shows it in a grey background.
- **m** is for misplaced letters and has an orange background.
- **c** is for correct letters and has a green background.

## Limitations

*WordleSolver* will not guarantee to win you in 1 round. It has a 0.002% chance of giving you a first-round victory.
You have to be either incredibly lucky or smart to do better than that.

*WordleSolver* has a 34% chance of giving you a 4th round victory, and a 24% chance at the 5th.

*WordleSolver's* prediction algorithms is only **91.8% stable**. This means the program will either fail to give you a solution at the 6th round or there's still a corner case where it cannot make any more predictions
(especially if the Wordle has repeating letters).

There is no way to undo wrong inputs in the game; you just have to start all-over again.

## Testing

1. Make sure you have `pipenv` installed.
2. `./bootstrap.py` or `pipenv install --dev`
3. For unit tests: `pipenv run pytest --cov-report=html`
4. For stability tests (4 to 5 hours): `pipenv run pytest --runslow -s > stability_tests.txt`
