import pygame
from constants import *
from mindbug_engine.rules import Phase
from .layout import DynamicLayout


class GameRenderer:
    """
    Responsable de l'affichage du jeu.
    Version finale unifiée avec DynamicLayout V2, gestion des images et Notifications.
    """

    def __init__(self, screen, game_instance, config, res_manager):
        self.screen = screen
        self.game = game_instance
        self.config = config
        self.res_manager = res_manager
        self.debug = config.debug_mode

        self.click_zones = []

        # 1. Initialisation du Layout Dynamique
        w, h = self.screen.get_size()
        self.layout = DynamicLayout(w, h)

        # 2. Cache local pour les images REDIMENSIONNÉES
        self.scaled_images = {}

        self.zoomed_card = None

        # 3. Initialisation des Polices
        self._update_fonts()

    def handle_resize(self, new_w, new_h):
        """Appelé par le contrôleur quand la fenêtre change de taille."""
        self.layout.update(new_w, new_h)
        self.scaled_images.clear()
        self._update_fonts()

    def _update_fonts(self):
        """Récupère les polices à la bonne échelle."""
        self.font_small = self.res_manager.get_font(self.layout.font_size_small, font_name="Arial")
        self.font_bold = self.res_manager.get_font(self.layout.font_size_std, bold=True, font_name="Arial")
        self.font_power = self.res_manager.get_font(self.layout.font_size_title, bold=True, font_name="Arial")
        self.font_hud = self.res_manager.get_font(self.layout.font_size_title, bold=True, font_name="Arial")
        self.font_popup = self.res_manager.get_font(self.layout.font_size_huge, bold=True, font_name="Arial")

    def _get_card_surface(self, card, width, height):
        if not card: return None
        img_key = card.image_path if card.image_path else str(card.id)
        cache_key = (img_key, width, height)

        if cache_key in self.scaled_images:
            return self.scaled_images[cache_key]

        original = self.res_manager.get_card_image(card)
        if original:
            try:
                scaled = pygame.transform.smoothscale(original, (width, height))
                self.scaled_images[cache_key] = scaled
                return scaled
            except ValueError:
                return None
        return None

    def render_all(self, viewing_discard_owner=None, is_paused=False, show_curtain=False, notification=None):
        """Boucle de rendu principale."""
        self.screen.fill(COLOR_BG)
        self.click_zones = []

        # --- RIDEAU DE CONFIDENTIALITÉ (Hotseat) ---
        if show_curtain:
            self._draw_curtain()
            return

        legal_moves = self.game.get_legal_moves()

        # 1. Interface de base (HUD)
        self._draw_hud()
        self._draw_system_menu_button()

        # 2. Gestion de la visibilité
        hide_p2 = True
        hide_p1 = False

        is_pve = getattr(self.config, "game_mode", "HOTSEAT") == "PVE"
        show_all = self.debug or (getattr(self.config, "game_mode", "") == "DEV")

        if show_all:
            hide_p1 = False
            hide_p2 = False
        elif is_pve:
            hide_p2 = True
            hide_p1 = False
        else:
            if self.game.active_player == self.game.player1:
                hide_p2 = True
                hide_p1 = False
            else:
                hide_p1 = True
                hide_p2 = False

        # 3. Dessin des zones
        self._draw_player_area(self.game.player2, is_top=True, hide_hand=hide_p2, legal_moves=legal_moves)
        self._draw_player_area(self.game.player1, is_top=False, hide_hand=hide_p1, legal_moves=legal_moves)

        # Zoom sur carte Mindbug
        if self.game.pending_card and not is_paused:
            self._draw_pending_card_zoom(self.game.pending_card)

        # 4. Actions contextuelles
        if not is_paused:
            self._draw_context_buttons(legal_moves)

        # 5. Overlays (Popups)
        if self.game.winner:
            self._draw_overlay_winner(self.game.winner.name)
        elif viewing_discard_owner:
            self._draw_discard_overlay(viewing_discard_owner, legal_moves)
        elif is_paused:
            self._draw_popup_pause()

        # Zoom Clic Droit
        if self.zoomed_card:
            self._draw_zoomed_view(self.zoomed_card)

        self._draw_zoom_hint()

        # 6. Notification (IA)
        if notification:
            self._draw_notification(notification)

    def _draw_player_area(self, player, is_top, hide_hand, legal_moves):
        suffix = "P2" if is_top else "P1"
        if is_top:
            y_hand = self.layout.p2_hand_y
            y_piles = self.layout.p2_piles_y
            y_board = self.layout.p2_board_y
        else:
            y_hand = self.layout.p1_hand_y
            y_piles = self.layout.p1_piles_y
            y_board = self.layout.p1_board_y

        self._draw_deck_pile(player, y_piles, is_right=True)
        self._draw_discard_pile(player, y_piles, f"DISCARD_PILE_{suffix}")

        self._draw_card_row(player.hand, y_hand, f"HAND_{suffix}", hide_hand, legal_moves, is_board=False)
        self._draw_card_row(player.board, y_board, f"BOARD_{suffix}", False, legal_moves, is_board=True)

    def _draw_card_row(self, cards, y, zone_type, hidden, legal_moves, is_board):
        if not cards: return
        start_x = self.layout.get_row_start_x(len(cards))

        is_p1_zone = "P1" in zone_type
        row_owner = self.game.player1 if is_p1_zone else self.game.player2
        is_active_owner = (row_owner == self.game.active_player)
        is_selection_phase = (self.game.phase == Phase.RESOLUTION_CHOICE)

        for i, card in enumerate(cards):
            x = start_x + i * (self.layout.card_w + self.layout.card_gap)
            display_power = self.game.calculate_real_power(card) if is_board else card.power
            should_highlight = False

            if is_selection_phase:
                select_key = f"SELECT_{zone_type}"
                if (select_key, i) in legal_moves: should_highlight = True
            elif is_active_owner:
                if is_board:
                    if self.game.phase == Phase.BLOCK_DECISION and ("BLOCK", i) in legal_moves:
                        should_highlight = True
                    elif self.game.phase in [Phase.P1_MAIN, Phase.P2_MAIN] and ("ATTACK", i) in legal_moves:
                        should_highlight = True
                else:
                    if self.game.phase in [Phase.P1_MAIN, Phase.P2_MAIN] and (
                    "PLAY", i) in legal_moves: should_highlight = True

            self._draw_card(card, x, y, hidden, is_board, should_highlight, display_power)
            rect = pygame.Rect(x, y, self.layout.card_w, self.layout.card_h)
            self.click_zones.append({"type": zone_type, "index": i, "rect": rect})

    def _draw_card(self, card, x, y, hidden=False, is_in_play=False, highlight=False, override_power=None):
        rect = pygame.Rect(x, y, self.layout.card_w, self.layout.card_h)

        if hidden:
            pygame.draw.rect(self.screen, (60, 40, 20), rect, border_radius=8)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=8)
            cx, cy = rect.center
            pygame.draw.circle(self.screen, (80, 40, 40), (cx, cy), 15)
            return

        img = self._get_card_surface(card, self.layout.card_w, self.layout.card_h)
        if img:
            self.screen.blit(img, (x, y))
        else:
            pygame.draw.rect(self.screen, COLOR_BG_MENU, rect, border_radius=8)
            name_txt = self.font_small.render(card.name[:12], True, COLOR_BLACK)
            self.screen.blit(name_txt, (x + 5, y + 5))

        final_power = override_power if override_power is not None else card.power
        font_color = COLOR_BLACK
        if "POISON" in card.keywords:
            font_color = COLOR_POWER_POISON
        elif final_power > card.power:
            font_color = COLOR_POWER_BUFF
        elif final_power < card.power:
            font_color = COLOR_POWER_DEBUFF

        cx, cy = x + int(self.layout.card_w * 0.2), y + int(self.layout.card_h * 0.15)
        radius = int(self.layout.card_w * 0.15)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), radius)
        pygame.draw.circle(self.screen, COLOR_BLACK, (cx, cy), radius, width=2)
        pow_surf = self.font_bold.render(str(final_power), True, font_color)
        pow_rect = pow_surf.get_rect(center=(cx, cy))
        self.screen.blit(pow_surf, pow_rect)

        if highlight:
            pygame.draw.rect(self.screen, COLOR_BORDER_LEGAL, rect, 4, border_radius=8)
        elif is_in_play and self.game.pending_attacker == card:
            pygame.draw.rect(self.screen, COLOR_BORDER_ATTACK, rect, 4, border_radius=8)
        elif not img:
            pygame.draw.rect(self.screen, COLOR_BLACK, rect, 1, border_radius=8)

    def _draw_hud(self):
        p1 = self.game.player1
        p2 = self.game.player2

        self._draw_text(f"Phase : {self.game.phase.name}", self.layout.hud_x, self.layout.hud_phase_y,
                        font=self.font_bold)
        turn_col = (50, 200, 50) if self.game.active_player_idx == 0 else (200, 50, 50)
        self._draw_text(f"Tour : {self.game.active_player.name}", self.layout.hud_x, self.layout.hud_turn_y,
                        font=self.font_bold, color=turn_col)

        txt_p2 = f"J2 | PV: {p2.hp} | MB: {p2.mindbugs}"
        txt_p1 = f"J1 | PV: {p1.hp} | MB: {p1.mindbugs}"

        surf_p2 = self.font_hud.render(txt_p2, True, (220, 220, 220))
        self.screen.blit(surf_p2, (self.layout.stats_x, self.layout.stats_p2_y))
        surf_p1 = self.font_hud.render(txt_p1, True, (220, 220, 220))
        self.screen.blit(surf_p1, (self.layout.stats_x, self.layout.stats_p1_y))

        if self.game.phase == Phase.RESOLUTION_CHOICE:
            txt = "CLIQUEZ SUR UNE CIBLE VERTE !"
            tsurf = self.font_hud.render(txt, True, (255, 215, 0))
            trect = tsurf.get_rect(center=(self.layout.screen_w // 2, self.layout.msg_center_y))
            bg_rect = trect.inflate(20, 10)
            pygame.draw.rect(self.screen, (0, 0, 0, 150), bg_rect, border_radius=10)
            self.screen.blit(tsurf, trect)

    def _draw_text(self, text, x, y, font=None, color=COLOR_WHITE):
        if font is None: font = self.font_small
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _draw_system_menu_button(self):
        self._draw_button("MENU", self.layout.btn_menu_x, self.layout.btn_menu_y, "TOGGLE_MENU",
                          color=(80, 80, 80), w=self.layout.btn_menu_w, h=40)

    def _draw_context_buttons(self, legal_moves):
        is_pve = getattr(self.config, "game_mode", "HOTSEAT") == "PVE"
        if is_pve and self.game.active_player != self.game.player1: return

        cx, cy = self.layout.btn_ctx_x, self.layout.btn_ctx_y
        w, h = self.layout.btn_w, self.layout.btn_h
        gap = h + 10

        if ("MINDBUG", -1) in legal_moves:
            self._draw_button("MINDBUG", cx, cy - gap, "BTN_MINDBUG", (150, 0, 150), w, h)
        if ("PASS", -1) in legal_moves:
            self._draw_button("PASSER", cx, cy + gap, "BTN_PASS", (100, 100, 100), w, h)
        if ("NO_BLOCK", -1) in legal_moves:
            self._draw_button("NO BLOCK", cx, cy, "BTN_NO_BLOCK", (200, 50, 50), w, h)

    def _draw_button(self, text, x, y, action, color=COLOR_BTN_NORMAL, w=None, h=None):
        if w is None: w = self.layout.btn_w
        if h is None: h = self.layout.btn_h
        rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        mouse_pos = pygame.mouse.get_pos()
        final_color = color
        if rect.collidepoint(mouse_pos):
            final_color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        pygame.draw.rect(self.screen, final_color, rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2, border_radius=12)
        txt_surf = self.font_bold.render(text, True, COLOR_WHITE)
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)
        self.click_zones.append({"type": action, "index": -1, "rect": rect})

    def _draw_deck_pile(self, player, y, is_right=True):
        count = len(player.deck)
        if count == 0: return
        x = self.layout.pile_right_x if is_right else self.layout.pile_left_x
        offset = 0
        for _ in range(min(count, 3)):
            rect = pygame.Rect(x + offset, y - offset, self.layout.card_w, self.layout.card_h)
            pygame.draw.rect(self.screen, (60, 40, 20), rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_WHITE, rect, 2, border_radius=8)
            offset += 2
        txt = self.font_power.render(str(count), True, COLOR_WHITE)
        txt_rect = txt.get_rect(center=(x + self.layout.card_w // 2, y + self.layout.card_h // 2))
        self.screen.blit(txt, txt_rect)

    def _draw_discard_pile(self, player, y, zone_type):
        x = self.layout.pile_left_x
        count = len(player.discard)
        rect = pygame.Rect(x, y, self.layout.card_w, self.layout.card_h)
        if count > 0:
            top_card = player.discard[-1]
            self._draw_card(top_card, x, y, hidden=False)
            pygame.draw.circle(self.screen, COLOR_BLACK, (x + self.layout.card_w, y), 15)
            cnt_surf = self.font_small.render(str(count), True, COLOR_WHITE)
            self.screen.blit(cnt_surf, (x + self.layout.card_w - 8, y - 8))
        else:
            pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=8)
            txt = self.font_small.render("Defausse", True, (200, 200, 200))
            txt_rect = txt.get_rect(center=rect.center)
            self.screen.blit(txt, txt_rect)
        self.click_zones.append({"type": zone_type, "index": -1, "rect": rect})

    def _draw_curtain(self):
        self.screen.fill((20, 30, 40))
        player_name = self.game.active_player.name
        color = (255, 215, 0)  # Or
        txt = self.font_popup.render(f"C'EST À {player_name} DE JOUER", True, color)
        rect = txt.get_rect(center=(self.layout.screen_w // 2, self.layout.screen_h // 2 - 20))
        self.screen.blit(txt, rect)
        sub = self.font_hud.render("(Cliquez pour révéler votre jeu)", True, (200, 200, 200))
        sub_rect = sub.get_rect(center=(self.layout.screen_w // 2, self.layout.screen_h // 2 + 30))
        self.screen.blit(sub, sub_rect)

    def _draw_pending_card_zoom(self, card):
        overlay = pygame.Surface((self.layout.screen_w, self.layout.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        zoom_factor = 2.0
        max_h = self.layout.screen_h * 0.6
        if self.layout.card_h * zoom_factor > max_h:
            zoom_factor = max_h / self.layout.card_h
        zw = int(self.layout.card_w * zoom_factor)
        zh = int(self.layout.card_h * zoom_factor)
        cx, cy = self.layout.screen_w // 2, self.layout.screen_h // 2
        x = cx - zw // 2
        y = cy - zh // 2

        title = self.font_hud.render("CARTE JOUÉE", True, (255, 215, 0))
        self.screen.blit(title, title.get_rect(center=(cx, y - 50)))

        img = self._get_card_surface(card, zw, zh)
        rect = pygame.Rect(x, y, zw, zh)
        if img:
            self.screen.blit(img, (x, y))
        else:
            pygame.draw.rect(self.screen, COLOR_BG_MENU, rect, border_radius=12)
            name_txt = self.font_bold.render(card.name, True, COLOR_BLACK)
            self.screen.blit(name_txt, name_txt.get_rect(center=rect.center))
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 4, border_radius=12)

        radius = int(zw * 0.15)
        pcx, pcy = x + int(zw * 0.2), y + int(zh * 0.15)
        pygame.draw.circle(self.screen, COLOR_WHITE, (pcx, pcy), radius)
        pygame.draw.circle(self.screen, COLOR_BLACK, (pcx, pcy), radius, width=3)
        font_zoom = self.res_manager.get_font(int(self.layout.font_size_title * zoom_factor), bold=True)
        pow_surf = font_zoom.render(str(card.power), True, COLOR_BLACK)
        self.screen.blit(pow_surf, pow_surf.get_rect(center=(pcx, pcy)))

    def _draw_zoom_hint(self):
        txt = "Clic Droit : Zoom"
        surf = self.font_bold.render(txt, True, (255, 255, 255))
        margin_right = 20
        margin_bottom = 10
        x = self.layout.screen_w - surf.get_width() - margin_right
        y = self.layout.screen_h - surf.get_height() - margin_bottom
        bg_rect = surf.get_rect(topleft=(x, y))
        bg_rect.inflate_ip(10, 6)
        pygame.draw.rect(self.screen, (0, 0, 0, 150), bg_rect, border_radius=5)
        self.screen.blit(surf, (x, y))

    def _draw_zoomed_view(self, card):
        overlay = pygame.Surface((self.layout.screen_w, self.layout.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        zoom_factor = 2.5
        max_h = self.layout.screen_h * 0.8
        if self.layout.card_h * zoom_factor > max_h:
            zoom_factor = max_h / self.layout.card_h
        zw = int(self.layout.card_w * zoom_factor)
        zh = int(self.layout.card_h * zoom_factor)
        cx, cy = self.layout.screen_w // 2, self.layout.screen_h // 2
        rect = pygame.Rect(cx - zw // 2, cy - zh // 2, zw, zh)

        img = self._get_card_surface(card, zw, zh)
        if img:
            self.screen.blit(img, rect)
        else:
            pygame.draw.rect(self.screen, COLOR_BG_MENU, rect, border_radius=15)
            t = self.font_popup.render(card.name, True, COLOR_BLACK)
            self.screen.blit(t, t.get_rect(center=rect.center))
        pygame.draw.rect(self.screen, COLOR_WHITE, rect, 4, border_radius=15)

        rad = int(zw * 0.12)
        pcx, pcy = rect.x + int(zw * 0.18), rect.y + int(zh * 0.15)
        pygame.draw.circle(self.screen, COLOR_WHITE, (pcx, pcy), rad)
        pygame.draw.circle(self.screen, COLOR_BLACK, (pcx, pcy), rad, width=3)
        font_z = self.res_manager.get_font(int(self.layout.font_size_huge * 1.5), bold=True)
        p_surf = font_z.render(str(card.power), True, COLOR_BLACK)
        self.screen.blit(p_surf, p_surf.get_rect(center=(pcx, pcy)))

    # --- NOUVEAUX ÉCRANS (NOTIFICATIONS & VICTOIRE) ---

    def _draw_notification(self, text):
        """Bannière de notification IA."""
        w, h = 600, 60
        x = (self.layout.screen_w - w) // 2
        y = 100
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, (0, 0, 0, 230), rect, border_radius=15)
        pygame.draw.rect(self.screen, (255, 215, 0), rect, 2, border_radius=15)
        surf = self.font_hud.render(text, True, (255, 255, 255))
        txt_rect = surf.get_rect(center=rect.center)
        self.screen.blit(surf, txt_rect)

    def _draw_overlay_winner(self, winner_name):
        """Écran de fin avec boutons Rejouer/Menu."""
        overlay = pygame.Surface((self.layout.screen_w, self.layout.screen_h))
        overlay.set_alpha(200)
        overlay.fill(COLOR_BLACK)
        self.screen.blit(overlay, (0, 0))

        color = (0, 255, 0) if winner_name == "P1" else (255, 50, 50)
        txt = self.font_popup.render(f"VICTOIRE : {winner_name} !", True, color)
        rect = txt.get_rect(center=(self.layout.screen_w // 2, self.layout.screen_h // 2 - 60))
        self.screen.blit(txt, rect)

        cx = self.layout.screen_w // 2
        cy = self.layout.screen_h // 2 + 40
        btn_w, btn_h = 160, 50

        self._draw_button("REJOUER", cx - 90, cy, "BTN_REPLAY", color=COLOR_BTN_PLAY, w=btn_w, h=btn_h)
        self._draw_button("MENU", cx + 90, cy, "BTN_MENU_END", color=COLOR_BTN_NORMAL, w=btn_w, h=btn_h)

    def _draw_popup_pause(self):
        overlay = pygame.Surface((self.layout.screen_w, self.layout.screen_h), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0, 0))
        box_w, box_h = int(self.layout.screen_w * 0.4), int(self.layout.screen_h * 0.3)
        if box_w < 300: box_w = 300
        cx, cy = self.layout.screen_w // 2, self.layout.screen_h // 2
        rect = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
        pygame.draw.rect(self.screen, COLOR_BG_MENU, rect, border_radius=20)
        pygame.draw.rect(self.screen, COLOR_BLACK, rect, 4, border_radius=20)
        txt = self.font_hud.render("Retourner au Menu ?", True, COLOR_BLACK)
        txt_rect = txt.get_rect(center=(cx, cy - 40))
        self.screen.blit(txt, txt_rect)
        btn_y = cy + 40
        btn_w, btn_h = 100, 40
        self._draw_button("OUI", cx - 70, btn_y, "CONFIRM_QUIT", color=COLOR_BTN_PLAY, w=btn_w, h=btn_h)
        self._draw_button("NON", cx + 70, btn_y, "CANCEL_QUIT", color=COLOR_BTN_QUIT, w=btn_w, h=btn_h)

    def _draw_discard_overlay(self, player, legal_moves):
        overlay = pygame.Surface((self.layout.screen_w, self.layout.screen_h), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0, 0))
        title = f"Défausse de {player.name}"
        tsurf = self.font_hud.render(title, True, COLOR_WHITE)
        self.screen.blit(tsurf, (50, 50))
        start_x = 100
        start_y = 150
        gap = 20
        is_p1 = (player == self.game.player1)
        select_key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
        x, y = start_x, start_y
        for i, card in enumerate(player.discard):
            is_legal = (select_key, i) in legal_moves
            self._draw_card(card, x, y, hidden=False, highlight=is_legal)
            rect = pygame.Rect(x, y, self.layout.card_w, self.layout.card_h)
            self.click_zones.append({"type": "OVERLAY_CARD", "index": i, "rect": rect})
            x += self.layout.card_w + gap
            if x + self.layout.card_w > self.layout.screen_w - 50:
                x = start_x
                y += self.layout.card_h + gap