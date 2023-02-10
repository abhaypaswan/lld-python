from model.board import Board
from model.dice import Dice
from model.player import Player
from model.ladder import Ladder 
from model.snake import Snake

# SnakeLadder class representing the complete game
class SnakeLadder:
    # Initialization method to create a board, dice, and player
    def __init__(self, ladders, snakes):
        self.board = Board(ladders, snakes)
        self.dice = Dice()
        self.player = Player(self.board)

    # Method to play the game
    def play(self):
        while not self.player.has_won():
            dice_roll = self.dice.roll()
            self.player.move(dice_roll)
        
        print("You won!")


"""
    Here is the sample inputs to create a board, if you want you can take these inputs from users.
"""
ladders = {1: Ladder(1, 38), 4: Ladder(4, 14), 9: Ladder(9, 31), 21: Ladder(21, 42), 28: Ladder(28, 84), 36: Ladder(36, 44), 51: Ladder(51, 67), 71: Ladder(71, 91), 80: Ladder(80, 100)}
snakes = {98: Snake(98, 78), 95: Snake(95, 75), 93: Snake(93, 73), 87: Snake(87, 24), 64: Snake(64, 60), 62: Snake(62, 19), 56: Snake(56, 53), 49: Snake(49, 11), 48: Snake(48, 26)}
max_position = 100 
start_position = 1
no_of_players = 2
no_of_dice = 1


# play the game
game = SnakeLadder(ladders, snakes)
game.play()