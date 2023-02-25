from model.board import Board
from model.dice import Dice
from model.player import Player

# SnakeLadder class representing the complete game
class SnakeLadderGame:
    # Initialization method to create a board, dice, and player
    def __init__(self, ladders, snakes, player_names, dice_strategy='fair', max_position=100, start_position=1):
        self.board = Board(ladders, snakes)
        self.dice = Dice(dice_strategy)
        self.players = []
        for player in player_names:
            self.players.append(Player(self.board, player))

    # Method to play the game
    def play(self):
        player_num = 0
        while 1:
            player = self.players[player_num]
            dice_roll = self.dice.roll()

            print(f"{player.name}'s turn (rolling dice...)")
            print(f"{player.name} rolled {dice_roll}")

            player.move(dice_roll)
            print('\n')

            if player.has_won():
                print(f'Player {player.name} has won the game!')
                return
            player_num += 1
            player_num = player_num % len(self.players)