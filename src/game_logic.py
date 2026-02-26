"""
Contains blackjack specific classes for 
classic blackjack. The suit, amount of cards,
shuffle, deck and hand counting is done here.
"""
import random
from enum import Enum


class Suit(Enum):
    HEARTS = "H"
    DIAMONDS = "D"
    CLUBS = "C"
    SPADES = "S"


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
    
    def value(self):
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11
        else:
            return int(self.rank)
    
    def __str__(self):
        return f"{self.rank}{self.suit.value}"


class Deck:
    def __init__(self):
        self.cards = []
        self.build()
    
    def build(self):
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = [Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS, Suit.SPADES]
        self.cards = [Card(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(self.cards)
    
    def draw(self):
        if len(self.cards) == 0:
            self.build()
        return self.cards.pop()


class Hand:
    def __init__(self):
        self.cards = []
    
    def add_card(self, card):
        self.cards.append(card)
    
    def get_value(self):
        value = sum(card.value() for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == 'A')
        
        while value > 21 and aces:
            value -= 10
            aces -= 1
        
        return value
    
    def is_bust(self):
        return self.get_value() > 21
    
    def is_blackjack(self):
        return len(self.cards) == 2 and self.get_value() == 21
    
    def can_split(self):
        return len(self.cards) == 2 and self.cards[0].rank == self.cards[1].rank
    
    def clear(self):
        self.cards = []
