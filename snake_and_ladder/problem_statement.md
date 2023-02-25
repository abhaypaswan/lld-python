# Snake and Ladder Low Level Design Problem

## Requirements

Design a Snake and Ladder game with the following requirements:

1. The board has a maximum position of 100.
2. The game can be played with either a fair dice or a crooked dice that favors generating even numbers over odd ones.
3. The number of players in the game should be decided by the user at the start of the game.
4. Snakes and Ladders should be randomly placed on the board.
5. Snakes and Ladders should not form a loop and the end point of a snake or ladder should not be the starting point for any other snake or ladder.

## Assumptions

1. The game is played by rolling a single dice.
2. If a player rolls a number that takes them beyond position 100, they do not move.
3. The game is played in turns, with players taking turns to roll the dice and move their pieces on the board.
4. Players must land exactly on position 100 to win the game.
5. The game does not have any special rules or power-ups beyond the basic rules of Snake and Ladder.

## Implementation

Design and implement the game using object-oriented programming principles and design patterns.


## Sample Input/Output
```sh
How many players are playing? 2
Enter player 1 name: Alice
Enter player 2 name: Bob


Alice's turn (rolling dice...)
Alice rolled 2
Alice current position: 2


Bob's turn (rolling dice...)
Bob rolled 4
(climbs a ladder from 4 to 14)
Bob current position: 14


Alice's turn (rolling dice...)
Alice rolled 3
Alice current position: 5


Bob's turn (rolling dice...)
Bob rolled 2
Bob current position: 16


Alice's turn (rolling dice...)
Alice rolled 4
(climbs a ladder from 9 to 31)
Alice current position: 31


Bob's turn (rolling dice...)
Bob rolled 5
(climbs a ladder from 21 to 42)
Bob current position: 42


Alice's turn (rolling dice...)
Alice rolled 2
Alice current position: 33


Bob's turn (rolling dice...)
Bob rolled 5
Bob current position: 47


Alice's turn (rolling dice...)
Alice rolled 3
(climbs a ladder from 36 to 44)
Alice current position: 44


Bob's turn (rolling dice...)
Bob rolled 1
(slides down a snake from 48 to 26)
Bob current position: 26


Alice's turn (rolling dice...)
Alice rolled 6
Alice current position: 50


Bob's turn (rolling dice...)
Bob rolled 6
Bob current position: 32


Alice's turn (rolling dice...)
Alice rolled 5
Alice current position: 55


Bob's turn (rolling dice...)
Bob rolled 1
Bob current position: 33


Alice's turn (rolling dice...)
Alice rolled 3
Alice current position: 58


Bob's turn (rolling dice...)
Bob rolled 1
Bob current position: 34


Alice's turn (rolling dice...)
Alice rolled 1
Alice current position: 59


Bob's turn (rolling dice...)
Bob rolled 4
Bob current position: 38


Alice's turn (rolling dice...)
Alice rolled 1
Alice current position: 60


Bob's turn (rolling dice...)
Bob rolled 5
Bob current position: 43


Alice's turn (rolling dice...)
Alice rolled 4
(slides down a snake from 64 to 60)
Alice current position: 60


Bob's turn (rolling dice...)
Bob rolled 3
Bob current position: 46


Alice's turn (rolling dice...)
Alice rolled 4
(slides down a snake from 64 to 60)
Alice current position: 60


Bob's turn (rolling dice...)
Bob rolled 5
(climbs a ladder from 51 to 67)
Bob current position: 67


Alice's turn (rolling dice...)
Alice rolled 1
Alice current position: 61


Bob's turn (rolling dice...)
Bob rolled 1
Bob current position: 68


Alice's turn (rolling dice...)
Alice rolled 5
Alice current position: 66


Bob's turn (rolling dice...)
Bob rolled 5
Bob current position: 73


Alice's turn (rolling dice...)
Alice rolled 1
Alice current position: 67


Bob's turn (rolling dice...)
Bob rolled 4
Bob current position: 77


Alice's turn (rolling dice...)
Alice rolled 1
Alice current position: 68


Bob's turn (rolling dice...)
Bob rolled 2
Bob current position: 79


Alice's turn (rolling dice...)
Alice rolled 6
Alice current position: 74


Bob's turn (rolling dice...)
Bob rolled 1
(climbs a ladder from 80 to 100)
Bob current position: 100


Player Bob has won the game!
```

## Running Instructions
To run the Snake and Ladder project, follow the below steps:
1. Open a terminal/command prompt.
2. Navigate to the project directory by running the following command:
```cd snake_and_ladder/src```
3. Run the following command to start the program:
```python3 main.py```