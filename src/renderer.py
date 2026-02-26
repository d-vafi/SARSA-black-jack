import pygame
from game_logic import Suit


class GameRenderer:
    def __init__(self, screen, fonts):
        self.screen = screen
        self.font_large = fonts['large']
        self.font_medium = fonts['medium']
        self.font_small = fonts['small']
    
    def draw_card(self, card, x, y, hidden=False):
        card_width = 70
        card_height = 100
        
        if hidden:
            pygame.draw.rect(self.screen, (0, 0, 128), (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(self.screen, (255, 255, 255), (x, y, card_width, card_height), 3, border_radius=5)
            
            for i in range(5):
                for j in range(7):
                    pygame.draw.circle(self.screen, (64, 64, 128), (x + 15 + i * 12, y + 15 + j * 12), 2)
        else:
            color = (255, 255, 255)
            pygame.draw.rect(self.screen, color, (x, y, card_width, card_height), border_radius=5)
            pygame.draw.rect(self.screen, (0, 0, 0), (x, y, card_width, card_height), 2, border_radius=5)
            
            text_color = (255, 0, 0) if card.suit in [Suit.HEARTS, Suit.DIAMONDS] else (0, 0, 0)
            
            rank_text = self.font_medium.render(card.rank, True, text_color)
            suit_text = self.font_large.render(card.suit.value, True, text_color)
            
            self.screen.blit(rank_text, (x + 5, y + 5))
            self.screen.blit(suit_text, (x + card_width // 2 - suit_text.get_width() // 2, 
                                         y + card_height // 2 - suit_text.get_height() // 2))
    
    def draw_hand(self, hand, x, y, hide_first=False):
        for i, card in enumerate(hand.cards):
            hidden = hide_first and i == 0
            self.draw_card(card, x + i * 80, y, hidden)
    
    def draw_header(self, width, budget, current_bet):
        title = self.font_large.render("Blackjack", True, (255, 255, 255))
        self.screen.blit(title, (width // 2 - title.get_width() // 2, 20))
        
        budget_text = self.font_large.render(f"${budget}", True, (255, 215, 0))
        self.screen.blit(budget_text, (width - budget_text.get_width() - 20, 20))
        
        bet_text = self.font_small.render(f"Bet: ${current_bet}", True, (255, 255, 255))
        self.screen.blit(bet_text, (width - bet_text.get_width() - 20, 70))
    
    def draw_stats(self, wins, losses, draws):
        stats_text = [
            f"Wins: {wins}  Losses: {losses}  Draws: {draws}",
            f"Total Games: {wins + losses + draws}"
        ]
        
        for i, text in enumerate(stats_text):
            stats_surface = self.font_small.render(text, True, (255, 255, 255))
            self.screen.blit(stats_surface, (20, 20 + i * 30))
    
    def draw_hand_info(self, label, count, x, y):
        label_surface = self.font_medium.render(label, True, (255, 255, 255))
        self.screen.blit(label_surface, (x, y))
        
        count_text = self.font_medium.render(f"Count: {count}", True, (255, 255, 255))
        self.screen.blit(count_text, (x, y + 40))
    
    def draw_hand_info_colored(self, label, count, x, y, color):
        label_surface = self.font_medium.render(label, True, color)
        self.screen.blit(label_surface, (x, y))
        
        count_text = self.font_medium.render(f"Count: {count}", True, color)
        self.screen.blit(count_text, (x, y + 40))
    
    def draw_hand_info_left(self, label, count, x, y, color):
        """Draw hand info to the left of cards (vertical stacked layout)"""
        label_surface = self.font_medium.render(label, True, color)
        self.screen.blit(label_surface, (x, y))
        
        count_text = self.font_medium.render("Count:", True, color)
        self.screen.blit(count_text, (x, y + 40))
        
        count_value = self.font_medium.render(f"{count}", True, color)
        self.screen.blit(count_value, (x + 20, y + 70))
    
    def draw_result_message(self, message, width):
        if message:
            result_color = (255, 215, 0) if "Win" in message else (255, 255, 255)
            result_surface = self.font_large.render(message, True, result_color)
            self.screen.blit(result_surface, (width // 2 - result_surface.get_width() // 2, 300))
