import random

class DiceRollStrategy:
    def rollDice(self, strategy="fair"):
        if strategy == "fair":
            return FairDiceRollStrategy().rollDice()
        elif strategy == "crooked":
            return CrookedDiceRollStrategy().rollDice()
        else:
            raise ValueError(f'{strategy} is not a valid dice strategy')

class FairDiceRollStrategy(DiceRollStrategy):
    def rollDice(self):
        return random.randint(1, 6)

class CrookedDiceRollStrategy(DiceRollStrategy):
    def rollDice(self):
        p = random.random() 
        if(p <= 0.2): # this ensures that dice will have only 20% probability of generating an odd number.
            return random.choice([1, 3, 5])
        return random.randint(1, 3) * 2
