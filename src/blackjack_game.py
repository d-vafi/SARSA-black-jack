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
from logger_config import get_logger


class BlackjackGame:
    # screen resolution, pixels
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 720


    def __init__(self):
        pygame.init()
        self.logger = get_logger("blackjack_game")
        self.logger.info("=" * 60)
        self.logger.info("[INIT] Initializing Blackjack Game")
        self.width = self.SCREEN_WIDTH
        self.normal_height = self.SCREEN_HEIGHT
        self.height = self.normal_height
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Blackjack - SARSA Training")
        self.logger.info(f"[INIT] Game window created ({self.width}x{self.height})")
        
        self.clock = pygame.time.Clock()
        fonts = {
            'large': pygame.font.Font(None, 48),
            'medium': pygame.font.Font(None, 36),
            'small': pygame.font.Font(None, 28)
        }
        
        self.state = GameState(starting_budget=500, bet_amount=20)
        self.renderer = GameRenderer(self.screen, fonts)
        self.logger.info(f"[INIT] Starting budget: ${self.state.budget}, Bet amount: ${self.state.bet_amount}")
        self.logger.info("[INIT] Select your bet amount and click 'START ROUND' to begin")
        
        # Bet amount buttons
        self.bet_amounts = [10, 20, 50, 100, 200]
        self.bet_buttons = []
        self.setup_bet_buttons()
        
        self.setup_buttons()
        # Don't auto-deal - let player choose bet first
    
    def setup_buttons(self):
        self.button_width = 120
        self.button_height = 50
        self.button_spacing = 20
        self.update_button_positions()
    
    # buttons appear in top right, greyed out if player cant 
    # afford the bet, gold otherwise
    def setup_bet_buttons(self):
        bet_button_width = 60
        bet_button_height = 35
        bet_button_spacing = 5
        start_x = self.width - (len(self.bet_amounts) * (bet_button_width + bet_button_spacing)) - 10
        start_y = 120
        
        for i, amount in enumerate(self.bet_amounts):
            x = start_x + i * (bet_button_width + bet_button_spacing)
            
            is_affordable = self.state.budget >= amount
            
            if amount == self.state.bet_amount and is_affordable:
                color = (255, 215, 0) 
                hover_color = (255, 235, 50)
            elif is_affordable:
                color = (70, 70, 70)
                hover_color = (100, 100, 100)
            else:
                color = (40, 40, 40)
                hover_color = (40, 40, 40)
            
            button = Button(x, start_y, bet_button_width, bet_button_height,
                          f"${amount}", color, hover_color)
            button.enabled = is_affordable
            self.bet_buttons.append(button)
    
    def update_button_positions(self):
        button_y = self.height - 100
        start_x = (self.width - (3 * self.button_width + 2 * self.button_spacing)) // 2
        
        self.hit_button = Button(start_x, button_y, self.button_width, self.button_height, 
                                  "HIT", (34, 139, 34), (50, 205, 50))
        self.stand_button = Button(start_x + self.button_width + self.button_spacing, button_y, 
                                    self.button_width, self.button_height, 
                                    "STAND", (220, 20, 60), (255, 69, 0))
        self.split_button = Button(start_x + 2 * (self.button_width + self.button_spacing), button_y, 
                                    self.button_width, self.button_height, 
                                    "SPLIT", (65, 105, 225), (100, 149, 237))
        
        # Change button text based on game state
        button_text = "START ROUND" if self.state.game_state == "betting" else "NEW GAME"
        self.new_game_button = Button(self.width // 2 - 100, button_y, 200, self.button_height,
                                       button_text, (218, 165, 32), (255, 215, 0))
        
        # Game over screen buttons
        center_x = self.width // 2
        center_y = self.height // 2
        self.quit_button = Button(center_x - 220, center_y + 100, 200, self.button_height,
                                   "QUIT", (139, 0, 0), (220, 20, 60))
        self.restart_button = Button(center_x + 20, center_y + 100, 200, self.button_height,
                                      "NEW BUDGET", (34, 139, 34), (50, 205, 50))
    

    
    def deal_initial_cards(self):
        self.logger.info("=" * 60)
        self.logger.info("[GAME] Starting new round")
        
        # Check if player can afford any bet
        min_bet = min(self.bet_amounts)
        if self.state.budget < min_bet:
            self.logger.info(f"[ERROR] Cannot afford any bet - Budget: ${self.state.budget}, Minimum bet: ${min_bet}")
            self.state.game_state = "broke"
            return
        
        # Auto-adjust bet if current bet is too high
        if self.state.budget < self.state.bet_amount:
            old_bet = self.state.bet_amount
            # Find largest affordable bet
            for amount in reversed(self.bet_amounts):
                if self.state.budget >= amount:
                    self.state.bet_amount = amount
                    break
            self.logger.info(f"[BET] Auto-adjusted bet from ${old_bet} to ${self.state.bet_amount} (insufficient funds)")
            # Update buttons to reflect new bet
            self.bet_buttons.clear()
            self.setup_bet_buttons()
        
        if not self.state.place_bet():
            self.logger.info("[ERROR] Cannot place bet - insufficient funds")
            self.state.game_state = "broke"
            return
        
        self.state.deal_initial_hand()
        
        # Update button text after dealing
        self.update_button_positions()
        
        if self.state.player_hand.is_blackjack():
            self.logger.info("[EVENT] Player has BLACKJACK!")
            self.stand()
    
    def hit(self):
        if self.state.game_state == "playing":
            # Check if current hand is already busted/21
            if self.state.is_split:
                current_hand = self.state.split_hands[self.state.current_hand_index]
                if current_hand.is_bust():
                    self.logger.info(f"[ERROR] Cannot hit - Hand {self.state.current_hand_index + 1} is already busted!")
                    return
                if current_hand.get_value() == 21:
                    self.logger.info(f"[ERROR] Cannot hit - Hand {self.state.current_hand_index + 1} already has 21!")
                    return
                self.logger.info(f"[ACTION] Player chose: HIT on Hand {self.state.current_hand_index + 1}")
            else:
                if self.state.player_hand.is_bust():
                    self.logger.info("[ERROR] Cannot hit - Hand is already busted!")
                    return
                if self.state.player_hand.get_value() == 21:
                    self.logger.info("[ERROR] Cannot hit - Hand already has 21!")
                    return
                self.logger.info("[ACTION] Player chose: HIT")
            
            busted = self.state.player_hit()
            
            # Check if we need to move to next hand or finish
            if self.state.is_split:
                # If busted is True, we've completed all hands
                if busted:
                    all_bust = all(hand.is_bust() for hand in self.state.split_hands)
                    if all_bust:
                        self.state.game_state = "game_over"
                        self.state.dealer_reveal = True
                        self.state.result_message = "All hands BUST!"
                        self.logger.info(f"[RESULT] All hands busted | Budget: ${self.state.budget} | W/L/D: {self.state.wins}/{self.state.losses}/{self.state.draws}")
                        self.update_bet_buttons_after_round()
                    else:
                        # Some hands still alive - dealer plays
                        self.logger.info("[SPLIT] All hands played, dealer's turn")
                        self.state.dealer_play()
                        self.state.determine_winner()
                        self.update_bet_buttons_after_round()
            else:
                # Check if busted (single hand)
                if busted:
                    # Update bet buttons after bust
                    self.update_bet_buttons_after_round()
                # Auto-stand if player reaches exactly 21
                elif self.state.game_state == "playing" and self.state.player_hand.get_value() == 21:
                    self.logger.info("[AUTO] Player reached 21 - automatically standing")
                    self.stand()
    
    def stand(self):
        if self.state.game_state == "playing":
            if self.state.is_split:
                self.logger.info(f"[ACTION] Player chose: STAND on Hand {self.state.current_hand_index + 1}")
                # Move to next hand if available
                if self.state.current_hand_index < len(self.state.split_hands) - 1:
                    self.state.current_hand_index += 1
                    self.logger.info(f"[SPLIT] Moving to Hand {self.state.current_hand_index + 1}")
                else:
                    # All hands played, dealer plays
                    self.logger.info("[SPLIT] All hands played, dealer's turn")
                    self.state.dealer_play()
                    self.state.determine_winner()
                    # Update bet buttons to reflect new budget
                    self.update_bet_buttons_after_round()
            else:
                self.logger.info("[ACTION] Player chose: STAND")
                self.state.dealer_play()
                self.state.determine_winner()
                # Update bet buttons to reflect new budget
                self.update_bet_buttons_after_round()
    
    def split(self):
        if self.state.game_state == "playing" and self.state.player_hand.can_split():
            self.logger.info("[ACTION] Player chose: SPLIT")
            if self.state.split_hand():
                # Split successful - no screen resize needed
                pass
            else:
                self.state.result_message = "Cannot split - insufficient funds"
     
    def update_bet_buttons_after_round(self):
        self.bet_buttons.clear()
        self.setup_bet_buttons()
    

    def change_bet_amount(self, new_amount):
        if self.state.budget >= new_amount:
            self.state.bet_amount = new_amount
            self.logger.info(f"[BET] Bet amount changed to ${new_amount}")
            # Update bet button colors
            self.bet_buttons.clear()
            self.setup_bet_buttons()
        else:
            self.logger.info(f"[BET] Cannot select ${new_amount} bet - insufficient funds (${self.state.budget} available)")
    
    def restart_with_new_budget(self):
        self.logger.info("=" * 60)
        self.logger.info("[RESTART] Starting new game with fresh budget")
        self.state.budget = 500
        self.state.wins = 0
        self.state.losses = 0
        self.state.draws = 0
        self.state.game_state = "betting"
        self.logger.info(f"[RESTART] New budget: ${self.state.budget}")
        self.logger.info("[RESTART] Select your bet amount and click 'START ROUND' to begin")
        # Update bet buttons after game over / broke
        self.bet_buttons.clear()
        self.setup_bet_buttons()
        self.update_button_positions()
    
    def draw(self):
        self.screen.fill((0, 100, 0))
        
        # Check if player can't afford minimum bet after a round 
        min_bet = min(self.bet_amounts)
        if self.state.game_state == "game_over" and self.state.budget < min_bet:
            self.logger.info(f"[GAME] Budget ${self.state.budget} below minimum bet ${min_bet} - transitioning to broke state")
            self.state.game_state = "broke"
        
        # Check if player is broke
        if self.state.game_state == "broke":
            self.draw_game_over_screen()
            return
        
        self.renderer.draw_header(self.width, self.state.budget, self.state.current_bet)
        self.renderer.draw_stats(self.state.wins, self.state.losses, self.state.draws)
        
        # Draw bet amount selector buttons (only when not in middle of a hand)
        if self.state.game_state != "playing":
            self.draw_bet_selector()
        
        # Show welcome message on initial betting screen
        if self.state.game_state == "betting" and self.state.wins == 0 and self.state.losses == 0 and self.state.draws == 0:
            self.draw_welcome_message()
        
        # Only draw hands if game has started (not in initial betting state)
        if self.state.game_state != "betting":
            dealer_value = self.state.get_dealer_visible_value()
            self.renderer.draw_hand_info("Dealer", dealer_value, 50, 100)
            self.renderer.draw_hand(self.state.dealer_hand, 50, 180, hide_first=not self.state.dealer_reveal)
        
        # when splitting, we want the 2 hands to be 
        # vertical to each other and change the info text to the left
        if self.state.is_split:
            for i, hand in enumerate(self.state.split_hands):
                y_offset = 350 + i * 140
                hand_label = f"Hand {i + 1}"
                is_active = (i == self.state.current_hand_index and self.state.game_state == "playing")
                label_color = (255, 255, 0) if is_active else (255, 255, 255)
                self.renderer.draw_hand_info_left(hand_label, hand.get_value(), 50, y_offset, label_color)
                self.renderer.draw_hand(hand, 250, y_offset)

        elif self.state.game_state != "betting":
            # Draw single player hand (only if not in initial betting state)
            self.renderer.draw_hand_info("Player", self.state.player_hand.get_value(), 50, 350)
            self.renderer.draw_hand(self.state.player_hand, 50, 430)
        
        self.renderer.draw_result_message(self.state.result_message, self.width)
        
        if self.state.game_state == "playing":
            self.hit_button.draw(self.screen, self.renderer.font_medium)
            self.stand_button.draw(self.screen, self.renderer.font_medium)
            
            # Only show split button if not already split and can split
            if not self.state.is_split:
                self.split_button.enabled = self.state.player_hand.can_split() and self.state.can_split()
                self.split_button.draw(self.screen, self.renderer.font_medium)
        else:
            self.new_game_button.draw(self.screen, self.renderer.font_medium)
        
        pygame.display.flip()
    
    # when broke or game over
    def draw_game_over_screen(self):
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(230)
        overlay.fill((0, 50, 0))
        self.screen.blit(overlay, (0, 0))
        
        # GAME OVER SCreen
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("GAME OVER!", True, (255, 0, 0))
        title_rect = title_text.get_rect(center=(self.width // 2, self.height // 2 - 100))
        self.screen.blit(title_text, title_rect)
        
        # Info for sarsa agent, after it loses a session
        msg_font = pygame.font.Font(None, 40)
        min_bet = min(self.bet_amounts)
        msg_line1 = msg_font.render(f"Budget: ${self.state.budget}", True, (255, 255, 255))
        msg_line2 = msg_font.render(f"Minimum bet: ${min_bet}", True, (255, 255, 255))
        msg_rect1 = msg_line1.get_rect(center=(self.width // 2, self.height // 2 - 40))
        msg_rect2 = msg_line2.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(msg_line1, msg_rect1)
        self.screen.blit(msg_line2, msg_rect2)
        
        # Info for sarsa agent, after it loses a session
        stats_font = pygame.font.Font(None, 32)
        stats_text = stats_font.render(
            f"Final Stats - Wins: {self.state.wins} | Losses: {self.state.losses} | Draws: {self.state.draws}",
            True, (255, 215, 0)
        )
        stats_rect = stats_text.get_rect(center=(self.width // 2, self.height // 2 + 50))
        self.screen.blit(stats_text, stats_rect)
        
        # Buttons
        self.quit_button.draw(self.screen, msg_font)
        self.restart_button.draw(self.screen, msg_font)
        
        pygame.display.flip()
    
    def draw_bet_selector(self):
        # Label
        label_font = pygame.font.Font(None, 28)
        label_text = label_font.render("Bet:", True, (255, 255, 255))
        label_x = self.width - (len(self.bet_amounts) * 65) - 50
        self.screen.blit(label_text, (label_x, 125))
        
        # Buttons
        for button in self.bet_buttons:
            button.draw(self.screen, label_font)
    
    def draw_welcome_message(self):
        welcome_font = pygame.font.Font(None, 56)
        instruction_font = pygame.font.Font(None, 36)
        
        # Welcome text
        welcome_text = welcome_font.render("Welcome to Blackjack!", True, (255, 215, 0))
        welcome_rect = welcome_text.get_rect(center=(self.width // 2, self.height // 2 - 80))
        self.screen.blit(welcome_text, welcome_rect)
        
        # Instructions
        instructions = [
            "Select your bet amount above",
            "Then click 'START ROUND' to begin"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = instruction_font.render(instruction, True, (255, 255, 255))
            inst_rect = inst_text.get_rect(center=(self.width // 2, self.height // 2 + i * 50))
            self.screen.blit(inst_text, inst_rect)
    
    def handle_mouse_motion(self, pos):
        if self.state.game_state == "broke":
            self.quit_button.check_hover(pos)
            self.restart_button.check_hover(pos)
        elif self.state.game_state == "playing":
            self.hit_button.check_hover(pos)
            self.stand_button.check_hover(pos)
            self.split_button.check_hover(pos)
        else:
            self.new_game_button.check_hover(pos)
            # Check bet buttons hover
            for button in self.bet_buttons:
                button.check_hover(pos)
    
    def handle_mouse_click(self, pos):
        if self.state.game_state == "broke":
            self.handle_broke_click(pos)
        elif self.state.game_state == "playing":
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
            action = "START ROUND" if self.state.game_state == "betting" else "NEW GAME"
            self.logger.info(f"[ACTION] Player chose: {action}")
            # Update bet buttons before dealing to reflect current budget
            self.update_bet_buttons_after_round()
            self.deal_initial_cards()
        else:
            # Check bet amount buttons
            for i, button in enumerate(self.bet_buttons):
                if button.is_clicked(pos):
                    self.change_bet_amount(self.bet_amounts[i])
    
    def handle_broke_click(self, pos):
        """Handle clicks on the game over (broke) screen"""
        if self.quit_button.is_clicked(pos):
            self.logger.info("[ACTION] Player chose: QUIT")
            pygame.quit()
            exit()
        elif self.restart_button.is_clicked(pos):
            self.logger.info("[ACTION] Player chose: RESTART WITH NEW BUDGET")
            self.restart_with_new_budget()
    
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
