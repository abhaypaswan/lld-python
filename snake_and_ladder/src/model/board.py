from model.ladder import Ladder 
from model.snake import Snake 

# Board class representing the game board with ladders and snakes
class Board:
    # Initialization method to create the ladders and snakes on the board
    def __init__(self, ladders, snakes):
        self.ladders = ladders
        self.snakes = snakes
    
    # Method to get the final position of the player after encountering ladders and snakes
    def get_final_position(self, position):
        if position in self.ladders:
            ladder = self.ladders[position]
            position = ladder.get_end_position()
        elif position in self.snakes:
            snake = self.snakes[position]
            position = snake.get_end_position()
        return position