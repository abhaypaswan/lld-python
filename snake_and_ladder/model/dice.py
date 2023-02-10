import random

# Dice class representing a single dice with 6 sides
class Dice:
    # Method to roll the dice and return a random number between 1 and 6
    def roll(self):
        return random.randint(1, 6)