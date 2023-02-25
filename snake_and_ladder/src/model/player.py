# Player class representing a single player playing the game
class Player:
    # Initialization method with board and position attributes
    def __init__(self, board, name):
        self.board = board
        self.name = name
        self.position = 0
    
    # Method to move the player based on the dice roll
    def move(self, dice_roll):
        if self.position + dice_roll > 100:
            print("{self.name} cannot move beyond position 100. His turn is skipped.")
            return
        self.position += dice_roll
        self.position = self.board.get_final_position(self.position)
        print(f"{self.name} current position: {self.position}")
    
    # Method to check if the player has won the game
    def has_won(self):
        return self.position == 100