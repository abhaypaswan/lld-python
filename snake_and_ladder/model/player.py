# Player class representing a single player playing the game
class Player:
    # Initialization method with board and position attributes
    def __init__(self, board):
        self.board = board
        self.position = 0
    
    # Method to move the player based on the dice roll
    def move(self, dice_roll):
        self.position += dice_roll
        self.position = self.board.get_final_position(self.position)
        print(self.position)
    
    # Method to check if the player has won the game
    def has_won(self):
        return self.position >= 100