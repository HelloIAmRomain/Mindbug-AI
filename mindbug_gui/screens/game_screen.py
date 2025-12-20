import pygame
import threading
import time
from copy import deepcopy
from typing import List, Optional

from mindbug_engine.utils.logger import log_info, log_error

# --- GUI CORE ---
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.card_view import CardView
from mindbug_gui.widgets.buttons import Button
from mindbug_gui.core.zones import ZoneManager

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
    Gère l'affichage, la boucle de jeu, l'IA et les interactions (Clic & Drag).
    """

    def __init__(self, app):
        super().__init__(app)
        self.res = app.res_manager

        # --- 1. ENGINE & CONFIG ---
        self.error_message: Optional[str] = None
        self.error_buttons: List[Button] = []

        self.game = MindbugGame(config=self.app.config)
        if not self.app.config.active_sets and hasattr(self.game, 'used_sets'):
            self.app.config.active_sets = self.game.used_sets
            self.app.config.save()

        try:
            self.game.start_game()
        except ValueError as e:
            self.error_message = str(e)
            self._init_error_ui()
            return

        # --- 2. GAME MODE ---
        self.game_mode = self.app.config.game_mode
        self.ai_agent = None
        self.ai_thinking = False
        self.ai_thread_result = None
        if self.game_mode == "PVE":
            self.ai_agent = AgentFactory.create_agent(difficulty=self.app.config.ai_difficulty)

        # --- 3. UI STATE ---
        self.last_active_idx = self.game.state.active_player_idx  # Plus fiable que l'objet Player
        self.show_curtain = (self.game_mode == "HOTSEAT")
        self.zoomed_card = None

        self.viewing_discard_pile: Optional[List[Card]] = None
        self.viewing_discard_owner_name: str = ""

        self.show_confirm_menu = False
        self.confirm_buttons: List[Button] = []

        # --- 4. DRAG & DROP SYSTEM ---
        self.zones = {}
        self.show_debug_zones = False

        self.dragged_card_view: Optional[CardView] = None
        self.valid_drop_zones: List[str] = []
        self.hovered_zone_id: Optional[str] = None
        self.current_ghost_rect: Optional[pygame.Rect] = None  # Position calculée du fantôme

        # Widgets
        self.card_views: List[CardView] = []
        self.ui_buttons: List[Button] = []

        # Premier calcul de layout
        self.on_resize(self.width, self.height)

    # =========================================================================
    #  LAYOUT & ZONES
    # =========================================================================

    def on_resize(self, w, h):
        """Recalcule tout lors d'un redimensionnement."""
        super().on_resize(w, h)
        # Recalcul des rectangles de zones via le Manager
        self.zones = ZoneManager.create_zones(w, h)

        if self.error_message:
            self._init_error_ui()
        else:
            self._init_layout()

    def _init_layout(self):
        """Reconstruit l'interface en injectant les cartes dans les Zones."""
        if self.error_message: return

        self.card_views.clear()
        self.ui_buttons.clear()

        if self.show_confirm_menu:
            self._create_confirm_buttons()

        # 1. Visibilité (Fog of War)
        debug = self.app.config.debug_mode
        hide_p2 = True and not debug
        hide_p1 = False

        if self.game_mode == "HOTSEAT":
            # Si c'est au tour de P2, on cache P1
            if self.game.state.active_player_idx == 1:
                hide_p1 = True and not debug
                hide_p2 = False
            else:
                hide_p2 = True and not debug
                hide_p1 = False

        # 2. Remplissage des Zones
        state = self.game.state
        self.zones["HAND_P1"].set_cards(state.player1.hand)
        self.zones["BOARD_P1"].set_cards(state.player1.board)
        self.zones["DISCARD_P1"].set_cards(state.player1.discard)
        self.zones["DECK_P1"].set_cards(state.player1.deck)

        self.zones["HAND_P2"].set_cards(state.player2.hand)
        self.zones["BOARD_P2"].set_cards(state.player2.board)
        self.zones["DISCARD_P2"].set_cards(state.player2.discard)
        self.zones["DECK_P2"].set_cards(state.player2.deck)

        # 3. Génération des Vues (CardView) depuis les Zones
        for zone_id, zone in self.zones.items():
            # La zone calcule les positions (et gère le fantôme si actif)
            card_positions = zone.get_card_rects()

            is_hidden = False
            if zone_id == "HAND_P2": is_hidden = hide_p2
            if zone_id == "HAND_P1": is_hidden = hide_p1
            if "DECK" in zone_id: is_hidden = True

            for card, rect in card_positions:
                cv = CardView(card, rect.x, rect.y, rect.width, rect.height, is_hidden=is_hidden)

                # Metadata (ex: clic défausse)
                if "DISCARD" in zone_id:
                    p = state.player1 if "P1" in zone_id else state.player2
                    cv.metadata = {"action": "VIEW_DISCARD", "player": p}

                # Highlight Attaquant
                if card == state.pending_attacker:
                    cv.is_attacking = True

                self.card_views.append(cv)

        # 4. Overlays & UI
        if state.active_request:
            self._create_selection_overlay_views()
        elif self.viewing_discard_pile:
            self._create_discard_inspection_views()

        self._refresh_highlights()
        self._create_ui_buttons()

    # =========================================================================
    #  INPUT HANDLING (EVENTS)
    # =========================================================================

    def handle_events(self, events):
        for event in events:
            # --- SHORTCUTS ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_d: self.show_debug_zones = not self.show_debug_zones
                if event.key == pygame.K_ESCAPE:
                    if self.error_message: return "MENU"
                    if self.viewing_discard_pile: self.viewing_discard_pile = None; self._init_layout(); return
                    if self.show_confirm_menu: self.show_confirm_menu = False; return
                    if self.game.state.winner: return "MENU"
                    self.show_confirm_menu = True;
                    self._create_confirm_buttons();
                    return

            # --- MODALES (Priorité Haute) ---
            if self.show_confirm_menu:
                for btn in self.confirm_buttons:
                    act = btn.handle_event(event)
                    if act == "CONFIRM_YES": return "MENU"
                    if act == "CONFIRM_NO": self.show_confirm_menu = False; return
                continue  # On bloque le reste du jeu

            if self.error_message:
                for btn in self.error_buttons:
                    if btn.handle_event(event) == "MENU": return "MENU"
                continue

            # --- BLOQUEURS ---
            if self.game.state.winner: continue
            if self.ai_thinking: continue

            # Rideau Hotseat : Clic pour débloquer
            if self.show_curtain:
                if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                    self.show_curtain = False
                continue

            # --- UI BOUTONS ---
            # On traite les boutons AVANT les cartes
            ui_handled = False
            for btn in self.ui_buttons:
                if btn.handle_event(event):
                    self._handle_button_action(btn.action)
                    ui_handled = True
                    break
            if ui_handled: continue

            # --- INTERACTIONS CARTES (CLIC & DRAG) ---

            # A. CLIC GAUCHE : DÉBUT DRAG OU CLIC SIMPLE
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Si on est en mode "Choix" ou inspection, le Drag est interdit -> Clic forcé
                is_res_phase = (self.game.state.phase == Phase.RESOLUTION_CHOICE)
                if self.viewing_discard_pile or is_res_phase:
                    self._handle_card_events(event)
                    continue

                # On cherche la carte sous la souris (Inversé pour attraper celle du dessus)
                clicked_cv = None
                for cv in reversed(self.card_views):
                    if cv.rect.collidepoint(event.pos) and not cv.is_hidden and cv.visible:
                        clicked_cv = cv
                        break

                if clicked_cv:
                    # Est-ce une carte de MA MAIN ? (Seule zone draggable pour Jouer)
                    is_in_hand = (clicked_cv.card in self.game.state.active_player.hand)

                    if is_in_hand:
                        # ... (Logique de Drag existante, on ne touche pas) ...
                        self.dragged_card_view = clicked_cv
                        clicked_cv.start_drag(event.pos)
                        self.valid_drop_zones = self._calculate_valid_drop_zones(clicked_cv.card)
                        self._update_zone_ghosts(origin_card=clicked_cv.card, hover_pos=event.pos)

                    else:
                        # >>> CLIC SIMPLE (ATTAQUE, EFFETS, DÉFAUSSE) <<<

                        # CORRECTION ICI :
                        # CardView.handle_event renvoie None sur un clic gauche (pour éviter conflit drag).
                        # On doit donc déclencher l'action manuellement ici.

                        # 1. Cas spécial : Inspection d'une pile de défausse
                        if hasattr(clicked_cv, 'metadata') and clicked_cv.metadata and clicked_cv.metadata.get(
                                "action") == "VIEW_DISCARD":
                            player = clicked_cv.metadata["player"]
                            self.viewing_discard_pile = player.discard
                            self.viewing_discard_owner_name = player.name
                            self._init_layout()

                        # 2. Cas général : Interaction de jeu (Attaquer / Sélectionner)
                        else:
                            self._try_play_card(clicked_cv.card)

            # B. CLIC GAUCHE RELÂCHÉ : FIN DU DRAG (DROP)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragged_card_view:
                    card_view = self.dragged_card_view
                    card_view.stop_drag()  # Visuellement, la carte revient à sa position (origin)

                    drop_zone_id = self.hovered_zone_id

                    # 3. Nettoyage des fantômes (Reset visuel)
                    self._clear_all_ghosts()

                    # 4. Action Moteur
                    from mindbug_gui.controller import InputHandler
                    action = InputHandler.handle_drag_drop(self.game, card_view.card, drop_zone_id)

                    if action:
                        # DROP VALIDE
                        if action[0] == "RESOLVE_SELECTION":
                            self.game.resolve_selection_effect(action[1])
                        else:
                            self.game.step(action[0], action[1])
                        self._init_layout()  # Refresh total du plateau
                    else:
                        # DROP INVALIDE (ou petit clic maladroit)
                        # Si on a à peine bougé, on considère que c'est un clic "Jouer" classique
                        dist = (event.pos[0] - card_view.origin_pos[0]) ** 2 + (
                                    event.pos[1] - card_view.origin_pos[1]) ** 2
                        if dist < 100:
                            self._try_play_card(card_view.card)
                        else:
                            # C'était un drag annulé -> Retour élastique (géré par stop_drag + refresh layout)
                            self._update_card_positions_from_zones()

                    # Reset états
                    self.dragged_card_view = None
                    self.valid_drop_zones = []
                    self.hovered_zone_id = None

            # C. SOURIS BOUGE : UPDATE DRAG & GHOST
            elif event.type == pygame.MOUSEMOTION:
                if self.dragged_card_view:
                    self.dragged_card_view.update_drag_position(event.pos)

                    # On utilise le centre de la carte pour détecter le survol
                    center = self.dragged_card_view.rect.center
                    self._update_hovered_zone(center)
                    self._update_zone_ghosts(origin_card=self.dragged_card_view.card, hover_pos=center)

            # D. CLIC DROIT (ZOOM)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                for cv in reversed(self.card_views):
                    if cv.rect.collidepoint(event.pos):
                        res = cv.handle_event(event)  # Appel direct à CardView pour le zoom
                        if res and res[0] == "ZOOM_CARD": self.zoomed_card = res[1]
                        break
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                self.zoomed_card = None

        return None

    # =========================================================================
    #  LOGIC & UPDATES
    # =========================================================================

    def update(self, dt):
        if self.error_message:
            mouse_pos = pygame.mouse.get_pos()
            for btn in self.error_buttons: btn.update(dt, mouse_pos)
            return

        self._update_ai()

        # Gestion Rideau Hotseat
        if self.game_mode == "HOTSEAT" and not self.game.state.winner:
            current_idx = self.game.state.active_player_idx
            if current_idx != self.last_active_idx:
                self.show_curtain = True
                self.last_active_idx = current_idx
                self.viewing_discard_pile = None
                self._init_layout()

        mouse_pos = pygame.mouse.get_pos()
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
                        log_error(f"⚠️ Erreur IA : {e}")

    def _run_ai_thread(self):
        try:
            time.sleep(1.0)
            game_clone = deepcopy(self.game)
            self.ai_thread_result = self.ai_agent.get_action(game_clone)
        except Exception:
            self.ai_thread_result = ("PASS", -1)

    # =========================================================================
    #  DRAG & DROP HELPERS (GHOSTS & ZONES)
    # =========================================================================

    def _calculate_valid_drop_zones(self, card) -> List[str]:
        """
        Détermine où la carte peut être lâchée (Uniquement depuis la main).
        """
        valid = []
        moves = self.game.get_legal_moves()
        ap = self.game.state.active_player

        # Détection dynamique du "Board Allié"
        is_p1 = (ap == self.game.state.player1)
        my_board = "BOARD_P1" if is_p1 else "BOARD_P2"

        # Si la carte est dans la main, on peut la jouer sur son plateau
        if card in ap.hand:
            try:
                idx = ap.hand.index(card)
                if ("PLAY", idx) in moves:
                    valid.append(my_board)
            except ValueError:
                pass

        return list(set(valid))

    def _update_hovered_zone(self, mouse_pos):
        """Identifie la zone valide sous la souris."""
        self.hovered_zone_id = None
        for z_id in self.valid_drop_zones:
            zone = self.zones.get(z_id)
            if zone and zone.rect.collidepoint(mouse_pos):
                self.hovered_zone_id = z_id
                break

    def _update_zone_ghosts(self, origin_card, hover_pos):
        """
        Met à jour l'état des zones (Trou + Fantôme).
        """
        # 1. Reset
        for zone in self.zones.values():
            zone.clear_ghost()
            zone.unignore_cards()

        # 2. Créer un trou dans la main (Ignorer la carte draguée)
        for zone in self.zones.values():
            if origin_card in zone.cards:
                zone.ignore_card(origin_card)
                break

        # 3. Ajouter le fantôme dans la zone cible
        if self.hovered_zone_id:
            target_zone = self.zones[self.hovered_zone_id]
            target_zone.set_ghost(origin_card)

        # 4. Appliquer aux vues
        self._update_card_positions_from_zones()

    def _clear_all_ghosts(self):
        """Nettoie tous les états fantômes."""
        for zone in self.zones.values():
            zone.clear_ghost()
            zone.unignore_cards()
        self._update_card_positions_from_zones()

    def _update_card_positions_from_zones(self):
        """
        Met à jour la position réelle (rect) des widgets CardView
        en fonction du layout calculé par les Zones.
        """
        view_map = {cv.card: cv for cv in self.card_views}

        for zone in self.zones.values():
            # La zone recalcule les positions (avec trou et fantôme)
            layout_data = zone.get_card_rects()

            for card_model, target_rect in layout_data:
                # Cas 1 : C'est le fantôme
                is_ghost = (self.dragged_card_view and
                            card_model == self.dragged_card_view.card and
                            zone.id == self.hovered_zone_id)

                if is_ghost:
                    self.current_ghost_rect = target_rect
                    continue

                # Cas 2 : C'est une carte normale
                if card_model in view_map:
                    # Téléportation visuelle (les cartes s'écartent)
                    view_map[card_model].rect = target_rect

                    # Si c'est la carte draguée (vue dans sa zone d'origine), on met à jour son point de retour
                    if self.dragged_card_view and card_model == self.dragged_card_view.card:
                        self.dragged_card_view.origin_pos = target_rect.topleft

    # =========================================================================
    #  DRAW
    # =========================================================================

    def draw(self, surface):
        surface.fill(BG_COLOR)

        if self.error_message: self._draw_error_modal(surface); return
        if self.show_curtain: self._draw_curtain(surface); return

        self._draw_hud(surface)
        self._draw_pile_counts(surface)

        # Overlays
        if self.game.state.active_request or self.viewing_discard_pile:
            self._draw_overlay_bg(surface)

        # 1. Feedback Fantôme (Sous les cartes)
        if self.dragged_card_view and self.hovered_zone_id and hasattr(self, 'current_ghost_rect'):
            self._draw_ghost_placeholder(surface)

        # 2. Cartes Statiques (Toutes SAUF celle qu'on drag)
        for w in self.card_views:
            if w != self.dragged_card_view:
                w.draw(surface)

        # 3. Carte Drag (Dessinée en dernier / au-dessus)
        if self.dragged_card_view:
            self.dragged_card_view.draw(surface)

        # UI & Popups
        for btn in self.ui_buttons: btn.draw(surface)
        if self.show_confirm_menu: self._draw_confirm_modal(surface)
        if self.ai_thinking: self._draw_ai_loader(surface)

        if self.game.state.pending_card and not self.game.state.winner:
            self._draw_pending_card_zoom(surface, self.game.state.pending_card)
        if self.zoomed_card: self._draw_zoomed_overlay(surface, self.zoomed_card)
        if self.game.state.winner: self._draw_winner_overlay(surface)

        if self.show_debug_zones: self._draw_debug_zones(surface)

    def _draw_ghost_placeholder(self, surface):
        if not self.hovered_zone_id: return
        rect = self.current_ghost_rect
        if not rect: return

        # Couleur (Vert = OK)
        color = (100, 255, 100)  # Vert Mindbug

        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        s.fill((*color, 80))  # Semi-transparent
        surface.blit(s, rect)
        pygame.draw.rect(surface, color, rect, 2, border_radius=8)

    # =========================================================================
    #  HELPERS UI & UTILS
    # =========================================================================

    def _init_error_ui(self):
        self.error_buttons.clear()
        font = self.app.res_manager.get_font(24, bold=True)
        cx, cy = self.width // 2, self.height // 2
        self.error_buttons.append(Button(
            cx - 100, cy + 60, 200, 50, "RETOUR MENU", font, "MENU",
            bg_color=BTN_DANGER, hover_color=BTN_HOVER
        ))

    def _create_confirm_buttons(self):
        self.confirm_buttons.clear()
        font = self.app.res_manager.get_font(24, bold=True)
        cx, cy = self.width // 2, self.height // 2
        self.confirm_buttons.append(
            Button(cx - 110, cy + 20, 100, 50, "OUI", font, "CONFIRM_YES", bg_color=BTN_DANGER, hover_color=BTN_HOVER))
        self.confirm_buttons.append(
            Button(cx + 10, cy + 20, 100, 50, "NON", font, "CONFIRM_NO", bg_color=BTN_SURFACE, hover_color=BTN_HOVER))

    def _create_ui_buttons(self):
        font = self.app.res_manager.get_font(20, bold=True)
        self.ui_buttons.append(Button(self.width - 100, 20, 80, 40, "MENU", font, "CMD_MENU", bg_color=BTN_SURFACE,
                                      text_color=TEXT_PRIMARY, hover_color=BTN_HOVER))

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
                self.ui_buttons.append(
                    Button(cx, current_y, btn_w, btn_h, "MINDBUG !", font, action, bg_color=BTN_MINDBUG,
                           hover_color=BTN_HOVER))
                current_y += spacing
            if has_no_block:
                action = self._find_move_action(legal_moves, "NO_BLOCK")
                self.ui_buttons.append(
                    Button(cx, current_y, btn_w, btn_h, "PAS DE BLOCK", font, action, bg_color=BTN_DANGER,
                           hover_color=BTN_HOVER))
                current_y += spacing
            if has_pass:
                action = self._find_move_action(legal_moves, "PASS")
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "PASSER", font, action, bg_color=BTN_PASS,
                                              hover_color=BTN_HOVER))

    def _find_move_action(self, moves, action_type):
        for i, m in enumerate(moves):
            if m[0] == action_type: return f"MOVE:{i}"
        return ""

    def _handle_button_action(self, action_id):
        # 1. Gestion du Menu (Pause / Quitter)
        if action_id == "CMD_MENU":
            self.show_confirm_menu = True
            self._create_confirm_buttons()
            return

        # 2. Gestion des coups de jeu (Play, Attack, Pass...)
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
        moves = self.game.get_legal_moves()
        for move in moves:
            action, idx = move[0], move[1]
            if action == "PLAY":
                if self.game.state.active_player.hand[idx] == card_obj: self.game.step(action,
                                                                                       idx); self._init_layout(); return
            elif action in ["ATTACK", "BLOCK"]:
                if self.game.state.active_player.board[idx] == card_obj: self.game.step(action,
                                                                                        idx); self._init_layout(); return
            elif action.startswith("SELECT_"):
                req = self.game.state.active_request
                if req and card_obj in req.candidates:
                    self.game.resolve_selection_effect(card_obj)
                    self._init_layout()
                    return

    def _refresh_highlights(self):
        for cv in self.card_views: cv.is_highlighted = False
        if self.game.state.winner or (self.game_mode == "PVE" and self.game.state.active_player_idx == 1): return
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
                    if cv.card in req.candidates: cv.is_highlighted = True
            if target_card:
                for cv in self.card_views:
                    if cv.card == target_card: cv.is_highlighted = True

    # --- DRAW UTILS ---
    def _draw_overlay_bg(self, surface):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))
        font = self.app.res_manager.get_font(30, bold=True)
        title = "CHOISISSEZ UNE CARTE" if self.game.state.active_request else f"DÉFAUSSE DE {self.viewing_discard_owner_name}"
        txt = font.render(title, True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=(self.width // 2, 80)))

    def _draw_pile_counts(self, surface):
        font = self.app.res_manager.get_font(24, bold=True)
        h_card = self.height * layout.CARD_HEIGHT_PERCENT
        w_card = h_card * layout.CARD_ASPECT_RATIO
        margin_x = self.width * layout.PILE_MARGIN_PERCENT
        if self.game.state.player1.deck:
            count = len(self.game.state.player1.deck)
            cx = self.width - margin_x - (w_card / 2)
            cy = (self.height * layout.P1_PILE_Y_PERCENT) + (h_card / 2)
            surface.blit(font.render(str(count), True, TEXT_PRIMARY),
                         font.render(str(count), True, TEXT_PRIMARY).get_rect(center=(cx, cy)))
        if self.game.state.player2.deck:
            count = len(self.game.state.player2.deck)
            cx = self.width - margin_x - (w_card / 2)
            cy = (self.height * layout.P2_PILE_Y_PERCENT) + (h_card / 2)
            surface.blit(font.render(str(count), True, TEXT_PRIMARY),
                         font.render(str(count), True, TEXT_PRIMARY).get_rect(center=(cx, cy)))

    def _draw_hud(self, surface):
        font = self.app.res_manager.get_font(24, bold=True)
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
        for btn in self.confirm_buttons: btn.draw(surface)

    def _draw_error_modal(self, surface):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        font_title = self.app.res_manager.get_font(40, bold=True)
        font_msg = self.app.res_manager.get_font(20)
        surface.blit(overlay, (0, 0))
        txt_title = font_title.render("CONFIGURATION INVALIDE", True, STATUS_CRIT)
        surface.blit(txt_title, txt_title.get_rect(center=(self.width // 2, self.height // 2 - 80)))
        lines = self.error_message.split('\n')
        y = self.height // 2 - 20
        for line in lines:
            txt_msg = font_msg.render(line, True, TEXT_PRIMARY)
            surface.blit(txt_msg, txt_msg.get_rect(center=(self.width // 2, y)))
            y += 30
        for btn in self.error_buttons: btn.draw(surface)

    def _draw_debug_zones(self, surface):
        font = self.app.res_manager.get_font(20)
        for z_id, zone in self.zones.items():
            s = pygame.Surface((zone.rect.width, zone.rect.height), pygame.SRCALPHA)
            color = (0, 255, 0, 50) if "P1" in z_id else (255, 0, 0, 50)
            if "PLAY" in z_id: color = (0, 0, 255, 50)
            s.fill(color)
            surface.blit(s, zone.rect)
            pygame.draw.rect(surface, (255, 255, 255), zone.rect, 2)
            txt = font.render(z_id, True, (255, 255, 255))
            surface.blit(txt, zone.rect.topleft)

    def _create_selection_overlay_views(self):
        req = self.game.state.active_request
        if req and req.candidates: self._create_overlay_grid(req.candidates)

    def _create_discard_inspection_views(self):
        if self.viewing_discard_pile: self._create_overlay_grid(self.viewing_discard_pile)

    def _create_overlay_grid(self, cards: List[Card]):
        if not cards: return
        valid_cards = [c for c in cards if hasattr(c, "keywords")]
        count = len(valid_cards)
        if count == 0: return
        h_c = self.height * layout.CARD_HEIGHT_PERCENT
        w_c = h_c * layout.CARD_ASPECT_RATIO
        gap = 10
        total_w = count * w_c + (count - 1) * gap
        start_x = (self.width - total_w) // 2
        y = (self.height - h_c) // 2
        for i, card in enumerate(valid_cards):
            x = start_x + i * (w_c + gap)
            cv = CardView(card, x, y, w_c, h_c)
            if self.game.state.active_request and card in self.game.state.active_request.candidates:
                cv.is_highlighted = True
            self.card_views.append(cv)