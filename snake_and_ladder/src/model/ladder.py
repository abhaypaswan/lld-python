# Ladder class representing a ladder on the board
class Ladder:
    # Initialization method with start and end positions of the ladder
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    # Method to return the end position of the ladder
    def get_end_position(self):
        print(f"(climbs a ladder from {self.start} to {self.end})")
        return self.end
