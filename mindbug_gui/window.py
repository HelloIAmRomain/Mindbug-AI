import pygame
import sys
import os
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase

# --- CONSTANTES VISUELLES ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 768

BG_COLOR = (34, 139, 34)       
CARD_BACK_COLOR = (60, 40, 20) 
CARD_FALLBACK_COLOR = (240, 240, 240)
TEXT_COLOR = (0, 0, 0)
OVERLAY_COLOR = (0, 0, 0, 200)

BUTTON_COLOR = (50, 50, 200)
BUTTON_HOVER = (80, 80, 250)
BORDER_ATTACK = (255, 50, 50)
BORDER_LEGAL = (0, 255, 0)
BORDER_NORMAL = (0, 0, 0)

POWER_BUFF = (0, 200, 0)
POWER_DEBUFF = (220, 0, 0)
POWER_POISON = (140, 0, 140)
POWER_NORMAL = (0, 0, 0)

CARD_WIDTH = 120
CARD_HEIGHT = 168
MARGIN = 15


def resource_path(relative_path):
    """Obtient le chemin absolu vers la ressource, fonctionne pour dev et pour PyInstaller"""
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MindbugGUI:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mindbug AI - Interface Graphique")
        self.clock = pygame.time.Clock()
        
        self.font_small = pygame.font.SysFont("Arial", 14)
        self.font_bold = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_power = pygame.font.SysFont("Arial", 32, bold=True)
        self.font_hud = pygame.font.SysFont("Arial", 24, bold=True)
        
        self.game = MindbugGame()
        
        self.debug_view = False 
        self.image_cache = {}
        self.click_zones = [] 
        self.viewing_discard_owner = None 
        
        self.load_images()

    def load_images(self):
        asset_dir = resource_path(os.path.join("assets", "cards"))
        if not os.path.exists(asset_dir): return
        
        cards_to_load = getattr(self.game, 'all_cards_ref', self.game.full_deck)
        for card in cards_to_load:
            if not card.image_path or card.image_path in self.image_cache: continue
            full_path = os.path.join(asset_dir, card.image_path)
            if os.path.exists(full_path):
                try:
                    img = pygame.image.load(full_path).convert_alpha()
                    img = pygame.transform.smoothscale(img, (CARD_WIDTH, CARD_HEIGHT))
                    self.image_cache[card.image_path] = img
                except: self.image_cache[card.image_path] = None 
            else: self.image_cache[card.image_path] = None

    def calculate_display_power(self, card, player_board):
        current_power = card.power
        turn_owner = self.game.active_player
        if self.game.phase in [Phase.BLOCK_DECISION, Phase.MINDBUG_DECISION]:
            turn_owner = self.game.opponent
        is_my_turn = (player_board == turn_owner.board)
        
        for ally in player_board:
            if ally == card: continue
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES":
                current_power += ally.ability.value
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_IF_MY_TURN":
             if is_my_turn: current_power += card.ability.value
        for ally in player_board:
            if ally == card: continue # --- CORRECTION BUG OURSIN ---
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES_IF_MY_TURN":
                if is_my_turn: current_power += ally.ability.value
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_AND_FRENZY_IF_ALONE":
            if len(player_board) == 1: current_power += card.ability.value
        
        opp_board = self.game.player2.board if player_board == self.game.player1.board else self.game.player1.board
        is_opp_turn = not is_my_turn 
        for enemy in opp_board:
            if enemy.ability and enemy.trigger == "PASSIVE" and enemy.ability.code == "DEBUFF_ENEMIES":
                if is_opp_turn: current_power += enemy.ability.value 
        return max(0, current_power)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_d: self.debug_view = not self.debug_view
                    elif event.key == pygame.K_ESCAPE: self.viewing_discard_owner = None
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: self.handle_click(event.pos)
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

    def handle_click(self, pos):
        if self.game.winner: return
        legal_moves = self.game.get_legal_moves()

        if self.viewing_discard_owner:
            clicked_card = False
            for zone in self.click_zones:
                if zone["type"] == "OVERLAY_CARD" and zone["rect"].collidepoint(pos):
                    idx = zone["index"]
                    is_p1 = (self.viewing_discard_owner == self.game.player1)
                    action_key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
                    if (action_key, idx) in legal_moves:
                        self.game.step(action_key, idx)
                        self.viewing_discard_owner = None 
                    clicked_card = True
                    break
            if not clicked_card: self.viewing_discard_owner = None
            return 

        for zone in self.click_zones:
            if zone["rect"].collidepoint(pos):
                ui_action = zone["type"]
                idx = zone["index"]
                active_idx = self.game.active_player_idx
                is_selection = (self.game.phase == Phase.RESOLUTION_CHOICE)

                if ui_action == "DISCARD_PILE_P1":
                    self.viewing_discard_owner = self.game.player1
                    return
                elif ui_action == "DISCARD_PILE_P2":
                    self.viewing_discard_owner = self.game.player2
                    return

                if not is_selection:
                    if ui_action == "HAND_P2" and active_idx == 0 and not self.debug_view: return
                    if ui_action == "HAND_P1" and active_idx == 1 and not self.debug_view: return
                    if ui_action == "BOARD_P1" and active_idx != 0: return
                    if ui_action == "BOARD_P2" and active_idx != 1: return

                engine_action = None
                if ui_action in ["HAND_P1", "HAND_P2"]: engine_action = ("PLAY", idx)
                elif ui_action in ["BOARD_P1", "BOARD_P2"]:
                    if self.game.phase == Phase.BLOCK_DECISION: engine_action = ("BLOCK", idx)
                    elif self.game.phase == Phase.RESOLUTION_CHOICE:
                        if ui_action == "BOARD_P1": engine_action = ("SELECT_BOARD_P1", idx)
                        if ui_action == "BOARD_P2": engine_action = ("SELECT_BOARD_P2", idx)
                    else: engine_action = ("ATTACK", idx)
                elif ui_action == "BTN_MINDBUG": engine_action = ("MINDBUG", -1)
                elif ui_action == "BTN_PASS": engine_action = ("PASS", -1)
                elif ui_action == "BTN_NO_BLOCK": engine_action = ("NO_BLOCK", -1)

                if engine_action in legal_moves:
                    self.game.step(engine_action[0], engine_action[1])
                return

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.click_zones = [] 
        legal_moves = self.game.get_legal_moves()
        
        # Auto-ouverture défausse
        if self.game.phase == Phase.RESOLUTION_CHOICE and self.game.selection_context:
            cands = self.game.selection_context["candidates"]
            if cands and not self.viewing_discard_owner:
                sample = cands[0]
                if sample in self.game.player1.discard: self.viewing_discard_owner = self.game.player1
                elif sample in self.game.player2.discard: self.viewing_discard_owner = self.game.player2

        self.draw_hud()
        
        should_hide_p2 = not self.debug_view
        self.draw_hand(self.game.player2, 20, "HAND_P2", should_hide_p2, legal_moves)
        self.draw_deck_pile(self.game.player2, 20, is_right=True)
        self.draw_discard_pile(self.game.player2, 20, "DISCARD_PILE_P2")
        self.draw_board(self.game.player2, 200, "BOARD_P2", legal_moves)
        
        self.draw_board(self.game.player1, SCREEN_HEIGHT - 380, "BOARD_P1", legal_moves)
        self.draw_hand(self.game.player1, SCREEN_HEIGHT - 190, "HAND_P1", False, legal_moves)
        self.draw_deck_pile(self.game.player1, SCREEN_HEIGHT - 190, is_right=True)
        self.draw_discard_pile(self.game.player1, SCREEN_HEIGHT - 190, "DISCARD_PILE_P1")
        
        self.draw_context_buttons(legal_moves)
        
        if self.game.winner:
            self.draw_overlay_winner(self.game.winner.name)
        if self.viewing_discard_owner:
            self.draw_discard_overlay(self.viewing_discard_owner, legal_moves)

    def draw_discard_pile(self, player, y, zone_type):
        x = 100
        count = len(player.discard)
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        if count > 0:
            top_card = player.discard[-1]
            self.draw_card(top_card, x, y, hidden=False, is_in_play=False)
            pygame.draw.circle(self.screen, (0,0,0), (x+CARD_WIDTH, y), 15)
            cnt_surf = self.font_small.render(str(count), True, (255,255,255))
            self.screen.blit(cnt_surf, (x+CARD_WIDTH-8, y-8))
        else:
            pygame.draw.rect(self.screen, (0,0,0), rect, 2, border_radius=8)
            txt = self.font_small.render("Défausse", True, (200,200,200))
            self.screen.blit(txt, (x+30, y+70))
        self.click_zones.append({"type": zone_type, "index": -1, "rect": rect})

    def draw_discard_overlay(self, player, legal_moves):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0,0))
        title = f"Défausse de {player.name} ({len(player.discard)} cartes)"
        tsurf = self.font_hud.render(title, True, (255, 255, 255))
        self.screen.blit(tsurf, (SCREEN_WIDTH//2 - 150, 50))
        start_x = 100
        start_y = 150
        gap_x, gap_y = 20, 20
        cards_per_row = 8
        is_p1 = (player == self.game.player1)
        select_key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
        for i, card in enumerate(player.discard):
            col = i % cards_per_row
            row = i // cards_per_row
            x = start_x + col * (CARD_WIDTH + gap_x)
            y = start_y + row * (CARD_HEIGHT + gap_y)
            is_legal = (select_key, i) in legal_moves
            self.draw_card(card, x, y, hidden=False, highlight=is_legal)
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.click_zones.append({"type": "OVERLAY_CARD", "index": i, "rect": rect})

    def draw_hud(self):
        p1 = self.game.player1
        p2 = self.game.player2
        if self.debug_view:
            self.draw_text("👁️ DEBUG", SCREEN_WIDTH//2 - 40, 5, color=(255, 50, 50), size=16)
        self.draw_text(f"Phase : {self.game.phase.name}", 10, 10)
        self.draw_text(f"Tour : {self.game.active_player.name}", 10, 40, color=(255, 255, 0))
        self.draw_text(f"J2 (HP:{p2.hp} | MB:{p2.mindbugs})", SCREEN_WIDTH - 250, 10, color=(200, 200, 200))
        self.draw_text(f"J1 (HP:{p1.hp} | MB:{p1.mindbugs})", SCREEN_WIDTH - 250, SCREEN_HEIGHT - 40, color=(200, 200, 200))
        if self.game.phase == Phase.RESOLUTION_CHOICE:
             txt = "CLIQUEZ SUR UNE CIBLE VERTE !"
             tsurf = self.font_hud.render(txt, True, (255, 215, 0)) 
             trect = tsurf.get_rect(center=(SCREEN_WIDTH//2, 80))   
             self.screen.blit(tsurf, trect)

    def draw_hand(self, player, y, zone_type, hidden=False, legal_moves=[]):
        total_w = len(player.hand) * (CARD_WIDTH + MARGIN)
        start_x = (SCREEN_WIDTH - total_w) // 2
        is_owner_active = (self.game.active_player == player)
        for i, card in enumerate(player.hand):
            x = start_x + i * (CARD_WIDTH + MARGIN)
            is_legal = is_owner_active and ("PLAY", i) in legal_moves
            self.draw_card(card, x, y, hidden=hidden, highlight=is_legal)
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.click_zones.append({"type": zone_type, "index": i, "rect": rect})

    def draw_board(self, player, y, zone_type, legal_moves=[]):
        total_w = len(player.board) * (CARD_WIDTH + MARGIN)
        start_x = (SCREEN_WIDTH - total_w) // 2
        is_owner_active = (self.game.active_player == player)
        for i, card in enumerate(player.board):
            x = start_x + i * (CARD_WIDTH + MARGIN)
            # UTILISATION DU CALCUL ENGINE
            display_power = self.game.calculate_real_power(card) 
            
            should_highlight = False
            select_key = f"SELECT_{zone_type}" 
            if (select_key, i) in legal_moves:
                should_highlight = True
            elif is_owner_active:
                if ("ATTACK", i) in legal_moves: should_highlight = True
                if ("BLOCK", i) in legal_moves: should_highlight = True
            
            self.draw_card(card, x, y, is_in_play=True, highlight=should_highlight, override_power=display_power)
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.click_zones.append({"type": zone_type, "index": i, "rect": rect})

    def draw_card(self, card, x, y, hidden=False, is_in_play=False, highlight=False, override_power=None):
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        if hidden:
            pygame.draw.rect(self.screen, CARD_BACK_COLOR, rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=8)
            return
        img = self.image_cache.get(card.image_path)
        if img: self.screen.blit(img, (x, y))
        else:
            pygame.draw.rect(self.screen, CARD_FALLBACK_COLOR, rect, border_radius=8)
            name_txt = self.font_bold.render(card.name[:10], True, TEXT_COLOR)
            self.screen.blit(name_txt, (x+5, y+5))

        final_power = override_power if override_power is not None else card.power
        font_color = POWER_NORMAL
        if "POISON" in card.keywords: font_color = POWER_POISON
        elif final_power > card.power: font_color = POWER_BUFF
        elif final_power < card.power: font_color = POWER_DEBUFF

        cx, cy = x + 25, y + 25
        pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 18)
        pygame.draw.circle(self.screen, (0, 0, 0), (cx, cy), 18, width=2)
        pow_surf = self.font_power.render(str(final_power), True, font_color)
        pow_rect = pow_surf.get_rect(center=(cx, cy))
        self.screen.blit(pow_surf, pow_rect)
        
        kw_y = y + CARD_HEIGHT - 20
        for kw in card.keywords:
            kw_surf = self.font_small.render(kw[:4], True, (255, 255, 255))
            bg_rect = kw_surf.get_rect(topleft=(x + 5, kw_y))
            pygame.draw.rect(self.screen, (0,0,0), bg_rect)
            self.screen.blit(kw_surf, (x + 5, kw_y))
            kw_y -= 15

        if card.is_damaged:
            drop_x, drop_y = x + CARD_WIDTH - 20, y + 25
            pygame.draw.circle(self.screen, (200, 0, 0), (drop_x, drop_y), 10)
            pygame.draw.circle(self.screen, (255, 255, 255), (drop_x, drop_y), 10, width=1)

        if highlight: pygame.draw.rect(self.screen, BORDER_LEGAL, rect, 5, border_radius=8)
        elif is_in_play and self.game.pending_attacker == card:
            pygame.draw.rect(self.screen, BORDER_ATTACK, rect, 4, border_radius=8)
        else: pygame.draw.rect(self.screen, BORDER_NORMAL, rect, 1, border_radius=8)

    def draw_deck_pile(self, player, y, is_right=True):
        count = len(player.deck)
        if count == 0: return 
        x = SCREEN_WIDTH - 150 if is_right else 100
        offset = 0
        for _ in range(min(count, 3)): 
            rect = pygame.Rect(x + offset, y - offset, CARD_WIDTH, CARD_HEIGHT)
            pygame.draw.rect(self.screen, CARD_BACK_COLOR, rect, border_radius=8)
            pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=8)
            offset += 2
        txt = self.font_power.render(str(count), True, (255, 255, 255))
        self.screen.blit(txt, (x + 45, y + 60))
        self.draw_text("PIOCHE", x + 30, y + 10, size=14)

    def draw_context_buttons(self, legal_moves):
        cx, cy = SCREEN_WIDTH - 150, SCREEN_HEIGHT // 2
        if ("MINDBUG", -1) in legal_moves: self.draw_button("UTILISER MINDBUG", cx, cy - 40, "BTN_MINDBUG", color=(100, 0, 100))
        if ("PASS", -1) in legal_moves: self.draw_button("REFUSER", cx, cy + 40, "BTN_PASS", color=(100, 100, 100))
        if ("NO_BLOCK", -1) in legal_moves: self.draw_button("NE PAS BLOQUER", cx, cy, "BTN_NO_BLOCK", color=(200, 50, 50))

    def draw_button(self, text, x, y, action, color=BUTTON_COLOR):
        w, h = 180, 50
        rect = pygame.Rect(x - w//2, y - h//2, w, h)
        mouse_pos = pygame.mouse.get_pos()
        final_color = BUTTON_HOVER if rect.collidepoint(mouse_pos) else color
        pygame.draw.rect(self.screen, final_color, rect, border_radius=12)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2, border_radius=12)
        txt_surf = self.font_bold.render(text, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)
        self.click_zones.append({"type": action, "index": -1, "rect": rect})

    def draw_text(self, text, x, y, size=18, color=(255, 255, 255)):
        f = pygame.font.SysFont("Arial", size, bold=True)
        surf = f.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def draw_overlay_winner(self, winner_name):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        txt = self.font_power.render(f"VICTOIRE : {winner_name} !", True, (255, 215, 0))
        rect = txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        self.screen.blit(txt, rect)

if __name__ == "__main__":
    gui = MindbugGUI()
    gui.run()
