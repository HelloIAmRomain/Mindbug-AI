import pygame
import threading
import time
from copy import deepcopy
from typing import List, Optional

# --- GUI CORE ---
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.card_view import CardView
from mindbug_gui.widgets.buttons import Button

# --- CONFIG & STYLING ---
from mindbug_gui.core import layout_config as layout
from mindbug_gui.core.colors import (
    BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT,
    BTN_SURFACE, BTN_DANGER, BTN_HOVER, BTN_MINDBUG, BTN_PASS,
    STATUS_OK, STATUS_CRIT, HIGHLIGHT_GOLD
)

# --- ENGINE ---
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Phase
from mindbug_ai.factory import AgentFactory
from mindbug_engine.core.models import Card


class GameScreen(BaseScreen):
    """
    Écran principal du jeu.
    Gère l'affichage, la boucle de jeu, l'IA et les interactions complexes (Overlay, Piles).
    """

    def __init__(self, app):
        super().__init__(app)
        self.res = app.res_manager

        # =====================================================================
        # 1. ENGINE SETUP
        # =====================================================================
        self.game = MindbugGame(
            active_card_ids=None,
            active_sets=self.app.config.active_sets,
            verbose=self.app.config.debug_mode
        )

        # Sauvegarde auto de la config si vide
        if not self.app.config.active_sets and self.game.used_sets:
            self.app.config.active_sets = self.game.used_sets
            self.app.config.save_settings()

        # =====================================================================
        # 2. GAME MODE & AI
        # =====================================================================
        self.game_mode = self.app.config.game_mode
        self.ai_agent = None
        self.ai_thinking = False
        self.ai_thread_result = None

        if self.game_mode == "PVE":
            try:
                diff = self.app.config.ai_difficulty
                print(f"🤖 Init IA PVE - Niveau : {diff.name}")
                self.ai_agent = AgentFactory.create_agent(difficulty=diff)
            except Exception as e:
                print(f"❌ Erreur Init IA : {e}. Fallback sur HOTSEAT.")
                self.game_mode = "HOTSEAT"

        self.game.start_game()

        # =====================================================================
        # 3. UI STATE
        # =====================================================================
        self.last_active_player = self.game.state.active_player
        self.show_curtain = (self.game_mode == "HOTSEAT")
        self.zoomed_card = None

        # État pour l'inspection manuelle de la défausse
        self.viewing_discard_pile: Optional[List[Card]] = None
        self.viewing_discard_owner_name: str = ""

        # État pour le menu de confirmation "Quitter ?"
        self.show_confirm_menu = False
        self.confirm_buttons: List[Button] = []

        self.card_views: List[CardView] = []
        self.ui_buttons: List[Button] = []

        self._init_layout()

    # =========================================================================
    #  LAYOUT & CONSTRUCTION UI
    # =========================================================================

    def on_resize(self, w, h):
        """Recalcule tout lors d'un redimensionnement."""
        super().on_resize(w, h)
        self._init_layout()

    def _init_layout(self):
        """
        Reconstruit l'interface.
        Ordre de dessin (Z-Index) : Piles < Mains/Board < Overlay < Highlights < Boutons.
        """
        self.card_views.clear()
        self.ui_buttons.clear()

        # Si le menu de confirmation est ouvert, on recrée ses boutons (pour centrage)
        if self.show_confirm_menu:
            self._create_confirm_buttons()

        # A. Gestion Visibilité (Debug / Fog of War)
        debug = self.app.config.debug_mode

        hide_p2 = True
        hide_p1 = True

        if self.game_mode == "PVE":
            hide_p1 = False
            hide_p2 = True and not debug
        elif self.game_mode == "HOTSEAT":
            if self.game.state.active_player_idx == 0:
                hide_p1 = False
                hide_p2 = True and not debug
            else:
                hide_p2 = False
                hide_p1 = True and not debug

        # B. Création des Zones (Couches basses)

        # 1. Piles (Decks & Défausses)
        self._create_pile_views()

        # 2. Mains & Plateau
        self._create_hand_views(self.game.state.player2, is_top=True, hidden=hide_p2)
        self._create_hand_views(self.game.state.player1, is_top=False, hidden=hide_p1)
        self._create_board_views(self.game.state.player2, is_top=True)
        self._create_board_views(self.game.state.player1, is_top=False)

        # C. Création des Overlays (Couches hautes)
        # Priorité : Sélection active du moteur > Inspection manuelle
        if self.game.state.active_request:
            self._create_selection_overlay_views()
        elif self.viewing_discard_pile is not None:
            self._create_discard_inspection_views()

        # D. Interface Utilisateur
        self._refresh_highlights()
        self._create_ui_buttons()

    def _create_pile_views(self):
        """Place les Decks (Droite) et Défausses (Gauche)."""
        h_card = self.height * layout.CARD_HEIGHT_PERCENT
        w_card = h_card * layout.CARD_ASPECT_RATIO

        margin_x = self.width * layout.PILE_MARGIN_PERCENT

        # Positions X
        x_discard = margin_x
        x_deck = self.width - w_card - margin_x

        # Positions Y (Alignées sur les zones joueurs définies dans layout)
        y_p1 = self.height * layout.P1_PILE_Y_PERCENT
        y_p2 = self.height * layout.P2_PILE_Y_PERCENT

        # --- JOUEUR 2 (Haut) ---
        # Défausse (Gauche)
        if self.game.state.player2.discard:
            top = self.game.state.player2.discard[-1]
            cv = CardView(top, x_discard, y_p2, w_card, h_card)
            cv.metadata = {"action": "VIEW_DISCARD", "player": self.game.state.player2}
            self.card_views.append(cv)
        # Deck (Droite)
        if self.game.state.player2.deck:
            dummy = Card("deck_p2", "Deck", 0)
            cv = CardView(dummy, x_deck, y_p2, w_card, h_card, is_hidden=True)
            self.card_views.append(cv)

        # --- JOUEUR 1 (Bas) ---
        # Défausse (Gauche)
        if self.game.state.player1.discard:
            top = self.game.state.player1.discard[-1]
            cv = CardView(top, x_discard, y_p1, w_card, h_card)
            cv.metadata = {"action": "VIEW_DISCARD", "player": self.game.state.player1}
            self.card_views.append(cv)
        # Deck (Droite)
        if self.game.state.player1.deck:
            dummy = Card("deck_p1", "Deck", 0)
            cv = CardView(dummy, x_deck, y_p1, w_card, h_card, is_hidden=True)
            self.card_views.append(cv)

    def _create_hand_views(self, player, is_top, hidden=False):
        """Génère la main du joueur."""
        count = len(player.hand)
        if count == 0: return

        h_c = self.height * layout.CARD_HEIGHT_PERCENT
        w_c = h_c * layout.CARD_ASPECT_RATIO
        gap = self.width * layout.GAP_PERCENT

        total_w = count * w_c + (count - 1) * gap
        start_x = (self.width - total_w) // 2

        # Positionnement
        y = (self.height * layout.P2_HAND_Y_PERCENT) if is_top else (self.height * layout.P1_HAND_Y_PERCENT)

        # Ajustement P1 (Bas) pour ne pas sortir de l'écran
        if not is_top:
            y = self.height - h_c - (self.height * 0.02)

        for i, card in enumerate(player.hand):
            cv = CardView(card, start_x + i * (w_c + gap), y, w_c, h_c, is_hidden=hidden)
            self.card_views.append(cv)

    def _create_board_views(self, player, is_top):
        """Génère le plateau."""
        count = len(player.board)
        if count == 0: return

        h_c = self.height * layout.CARD_HEIGHT_PERCENT
        w_c = h_c * layout.CARD_ASPECT_RATIO
        gap = self.width * layout.GAP_PERCENT

        total_w = count * w_c + (count - 1) * gap
        start_x = (self.width - total_w) // 2

        center_y = self.height // 2
        margin = self.height * 0.05  # Marge autour du centre

        y = center_y - h_c - margin if is_top else center_y + margin

        for i, card in enumerate(player.board):
            cv = CardView(card, start_x + i * (w_c + gap), y, w_c, h_c)
            if card == self.game.state.pending_attacker:
                cv.is_attacking = True
            self.card_views.append(cv)

    def _create_selection_overlay_views(self):
        """Affiche les cartes d'une sélection active (ex: Dracompost)."""
        req = self.game.state.active_request
        if req and req.candidates:
            self._create_overlay_grid(req.candidates)

    def _create_discard_inspection_views(self):
        """Affiche le contenu de la défausse inspectée."""
        if self.viewing_discard_pile:
            self._create_overlay_grid(self.viewing_discard_pile)

    def _create_overlay_grid(self, cards: List[Card]):
        """Helper pour afficher une liste de cartes au centre."""
        if not cards: return

        # --- FIX BUG CRASH ---
        # On filtre pour ne garder que les objets qui sont réellement des cartes.
        # Cela évite que des objets 'Player' (qui n'ont pas d'attribut 'keywords')
        # ne se retrouvent dans un CardView et fassent planter le dessin.
        valid_cards = [c for c in cards if hasattr(c, "keywords")]

        count = len(valid_cards)
        if count == 0: return  # Rien à afficher si aucun candidat valide

        h_c = self.height * layout.CARD_HEIGHT_PERCENT
        w_c = h_c * layout.CARD_ASPECT_RATIO
        gap = 10

        total_w = count * w_c + (count - 1) * gap
        start_x = (self.width - total_w) // 2
        y = (self.height - h_c) // 2

        for i, card in enumerate(valid_cards):
            x = start_x + i * (w_c + gap)
            cv = CardView(card, x, y, w_c, h_c)

            # Highlight si candidat sélection
            if self.game.state.active_request and card in self.game.state.active_request.candidates:
                cv.is_highlighted = True

            self.card_views.append(cv)

    def _create_ui_buttons(self):
        """Boutons contextuels."""
        font = self.app.res_manager.get_font(20, bold=True)

        # Bouton Menu permanent
        self.ui_buttons.append(
            Button(self.width - 100, 20, 80, 40, "MENU", font, "CMD_MENU",
                   bg_color=BTN_SURFACE, text_color=TEXT_PRIMARY, hover_color=BTN_HOVER)
        )

        is_human_turn = not (self.game_mode == "PVE" and self.game.state.active_player_idx == 1)

        if is_human_turn and not self.game.state.winner:
            legal_moves = self.game.get_legal_moves()

            btn_w, btn_h = 160, 50
            cx = self.width - btn_w - 20
            cy_start = self.height // 2
            spacing = 60
            current_y = cy_start - spacing

            has_mindbug = any(m[0] == "MINDBUG" for m in legal_moves)
            has_pass = any(m[0] == "PASS" for m in legal_moves)
            has_no_block = any(m[0] == "NO_BLOCK" for m in legal_moves)

            if has_mindbug:
                action = self._find_move_action(legal_moves, "MINDBUG")
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "MINDBUG !", font, action,
                                              bg_color=BTN_MINDBUG, hover_color=BTN_HOVER))
                current_y += spacing

            if has_no_block:
                action = self._find_move_action(legal_moves, "NO_BLOCK")
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "PAS DE BLOCK", font, action,
                                              bg_color=BTN_DANGER, hover_color=BTN_HOVER))
                current_y += spacing

            if has_pass:
                action = self._find_move_action(legal_moves, "PASS")
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "PASSER", font, action,
                                              bg_color=BTN_PASS, hover_color=BTN_HOVER))

    def _create_confirm_buttons(self):
        """Crée les boutons OUI/NON pour la confirmation."""
        self.confirm_buttons.clear()
        font = self.app.res_manager.get_font(24, bold=True)
        cx, cy = self.width // 2, self.height // 2

        # Bouton OUI (Rouge)
        self.confirm_buttons.append(Button(
            cx - 110, cy + 20, 100, 50, "OUI", font, "CONFIRM_YES",
            bg_color=BTN_DANGER, hover_color=BTN_HOVER
        ))
        # Bouton NON (Neutre)
        self.confirm_buttons.append(Button(
            cx + 10, cy + 20, 100, 50, "NON", font, "CONFIRM_NO",
            bg_color=BTN_SURFACE, hover_color=BTN_HOVER
        ))

    def _find_move_action(self, moves, action_type):
        for i, m in enumerate(moves):
            if m[0] == action_type:
                return f"MOVE:{i}"
        return ""

    def _refresh_highlights(self):
        """Illumine les cartes jouables."""
        for cv in self.card_views:
            cv.is_highlighted = False

        if self.game.state.winner or (self.game_mode == "PVE" and self.game.state.active_player_idx == 1):
            return

        legal_moves = self.game.get_legal_moves()
        ap = self.game.state.active_player
        req = self.game.state.active_request

        for move in legal_moves:
            action, idx = move[0], move[1]
            target_card = None

            if action == "PLAY" and 0 <= idx < len(ap.hand):
                target_card = ap.hand[idx]
            elif action in ["ATTACK", "BLOCK"] and 0 <= idx < len(ap.board):
                target_card = ap.board[idx]
            elif action.startswith("SELECT_") and req:
                for cv in self.card_views:
                    if cv.card in req.candidates:
                        cv.is_highlighted = True

            if target_card:
                for cv in self.card_views:
                    if cv.card == target_card:
                        cv.is_highlighted = True

    # =========================================================================
    #  INPUT HANDLER
    # =========================================================================

    def handle_events(self, events):
        for event in events:
            # 1. Menu de Confirmation (Priorité absolue)
            if self.show_confirm_menu:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.show_confirm_menu = False
                    return
                for btn in self.confirm_buttons:
                    action = btn.handle_event(event)
                    if action == "CONFIRM_YES": return "MENU"
                    if action == "CONFIRM_NO":
                        self.show_confirm_menu = False
                        return
                continue  # On bloque les autres inputs

            # 2. Overlay actif (Défausse)
            if self.viewing_discard_pile:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.viewing_discard_pile = None
                    self._init_layout()
                    return

            # 3. Fin de partie
            if self.game.state.winner:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return "MENU"
                continue

            # 4. Zoom
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self.zoomed_card = None

            # 5. Rideau Hotseat
            if self.show_curtain:
                if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                    self.show_curtain = False
                continue

            # 6. UI (Boutons Jeu)
            for btn in self.ui_buttons:
                action = btn.handle_event(event)
                if action:
                    if action == "CMD_MENU":
                        self.show_confirm_menu = True
                        self._create_confirm_buttons()
                        return
                    self._handle_button_action(action)
                    break

            # 7. Cartes & Fermeture Overlay
            if not self.ai_thinking:
                if self.viewing_discard_pile and event.type == pygame.MOUSEBUTTONDOWN:
                    # Si clic hors carte dans l'overlay, on ferme
                    hit_card = False
                    for cv in self.card_views:
                        if cv.rect.collidepoint(event.pos):
                            hit_card = True
                            break

                    if not hit_card:
                        self.viewing_discard_pile = None
                        self._init_layout()
                    else:
                        self._handle_card_events(event)
                else:
                    self._handle_card_events(event)

        return None

    def _handle_button_action(self, action_id):
        if action_id.startswith("MOVE:"):
            idx = int(action_id.split(":")[1])
            legal_moves = self.game.get_legal_moves()
            if 0 <= idx < len(legal_moves):
                move = legal_moves[idx]
                self.game.step(move[0], move[1] if len(move) > 1 else None)
                self._init_layout()

    def _handle_card_events(self, event):
        for cv in self.card_views:
            res = cv.handle_event(event)
            if res:
                evt_type, card_obj = res

                # Clic sur une pile de défausse -> Ouvrir Overlay
                if hasattr(cv, 'metadata') and cv.metadata and cv.metadata.get("action") == "VIEW_DISCARD":
                    player = cv.metadata["player"]
                    self.viewing_discard_pile = player.discard
                    self.viewing_discard_owner_name = player.name
                    self._init_layout()
                    return

                if evt_type == "ZOOM_CARD":
                    if not cv.is_hidden: self.zoomed_card = card_obj
                elif evt_type == "CLICK_CARD":
                    self._try_play_card(card_obj)
                break

    def _try_play_card(self, card_obj):
        """Joue le coup si la carte cliquée est valide."""
        moves = self.game.get_legal_moves()
        for move in moves:
            action, idx = move[0], move[1]

            if action == "PLAY":
                if self.game.state.active_player.hand[idx] == card_obj:
                    self.game.step(action, idx);
                    self._init_layout();
                    return
            elif action in ["ATTACK", "BLOCK"]:
                if self.game.state.active_player.board[idx] == card_obj:
                    self.game.step(action, idx);
                    self._init_layout();
                    return
            elif action.startswith("SELECT_"):
                req = self.game.state.active_request
                if req and card_obj in req.candidates:
                    self.game.resolve_selection_effect(card_obj)
                    self._init_layout()
                    return

    # =========================================================================
    #  UPDATE & DRAW
    # =========================================================================

    def update(self, dt):
        self._update_ai()

        # Hotseat Turn Switch
        if self.game_mode == "HOTSEAT" and not self.game.state.winner:
            if self.game.state.active_player != self.last_active_player:
                self.show_curtain = True
                self.last_active_player = self.game.state.active_player
                self.viewing_discard_pile = None
                self._init_layout()

        mouse_pos = pygame.mouse.get_pos()

        # On update les widgets actifs
        widgets = self.confirm_buttons if self.show_confirm_menu else (self.card_views + self.ui_buttons)
        for w in widgets: w.update(dt, mouse_pos)

    def _update_ai(self):
        is_ai_turn = (self.game_mode == "PVE" and self.game.state.active_player_idx == 1)
        if is_ai_turn and not self.game.state.winner:
            if not self.ai_thinking:
                self.ai_thinking = True
                t = threading.Thread(target=self._run_ai_thread)
                t.daemon = True
                t.start()
            if self.ai_thread_result:
                move = self.ai_thread_result
                self.ai_thread_result = None
                self.ai_thinking = False
                if move:
                    try:
                        self.game.step(move[0], move[1] if len(move) > 1 else None)
                        self._init_layout()
                    except Exception as e:
                        print(f"⚠️ Erreur IA : {e}")

    def _run_ai_thread(self):
        try:
            time.sleep(1.0)
            game_clone = deepcopy(self.game)
            self.ai_thread_result = self.ai_agent.get_action(game_clone)
        except Exception:
            self.ai_thread_result = ("PASS", -1)

    def draw(self, surface):
        surface.fill(BG_COLOR)
        if self.show_curtain: self._draw_curtain(surface); return

        self._draw_hud(surface)

        # Overlay Discard / Selection
        is_overlay_active = (self.viewing_discard_pile is not None) or (self.game.state.active_request is not None)
        if is_overlay_active:
            ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 200))
            surface.blit(ov, (0, 0))
            font = self.app.res_manager.get_font(30, bold=True)
            title = "CHOISISSEZ UNE CARTE" if self.game.state.active_request else f"DÉFAUSSE DE {self.viewing_discard_owner_name}"
            txt = font.render(title, True, TEXT_PRIMARY)
            surface.blit(txt, txt.get_rect(center=(self.width // 2, 80)))

        for w in self.card_views: w.draw(surface)
        self._draw_pile_counts(surface)
        for btn in self.ui_buttons: btn.draw(surface)

        if self.show_confirm_menu:
            self._draw_confirm_modal(surface)

        if self.ai_thinking: self._draw_ai_loader(surface)
        if self.game.state.pending_card and not self.game.state.winner: self._draw_pending_card_zoom(surface,
                                                                                                     self.game.state.pending_card)
        if self.zoomed_card: self._draw_zoomed_overlay(surface, self.zoomed_card)
        if self.game.state.winner: self._draw_winner_overlay(surface)

    def _draw_pile_counts(self, surface):
        font = self.app.res_manager.get_font(24, bold=True)
        h_card = self.height * layout.CARD_HEIGHT_PERCENT
        w_card = h_card * layout.CARD_ASPECT_RATIO
        margin_x = self.width * layout.PILE_MARGIN_PERCENT

        if self.game.state.player1.deck:
            count = len(self.game.state.player1.deck)
            cx = self.width - margin_x - (w_card / 2)
            cy = (self.height * layout.P1_PILE_Y_PERCENT) + (h_card / 2)
            txt = font.render(str(count), True, TEXT_PRIMARY)
            surface.blit(txt, txt.get_rect(center=(cx, cy)))

        if self.game.state.player2.deck:
            count = len(self.game.state.player2.deck)
            cx = self.width - margin_x - (w_card / 2)
            cy = (self.height * layout.P2_PILE_Y_PERCENT) + (h_card / 2)
            txt = font.render(str(count), True, TEXT_PRIMARY)
            surface.blit(txt, txt.get_rect(center=(cx, cy)))

    def _draw_hud(self, surface):
        font = self.app.res_manager.get_font(24, bold=True)

        # --- FIX ROBUSTESSE : String vs Enum ---
        raw_phase = self.game.state.phase
        phase_name = raw_phase.name if hasattr(raw_phase, "name") else str(raw_phase)

        surface.blit(font.render(f"PHASE: {phase_name}", True, TEXT_PRIMARY), (20, 20))

        p1, p2 = self.game.state.player1, self.game.state.player2
        col_p2 = STATUS_CRIT if self.game.state.active_player_idx == 1 else TEXT_SECONDARY
        surface.blit(font.render(f"{p2.name} | PV: {p2.hp} | MB: {p2.mindbugs}", True, col_p2), (120, 60))
        col_p1 = STATUS_OK if self.game.state.active_player_idx == 0 else TEXT_SECONDARY
        surface.blit(font.render(f"{p1.name} | PV: {p1.hp} | MB: {p1.mindbugs}", True, col_p1), (120, self.height - 40))

    def _draw_curtain(self, surface):
        surface.fill(BG_COLOR)
        font = self.app.res_manager.get_font(50, bold=True)
        txt = font.render(f"TOUR DE {self.game.state.active_player.name}", True, ACCENT)
        surface.blit(txt, txt.get_rect(center=(self.width // 2, self.height // 2)))
        sub = self.app.res_manager.get_font(24).render("(Cliquez pour révéler)", True, TEXT_SECONDARY)
        surface.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 50)))

    def _draw_ai_loader(self, surface):
        rect = pygame.Rect(self.width - 200, 10, 180, 40)
        pygame.draw.rect(surface, BTN_SURFACE, rect, border_radius=10)
        pygame.draw.rect(surface, ACCENT, rect, 2, border_radius=10)
        txt = self.app.res_manager.get_font(20).render("L'IA réfléchit...", True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_pending_card_zoom(self, surface, card):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        zw = int(self.height * 0.4 * layout.CARD_ASPECT_RATIO)
        zh = int(self.height * 0.4)
        cx, cy = self.width // 2, self.height // 2
        font = self.app.res_manager.get_font(40, bold=True)
        lbl = font.render("CARTE JOUÉE", True, ACCENT)
        surface.blit(lbl, lbl.get_rect(center=(cx, cy - zh // 2 - 40)))
        temp_cv = CardView(card, cx - zw // 2, cy - zh // 2, zw, zh)
        temp_cv.draw(surface)

    def _draw_zoomed_overlay(self, surface, card):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))
        zoom_factor = getattr(layout, 'ZOOM_FACTOR', 2.0)
        zw = int(self.height * layout.CARD_HEIGHT_PERCENT * zoom_factor * layout.CARD_ASPECT_RATIO)
        zh = int(self.height * layout.CARD_HEIGHT_PERCENT * zoom_factor)
        cx, cy = self.width // 2, self.height // 2
        temp_cv = CardView(card, cx - zw // 2, cy - zh // 2, zw, zh)
        temp_cv.draw(surface)

    def _draw_winner_overlay(self, surface):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))
        winner_name = self.game.state.winner.name
        font = self.app.res_manager.get_font(60, bold=True)
        color = STATUS_OK if winner_name == "P1" else STATUS_CRIT
        txt = font.render(f"VICTOIRE : {winner_name} !", True, color)
        surface.blit(txt, txt.get_rect(center=(self.width // 2, self.height // 2)))
        sub = self.app.res_manager.get_font(24).render("Appuyez sur ECHAP pour quitter", True, TEXT_PRIMARY)
        surface.blit(sub, sub.get_rect(center=(self.width // 2, self.height // 2 + 60)))

    def _draw_confirm_modal(self, surface):
        """Dessine une boîte 'Êtes-vous sûr ?'."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        box_w, box_h = 400, 200
        cx, cy = self.width // 2, self.height // 2
        rect = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)
        pygame.draw.rect(surface, BTN_SURFACE, rect, border_radius=12)
        pygame.draw.rect(surface, ACCENT, rect, 2, border_radius=12)

        font = self.app.res_manager.get_font(30, bold=True)
        txt = font.render("QUITTER LA PARTIE ?", True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=(cx, cy - 40)))

        for btn in self.confirm_buttons:
            btn.draw(surface)