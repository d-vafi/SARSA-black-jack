"""
COMP 432 - Darren Vafi

Blackjack pygame , used for SARSA 
Reinforcement Learning (beeg gamba).
A player can either hit, stand, or split on
pairs. A dealer plays once the player makes all 
their moves. The win/loss count is shown above and 
digital currency is displayed, meant to replicate a real
life example.  

"""
import pygame
from game_state import GameState
from ui_components import Button
from renderer import GameRenderer


class BlackjackGame:
    def __init__(self):
        pygame.init()
        self.width = 1000
        self.height = 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Blackjack - SARSA Training")
        
        self.clock = pygame.time.Clock()
        fonts = {
            'large': pygame.font.Font(None, 48),
            'medium': pygame.font.Font(None, 36),
            'small': pygame.font.Font(None, 28)
        }
        
        self.state = GameState(starting_budget=500, bet_amount=20)
        self.renderer = GameRenderer(self.screen, fonts)
        
        self.setup_buttons()
        self.deal_initial_cards()
    
    def setup_buttons(self):
        button_y = 600
        button_width = 120
        button_height = 50
        button_spacing = 20
        
        start_x = (self.width - (3 * button_width + 2 * button_spacing)) // 2
        
        self.hit_button = Button(start_x, button_y, button_width, button_height, 
                                  "HIT", (34, 139, 34), (50, 205, 50))
        self.stand_button = Button(start_x + button_width + button_spacing, button_y, 
                                    button_width, button_height, 
                                    "STAND", (220, 20, 60), (255, 69, 0))
        self.split_button = Button(start_x + 2 * (button_width + button_spacing), button_y, 
                                    button_width, button_height, 
                                    "SPLIT", (65, 105, 225), (100, 149, 237))
        
        self.new_game_button = Button(self.width // 2 - 100, button_y, 200, button_height,
                                       "NEW GAME", (218, 165, 32), (255, 215, 0))
    
    def deal_initial_cards(self):
        if not self.state.place_bet():
            return
        
        self.state.deal_initial_hand()
        
        if self.state.player_hand.is_blackjack():
            self.stand()
    
    def hit(self):
        if self.state.game_state == "playing":
            self.state.player_hit()
    
    def stand(self):
        if self.state.game_state == "playing":
            self.state.dealer_play()
            self.state.determine_winner()
    
    def split(self):
        if self.state.game_state == "playing" and self.state.player_hand.can_split():
            self.state.result_message = "Split not fully implemented yet"
    
    def draw(self):
        self.screen.fill((0, 100, 0))
        
        self.renderer.draw_header(self.width, self.state.budget, self.state.current_bet)
        self.renderer.draw_stats(self.state.wins, self.state.losses, self.state.draws)
        
        dealer_value = self.state.get_dealer_visible_value()
        self.renderer.draw_hand_info("Dealer", dealer_value, 50, 100)
        self.renderer.draw_hand(self.state.dealer_hand, 50, 180, hide_first=not self.state.dealer_reveal)
        
        self.renderer.draw_hand_info("Player", self.state.player_hand.get_value(), 50, 350)
        self.renderer.draw_hand(self.state.player_hand, 50, 430)
        
        self.renderer.draw_result_message(self.state.result_message, self.width)
        
        if self.state.game_state == "playing":
            self.hit_button.draw(self.screen, self.renderer.font_medium)
            self.stand_button.draw(self.screen, self.renderer.font_medium)
            
            self.split_button.enabled = self.state.player_hand.can_split()
            self.split_button.draw(self.screen, self.renderer.font_medium)
        else:
            self.new_game_button.draw(self.screen, self.renderer.font_medium)
        
        pygame.display.flip()
    
    def handle_mouse_motion(self, pos):
        if self.state.game_state == "playing":
            self.hit_button.check_hover(pos)
            self.stand_button.check_hover(pos)
            self.split_button.check_hover(pos)
        else:
            self.new_game_button.check_hover(pos)
    
    def handle_mouse_click(self, pos):
        if self.state.game_state == "playing":
            self.handle_playing_click(pos)
        else:
            self.handle_game_over_click(pos)
    
    def handle_playing_click(self, pos):
        if self.hit_button.is_clicked(pos):
            self.hit()
        elif self.stand_button.is_clicked(pos):
            self.stand()
        elif self.split_button.is_clicked(pos):
            self.split()
    
    def handle_game_over_click(self, pos):
        if self.new_game_button.is_clicked(pos):
            self.deal_initial_cards()
    
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(pygame.mouse.get_pos())
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.handle_mouse_click(pygame.mouse.get_pos())
        
        return True
    
    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)
            
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()


if __name__ == "__main__":
    game = BlackjackGame()
    game.run()
