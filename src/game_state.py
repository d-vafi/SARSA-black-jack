from game_logic import Deck, Hand

"""
Contains classes for the game state. 
Winning, playing, dealing and betting are implemented here

"""
class GameState:
    def __init__(self, starting_budget=500, bet_amount=20):
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        
        self.wins = 0
        self.losses = 0
        self.draws = 0
        
        self.budget = starting_budget
        self.bet_amount = bet_amount
        self.current_bet = 0
        
        self.game_state = "betting"
        self.dealer_reveal = False
        self.result_message = ""
    
    def can_play(self):
        return self.budget >= self.bet_amount
    
    def place_bet(self):
        if not self.can_play():
            self.result_message = "Not enough money to play!"
            self.game_state = "game_over"
            return False
        
        self.budget -= self.bet_amount
        self.current_bet = self.bet_amount
        return True
    
    def deal_initial_hand(self):
        self.player_hand.clear()
        self.dealer_hand.clear()
        
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())
        self.player_hand.add_card(self.deck.draw())
        self.dealer_hand.add_card(self.deck.draw())
        
        self.game_state = "playing"
        self.dealer_reveal = False
        self.result_message = ""
    
    def player_hit(self):
        self.player_hand.add_card(self.deck.draw())
        
        if self.player_hand.is_bust():
            self.game_state = "game_over"
            self.dealer_reveal = True
            self.result_message = "BUST! Dealer Wins"
            self.losses += 1
            self.current_bet = 0
            return True
        return False
    
    def dealer_play(self):
        self.dealer_reveal = True
        
        while self.dealer_hand.get_value() < 17:
            self.dealer_hand.add_card(self.deck.draw())
    
    def determine_winner(self):
        player_value = self.player_hand.get_value()
        dealer_value = self.dealer_hand.get_value()
        
        if self.player_hand.is_blackjack() and not self.dealer_hand.is_blackjack():
            self.result_message = "BLACKJACK! You Win!"
            self.budget += self.current_bet + int(self.current_bet * 1.5)
            self.wins += 1
        elif self.dealer_hand.is_bust():
            self.result_message = "Dealer Busts! You Win!"
            self.budget += self.current_bet * 2
            self.wins += 1
        elif player_value > dealer_value:
            self.result_message = "You Win!"
            self.budget += self.current_bet * 2
            self.wins += 1
        elif player_value < dealer_value:
            self.result_message = "Dealer Wins!"
            self.losses += 1
        else:
            self.result_message = "Push (Draw)"
            self.budget += self.current_bet
            self.draws += 1
        
        self.current_bet = 0
        self.game_state = "game_over"
    
    def get_dealer_visible_value(self):
        if self.dealer_reveal:
            return self.dealer_hand.get_value()
        else:
            return self.dealer_hand.cards[1].value()
