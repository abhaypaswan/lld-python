# Snake class representing a snake on the board
class Snake:
    # Initialization method with start and end positions of the snake
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    # Method to return the end position of the snake
    def get_end_position(self):
        print(f"(slides down a snake from {self.start} to {self.end})")
        return self.end