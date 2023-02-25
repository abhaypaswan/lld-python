from game_logic.dice_strategy import DiceRollStrategy

import random

# Dice class representing a single dice with 6 sides
class Dice:
    def __init__(self, strategy='fair'):
        # Default strategy is fair
        self.strategy = strategy
   
    # Method to roll the dice and return a random number between 1 and 6
    def roll(self):
        return DiceRollStrategy().rollDice(self.strategy)