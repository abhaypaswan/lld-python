from model.board import Board
from model.dice import Dice
from model.player import Player
from model.ladder import Ladder 
from model.snake import Snake

# SnakeLadder class representing the complete game
class SnakeLadder:
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
        


"""
   For the sake of simplicity and to focus more on Design Patterns, we have used sample input. 
   However, if you wish, you can modify the input and output format according to your requirements.
"""
num_players = int(input("How many players are playing? "))
player_names = []
for i in range(num_players):
    name = input("Enter player " + str(i+1) + " name: ")
    player_names.append(name)
print("\n")

# Assumption: Ladders and Snakes won't make a loop.
ladders = {
    1: Ladder(1, 38), 
    4: Ladder(4, 14), 
    9: Ladder(9, 31), 
    21: Ladder(21, 42), 
    28: Ladder(28, 84), 
    36: Ladder(36, 44), 
    51: Ladder(51, 67), 
    71: Ladder(71, 91), 
    80: Ladder(80, 100)
}
snakes = {
    98: Snake(98, 78), 
    95: Snake(95, 75), 
    93: Snake(93, 73), 
    87: Snake(87, 24), 
    64: Snake(64, 60), 
    62: Snake(62, 19), 
    56: Snake(56, 53), 
    49: Snake(49, 11), 
    48: Snake(48, 26)
}


# play the game
game = SnakeLadder(ladders, snakes, player_names, 'crooked')
game.play()