from model.ladder import Ladder 
from model.snake import Snake
from game_logic.snakeladdergame import SnakeLadderGame     


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
game = SnakeLadderGame(ladders, snakes, player_names, 'crooked')
game.play()