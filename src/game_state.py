from game_logic import Deck, Hand
from logger_config import get_logger

"""
Contains classes for the game state. 
Winning, playing, dealing and betting are implemented here

"""
class GameState:
    def __init__(self, starting_budget=500, bet_amount=20):
        self.deck = Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()
        
        # Split hands support
        self.is_split = False
        self.split_hands = []  # List of hands when split
        self.current_hand_index = 0
        self.split_bets = []  # Bet for each split hand
        
        self.wins = 0
        self.losses = 0
        self.draws = 0
        
        self.budget = starting_budget
        self.bet_amount = bet_amount
        self.current_bet = 0
        
        self.game_state = "betting"
        self.dealer_reveal = False
        self.result_message = ""
        self.logger = get_logger("game_state")
    
    def can_play(self):
        return self.budget >= self.bet_amount
    
    def can_split(self):
        # Check if player has enough budget to double the bet for split
        return self.budget >= self.bet_amount
    
    def place_bet(self):
        if not self.can_play():
            self.result_message = "Not enough money to play!"
            # Don't set to broke here - let game logic handle it
            self.logger.info(f"[BET] Cannot place bet - Budget: ${self.budget}, Required: ${self.bet_amount}")
            return False
        
        self.budget -= self.bet_amount
        self.current_bet = self.bet_amount
        self.logger.info(f"[BET] Bet placed: ${self.current_bet} | Remaining budget: ${self.budget}")
        return True
    
    def deal_initial_hand(self):
        self.player_hand.clear()
        self.dealer_hand.clear()
        self.is_split = False
        self.split_hands = []
        self.current_hand_index = 0
        self.split_bets = []
        
        card1 = self.deck.draw()
        self.player_hand.add_card(card1)
        card2 = self.deck.draw()
        self.dealer_hand.add_card(card2)
        card3 = self.deck.draw()
        self.player_hand.add_card(card3)
        card4 = self.deck.draw()
        self.dealer_hand.add_card(card4)
        
        self.logger.info(f"[DEAL] Player cards: {card1}, {card3} | Value: {self.player_hand.get_value()}")
        self.logger.info(f"[DEAL] Dealer shows: {card4} | Hidden card: [?]")
        
        self.game_state = "playing"
        self.dealer_reveal = False
        self.result_message = ""
    
    def player_hit(self):
        if self.is_split:
            active_hand = self.split_hands[self.current_hand_index]
            hand_label = f"Hand {self.current_hand_index + 1}"
        else:
            active_hand = self.player_hand
            hand_label = "Player"
        
        card = self.deck.draw()
        active_hand.add_card(card)
        hand_value = active_hand.get_value()
        self.logger.info(f"[{hand_label.upper()}] Drew: {card} | New value: {hand_value}")
        
        if active_hand.is_bust():
            self.logger.info(f"[BUST] {hand_label} busted with {hand_value}!")
            
            if self.is_split:
                # Move to next hand or end if this was the last hand
                if self.current_hand_index < len(self.split_hands) - 1:
                    self.current_hand_index += 1
                    self.logger.info(f"[SPLIT] Moving to Hand {self.current_hand_index + 1}")
                    return False
                else:
                    # All hands played, dealer plays
                    return True
            else:
                # Single hand bust
                self.game_state = "game_over"
                self.dealer_reveal = True
                self.result_message = "BUST! Dealer Wins"
                self.losses += 1
                self.logger.info(f"[RESULT] Dealer Wins | Budget: ${self.budget} | W/L/D: {self.wins}/{self.losses}/{self.draws}")
                self.current_bet = 0
                return True
        
        # Check if hand reached 21
        if hand_value == 21:
            self.logger.info(f"[{hand_label.upper()}] Reached 21!")
            if self.is_split:
                if self.current_hand_index < len(self.split_hands) - 1:
                    # Auto-stand and move to next hand
                    self.current_hand_index += 1
                    self.logger.info(f"[SPLIT] Moving to Hand {self.current_hand_index + 1}")
                    return False
                else:
                    # Last hand reached 21 - all hands complete
                    return True
        
        return False
    
    def split_hand(self):
        if not self.player_hand.can_split() or not self.can_split():
            return False
        
        self.logger.info(f"[SPLIT] Splitting pair of {self.player_hand.cards[0].rank}")
        
        # Deduct additional bet
        self.budget -= self.bet_amount
        self.logger.info(f"[SPLIT] Additional bet placed: ${self.bet_amount} | Remaining budget: ${self.budget}")
        
        # Create two hands from the split
        hand1 = Hand()
        hand2 = Hand()
        hand1.add_card(self.player_hand.cards[0])
        hand2.add_card(self.player_hand.cards[1])
        
        # Deal one card to each hand
        card1 = self.deck.draw()
        hand1.add_card(card1)
        card2 = self.deck.draw()
        hand2.add_card(card2)
        
        self.split_hands = [hand1, hand2]
        self.split_bets = [self.bet_amount, self.bet_amount]
        self.current_hand_index = 0
        self.is_split = True
        self.current_bet = self.bet_amount * 2  # Total bet is doubled
        
        self.logger.info(f"[SPLIT] Hand 1: {hand1.cards[0]}, {card1} | Value: {hand1.get_value()}")
        self.logger.info(f"[SPLIT] Hand 2: {hand2.cards[0]}, {card2} | Value: {hand2.get_value()}")
        self.logger.info("[SPLIT] Now playing Hand 1")
        
        return True
    
    def dealer_play(self):
        self.dealer_reveal = True
        dealer_value = self.dealer_hand.get_value()
        self.logger.info(f"[DEALER] Reveals hand | Value: {dealer_value}")
        
        while self.dealer_hand.get_value() < 17:
            card = self.deck.draw()
            self.dealer_hand.add_card(card)
            dealer_value = self.dealer_hand.get_value()
            self.logger.info(f"[DEALER] Drew: {card} | New value: {dealer_value}")
    
    def determine_winner(self):
        dealer_value = self.dealer_hand.get_value()
        
        if self.is_split:
            # Handle each split hand independently
            self.logger.info(f"[SHOWDOWN] Dealer: {dealer_value}")
            results = []
            total_payout = 0
            
            for i, hand in enumerate(self.split_hands):
                hand_value = hand.get_value()
                bet = self.split_bets[i]
                self.logger.info(f"[SHOWDOWN] Hand {i + 1}: {hand_value} vs Dealer: {dealer_value}")
                
                if hand.is_bust():
                    results.append(f"Hand {i + 1}: BUST")
                    self.losses += 1
                    self.logger.info(f"[RESULT] Hand {i + 1} BUSTED | Lost ${bet}")
                elif self.dealer_hand.is_bust():
                    results.append(f"Hand {i + 1}: WIN")
                    payout = bet * 2
                    total_payout += payout
                    self.wins += 1
                    self.logger.info(f"[RESULT] Hand {i + 1} Wins (Dealer Bust) | Won ${payout}")
                elif hand_value > dealer_value:
                    results.append(f"Hand {i + 1}: WIN")
                    payout = bet * 2
                    total_payout += payout
                    self.wins += 1
                    self.logger.info(f"[RESULT] Hand {i + 1} Wins | Won ${payout}")
                elif hand_value < dealer_value:
                    results.append(f"Hand {i + 1}: LOSE")
                    self.losses += 1
                    self.logger.info(f"[RESULT] Hand {i + 1} Loses | Lost ${bet}")
                else:
                    results.append(f"Hand {i + 1}: PUSH")
                    total_payout += bet
                    self.draws += 1
                    self.logger.info(f"[RESULT] Hand {i + 1} Push | Returned ${bet}")
            
            self.budget += total_payout
            self.result_message = " | ".join(results)
            self.logger.info(f"[TOTAL PAYOUT] ${total_payout}")
        else:
            # Single hand
            player_value = self.player_hand.get_value()
            self.logger.info(f"[SHOWDOWN] Player: {player_value} vs Dealer: {dealer_value}")
            
            if self.player_hand.is_blackjack() and not self.dealer_hand.is_blackjack():
                self.result_message = "BLACKJACK! You Win!"
                winnings = self.current_bet + int(self.current_bet * 1.5)
                self.budget += winnings
                self.wins += 1
                self.logger.info(f"[RESULT] BLACKJACK! Player Wins ${winnings}")
            elif self.dealer_hand.is_bust():
                self.result_message = "Dealer Busts! You Win!"
                winnings = self.current_bet * 2
                self.budget += winnings
                self.wins += 1
                self.logger.info(f"[RESULT] Dealer Busts! Player Wins ${winnings}")
            elif player_value > dealer_value:
                self.result_message = "You Win!"
                winnings = self.current_bet * 2
                self.budget += winnings
                self.wins += 1
                self.logger.info(f"[RESULT] Player Wins ${winnings}")
            elif player_value < dealer_value:
                self.result_message = "Dealer Wins!"
                self.losses += 1
                self.logger.info(f"[RESULT] Dealer Wins | Player loses ${self.current_bet}")
            else:
                self.result_message = "Push (Draw)"
                self.budget += self.current_bet
                self.draws += 1
                self.logger.info(f"[RESULT] Push (Draw) | Bet returned: ${self.current_bet}")
        
        self.logger.info(f"[STATS] Budget: ${self.budget} | W/L/D: {self.wins}/{self.losses}/{self.draws}")
        self.logger.info("=" * 60)
        
        self.current_bet = 0
        self.game_state = "game_over"
    
    def get_dealer_visible_value(self):
        if self.dealer_reveal:
            return self.dealer_hand.get_value()
        else:
            return self.dealer_hand.cards[1].value()
