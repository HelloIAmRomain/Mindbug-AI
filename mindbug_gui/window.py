import pygame
import sys
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase

# --- CONSTANTES ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
BG_COLOR = (34, 139, 34)
CARD_COLOR = (240, 240, 240)
TEXT_COLOR = (0, 0, 0)
BUTTON_COLOR = (50, 50, 200)
BUTTON_HOVER = (80, 80, 250)

CARD_WIDTH = 100
CARD_HEIGHT = 140
MARGIN = 15

class MindbugGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mindbug AI - Interface Jouable")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        
        self.game = MindbugGame()
        
        # Stockage des zones cliquables (Hitboxes)
        # Format: {"type":Str, "index":Int, "rect":Rect}
        self.click_zones = []

    def run(self):
        running = True
        while running:
            # 1. Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Clic Gauche
                        self.handle_click(event.pos)

            # 2. Draw
            self.draw()
            
            # 3. Update
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

    def handle_click(self, pos):
        """Détecte ce que le joueur a touché"""
        for zone in self.click_zones:
            if zone["rect"].collidepoint(pos):
                action = zone["type"]
                idx = zone["index"]
                
                print(f"Clic sur : {action} (Index {idx})")
                
                # --- LOGIQUE D'INTERACTION ---
                
                # 1. JOUER UNE CARTE (Phase MAIN)
                if action == "HAND_P1" and self.game.phase == Phase.P1_MAIN:
                    self.game.step("PLAY", idx)
                elif action == "HAND_P2" and self.game.phase == Phase.P2_MAIN:
                    self.game.step("PLAY", idx)
                
                # 2. ATTAQUER (Phase MAIN)
                elif action == "BOARD_P1" and self.game.phase == Phase.P1_MAIN:
                    self.game.step("ATTACK", idx)
                elif action == "BOARD_P2" and self.game.phase == Phase.P2_MAIN:
                    self.game.step("ATTACK", idx)
                
                # 3. BLOQUER (Phase BLOCK)
                elif action == "BOARD_P1" and self.game.phase == Phase.BLOCK_DECISION and self.game.active_player_idx == 0:
                    self.game.step("BLOCK", idx)
                elif action == "BOARD_P2" and self.game.phase == Phase.BLOCK_DECISION and self.game.active_player_idx == 1:
                    self.game.step("BLOCK", idx)

                # 4. BOUTONS (Mindbug / Pass / No Block)
                elif action == "BTN_MINDBUG":
                    self.game.step("MINDBUG")
                elif action == "BTN_PASS":
                    self.game.step("PASS") # Sert aussi pour NO_BLOCK selon contexte
                elif action == "BTN_NO_BLOCK":
                    self.game.step("NO_BLOCK")
                    
                # Après une action, on print l'état pour debug
                return # On arrête après le premier clic valide

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.click_zones = [] # On vide les hitboxes à chaque frame
        
        # --- HUD ---
        phase_txt = f"Phase: {self.game.phase.name}"
        turn_txt = f"Tour: {self.game.active_player.name}"
        self.draw_text(phase_txt, 10, 10, size=24)
        self.draw_text(turn_txt, 10, 40, size=24, color=(255, 255, 0))
        
        # --- ZONES DE JEU ---
        
        # P2 (Haut)
        self.draw_hand(self.game.player2, 20, "HAND_P2", hidden=False) # Mettre hidden=True pour cacher
        self.draw_board(self.game.player2, 180, "BOARD_P2")
        
        # P1 (Bas)
        self.draw_board(self.game.player1, SCREEN_HEIGHT - 320, "BOARD_P1")
        self.draw_hand(self.game.player1, SCREEN_HEIGHT - 160, "HAND_P1")

        # --- BOUTONS CONTEXTUELS ---
        # On affiche les boutons seulement si c'est pertinent
        cx, cy = SCREEN_WIDTH - 200, SCREEN_HEIGHT // 2
        
        if self.game.phase == Phase.MINDBUG_DECISION:
            self.draw_button("UTILISER MINDBUG", cx, cy - 40, "BTN_MINDBUG")
            self.draw_button("REFUSER", cx, cy + 40, "BTN_PASS")
            
        elif self.game.phase == Phase.BLOCK_DECISION:
            self.draw_button("NE PAS BLOQUER", cx, cy, "BTN_NO_BLOCK")

    def draw_hand(self, player, y, zone_type, hidden=False):
        total_width = len(player.hand) * (CARD_WIDTH + MARGIN)
        start_x = (SCREEN_WIDTH - total_width) // 2
        
        for i, card in enumerate(player.hand):
            x = start_x + i * (CARD_WIDTH + MARGIN)
            self.draw_card(card, x, y, hidden)
            # Ajout Hitbox
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.click_zones.append({"type": zone_type, "index": i, "rect": rect})

    def draw_board(self, player, y, zone_type):
        total_width = len(player.board) * (CARD_WIDTH + MARGIN)
        start_x = (SCREEN_WIDTH - total_width) // 2
        
        for i, card in enumerate(player.board):
            x = start_x + i * (CARD_WIDTH + MARGIN)
            self.draw_card(card, x, y, hidden=False, is_in_play=True)
            # Ajout Hitbox
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.click_zones.append({"type": zone_type, "index": i, "rect": rect})

    def draw_button(self, text, x, y, action_type):
        w, h = 200, 50
        rect = pygame.Rect(x, y, w, h)
        mouse_pos = pygame.mouse.get_pos()
        color = BUTTON_HOVER if rect.collidepoint(mouse_pos) else BUTTON_COLOR
        
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (255,255,255), rect, 2, border_radius=10)
        
        txt_surf = self.font.render(text, True, (255,255,255))
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)
        
        self.click_zones.append({"type": action_type, "index": -1, "rect": rect})

    def draw_card(self, card, x, y, hidden=False, is_in_play=False):
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        
        if hidden:
            pygame.draw.rect(self.screen, (100, 50, 0), rect, border_radius=5) # Dos de carte marron
            pygame.draw.rect(self.screen, (0,0,0), rect, 2, border_radius=5)
            return

        # Fond carte
        pygame.draw.rect(self.screen, CARD_COLOR, rect, border_radius=5)
        
        # Bordure (Rouge si attaquant, Bleu si bloqueur potentiel... à faire plus tard)
        border_col = (0,0,0)
        if is_in_play and self.game.pending_attacker == card:
            border_col = (255, 0, 0) # Rouge si attaque
        pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=5)
        
        # Texte
        name_surf = self.font.render(card.name[:9], True, TEXT_COLOR)
        self.screen.blit(name_surf, (x + 5, y + 5))
        
        # Puissance
        pow_font = pygame.font.SysFont("Arial", 30, bold=True)
        col = (200, 0, 0) if "POISON" in card.keywords else (0, 0, 0)
        pow_surf = pow_font.render(str(card.power), True, col)
        self.screen.blit(pow_surf, (x + 35, y + 45))
        
        # Keywords (petits symboles)
        y_kw = y + 80
        kw_font = pygame.font.SysFont("Arial", 12)
        for kw in card.keywords:
            kw_surf = kw_font.render(kw[:4], True, (50, 50, 50))
            self.screen.blit(kw_surf, (x + 5, y_kw))
            y_kw += 12

        # Status
        if card.is_damaged:
            pygame.draw.circle(self.screen, (255, 0, 0), (x + CARD_WIDTH - 15, y + 15), 5)

    def draw_text(self, text, x, y, size=18, color=(255, 255, 255)):
        f = pygame.font.SysFont("Arial", size, bold=True)
        surf = f.render(text, True, color)
        self.screen.blit(surf, (x, y))

if __name__ == "__main__":
    gui = MindbugGUI()
    gui.run()
