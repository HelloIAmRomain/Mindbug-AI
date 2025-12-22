import pygame
import threading
import time
from copy import deepcopy
from typing import List, Optional

from mindbug_engine.utils.logger import log_error
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Phase
from mindbug_engine.core.models import Card
from mindbug_ai.factory import AgentFactory

# --- GUI CORE ---
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.card_view import CardView
from mindbug_gui.widgets.buttons import Button
from mindbug_gui.core.zones import ZoneManager
from mindbug_gui.core.colors import (
    TEXT_PRIMARY, BTN_SURFACE, BTN_DANGER, BTN_HOVER, BTN_MINDBUG, BTN_PASS
)

# --- NEW ARCHITECTURE IMPORTS ---
from mindbug_gui.controller import InputHandler
from mindbug_gui.renderers.game_renderer import GameRenderer


class GameScreen(BaseScreen):
    """
    Controller principal du jeu.
    """

    def __init__(self, app):
        super().__init__(app)

        # 1. INITIALISATION DU MOTEUR
        self.game = MindbugGame(config=self.app.config)
        self.error_message = None

        if not self.app.config.active_sets and hasattr(self.game, 'used_sets'):
            self.app.config.active_sets = self.game.used_sets
            self.app.config.save()

        try:
            self.game.start_game()
        except ValueError as e:
            self.error_message = str(e)

        # 2. IA (AGENT)
        self.ai_agent = None
        if self.app.config.game_mode == "PVE":
            self.ai_agent = AgentFactory.create_agent(
                difficulty=self.app.config.ai_difficulty,
                strategy="MCTS"
            )

        self.ai_thinking = False
        self.ai_thread_result = None

        # 3. INITIALISATION VUE
        self.renderer = GameRenderer(app.res_manager, self.width, self.height)

        # 4. ÉTAT UI
        self.zones = {}
        self.card_views: List[CardView] = []
        self.ui_buttons: List[Button] = []

        self.confirm_buttons: List[Button] = []
        self.error_buttons: List[Button] = []
        self.show_confirm_menu = False

        # FIX RIDEAU : Pas de rideau au démarrage si on est en bataille d'initiative
        is_hotseat = (self.app.config.game_mode == "HOTSEAT")
        is_init_phase = (self.game.state.phase == Phase.INITIATIVE_BATTLE)
        self.show_curtain = is_hotseat and not is_init_phase

        self.last_active_idx = 0

        self.zoomed_card = None
        self.viewing_discard_pile = None
        self.viewing_discard_owner_name = ""
        self.show_debug_zones = False

        self.dragged_card_view: Optional[CardView] = None
        self.valid_drop_zones: List[str] = []
        self.hovered_zone_id: Optional[str] = None
        self.current_ghost_rect: Optional[pygame.Rect] = None

        self.on_resize(self.width, self.height)
        if self.error_message:
            self._init_error_ui()

    def on_resize(self, w, h):
        super().on_resize(w, h)
        self.renderer.on_resize(w, h)
        self.zones = ZoneManager.create_zones(w, h)

        if not self.error_message:
            self._refresh_ui_components()
        else:
            self._init_error_ui()

    # =========================================================================
    #  BOUCLE PRINCIPALE
    # =========================================================================

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return self._handle_escape()
                if event.key == pygame.K_d:
                    self.show_debug_zones = not self.show_debug_zones

            if self.error_message:
                res = self._handle_modal_events(event, self.error_buttons)
                if res == "MENU":
                    return "MENU"
                continue

            if self.show_confirm_menu:
                res = self._handle_modal_events(event, self.confirm_buttons)
                if res == "CONFIRM_YES":
                    return "MENU"
                if res == "CONFIRM_NO":
                    self.show_confirm_menu = False
                continue

            # Rideau (Prioritaire sauf si Initiative)
            if self.show_curtain:
                if event.type in [pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN]:
                    self.show_curtain = False
                continue

            if self.game.state.phase == Phase.INITIATIVE_BATTLE:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # On envoie la commande de confirmation
                    self._execute_game_step(("CONFIRM_INITIATIVE", -1))
                continue

            if self.game.state.winner or self.ai_thinking:
                continue

            if self._handle_ui_buttons(event):
                continue

            self._handle_card_interactions(event)

        return None

    def update(self, dt):
        if self.error_message:
            return
        self._update_ai()
        self._check_hotseat_curtain()

        mouse_pos = pygame.mouse.get_pos()
        active_widgets = self.confirm_buttons if self.show_confirm_menu else (
            self.card_views + self.ui_buttons)
        for w in active_widgets:
            w.update(dt, mouse_pos)

    def draw(self, surface):
        ui_context = {
            "error_message": self.error_message,
            "error_buttons": self.error_buttons,
            "show_curtain": self.show_curtain,
            "show_confirm_menu": self.show_confirm_menu,
            "confirm_buttons": self.confirm_buttons,
            "ai_thinking": self.ai_thinking,
            "card_views": self.card_views,
            "ui_buttons": self.ui_buttons,
            "viewing_discard_pile": self.viewing_discard_pile,
            "viewing_discard_owner_name": self.viewing_discard_owner_name,
            "is_selection_active": self.game.state.phase == Phase.RESOLUTION_CHOICE,
            "dragged_card_view": self.dragged_card_view,
            "hovered_zone_id": self.hovered_zone_id,
            "current_ghost_rect": self.current_ghost_rect,
            "valid_drop_zones": self.valid_drop_zones,
            "zoomed_card": self.zoomed_card,
            "show_debug_zones": self.show_debug_zones,
            "zones": self.zones
        }
        self.renderer.draw(surface, self.game.state, ui_context)

    # =========================================================================
    #  LOGIQUE IA
    # =========================================================================

    def _update_ai(self):
        if self.app.config.game_mode != "PVE" or self.game.state.winner:
            return

        # Pas d'IA pendant la phase d'initiative
        if self.game.state.phase == Phase.INITIATIVE_BATTLE:
            return

        is_p2_active = (self.game.state.active_player_idx == 1)
        req = self.game.state.active_request
        is_p2_selecting = (req is not None and req.selector ==
                           self.game.state.player2)
        ai_must_play = (is_p2_active or is_p2_selecting)

        if ai_must_play:
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
                        if move[0].startswith("SELECT_"):
                            from mindbug_engine.commands.command_factory import CommandFactory
                            cmd = CommandFactory.create(
                                move[0], move[1], self.game)
                            if cmd:
                                cmd.execute(self.game)
                        else:
                            self.game.step(move[0], move[1]
                                           if len(move) > 1 else None)
                        self._refresh_ui_components()
                    except Exception as e:
                        log_error(f"⚠️ Erreur exécution coup IA : {e}")

    def _run_ai_thread(self):
        try:
            time.sleep(0.5)
            game_clone = deepcopy(self.game)
            self.ai_thread_result = self.ai_agent.get_action(game_clone)
        except Exception as e:
            log_error(f"❌ CRASH IA Thread : {e}")
            self.ai_thread_result = ("PASS", -1)

    # =========================================================================
    #  LOGIQUE STANDARD
    # =========================================================================

    def _handle_ui_buttons(self, event):
        for btn in self.ui_buttons:
            if btn.handle_event(event):
                cmd = InputHandler.handle_button_click(btn.action)
                if cmd:
                    self._execute_game_step(cmd)
                elif btn.action == "CMD_MENU":
                    self._open_confirm_menu()
                elif btn.action == "SKIP_HUNTER":
                    self.game.resolve_selection_effect("NO_HUNT")
                    self._refresh_ui_components()
                return True
        return False

    def _handle_card_interactions(self, event):
        # ... (Identique à avant, juste copié pour la structure)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._handle_right_click(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.zoomed_card = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.ai_thinking:
                return
            if self.app.config.game_mode == "PVE":
                req = self.game.state.active_request
                if req and req.selector == self.game.state.player2:
                    return

            clicked_cv = self._get_card_view_under_mouse(event.pos)
            if clicked_cv:
                if clicked_cv.metadata and clicked_cv.metadata.get("action") == "VIEW_DISCARD":
                    self._open_discard_pile(clicked_cv.metadata["player"])
                    return
                is_in_hand = (
                    clicked_cv.card in self.game.state.active_player.hand)
                allow_drag = not (
                    self.viewing_discard_pile or self.game.state.phase == Phase.RESOLUTION_CHOICE)
                if is_in_hand and allow_drag:
                    self._start_drag(clicked_cv, event.pos)
                else:
                    self._handle_simple_click(clicked_cv.card)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_card_view:
                self._stop_drag(event.pos)
        elif event.type == pygame.MOUSEMOTION:
            if self.dragged_card_view:
                self.dragged_card_view.update_drag_position(event.pos)
                self._update_ghosts(self.dragged_card_view.rect.center)

    def _handle_simple_click(self, card):
        action = InputHandler.handle_card_click(self.game, card)
        if action:
            if action[0] == "RESOLVE_SELECTION":
                self.game.resolve_selection_effect(action[1])
                self._refresh_ui_components()
            else:
                self._execute_game_step(action)

    def _start_drag(self, card_view, pos):
        self.dragged_card_view = card_view
        card_view.start_drag(pos)
        self.valid_drop_zones = InputHandler.get_valid_drop_zones(
            self.game, card_view.card)
        self._update_ghosts(pos)

    def _stop_drag(self, pos):
        card_view = self.dragged_card_view
        card_view.stop_drag()
        action = InputHandler.handle_drag_drop(
            self.game, card_view.card, self.hovered_zone_id)
        self.dragged_card_view = None
        self.valid_drop_zones = []
        self.hovered_zone_id = None
        self._clear_ghosts()

        if action:
            if action[0] == "RESOLVE_SELECTION":
                self.game.resolve_selection_effect(action[1])
            else:
                self.game.step(action[0], action[1])
            self._refresh_ui_components()
        else:
            dist = (pos[0] - card_view.origin_pos[0])**2 + \
                (pos[1] - card_view.origin_pos[1])**2
            if dist < 100:
                self._handle_simple_click(card_view.card)
            else:
                self._update_card_positions_from_zones()

    # =========================================================================
    #  LOGIQUE ZONES & GHOSTS
    # =========================================================================

    def _update_ghosts(self, mouse_pos):
        card = self.dragged_card_view.card
        self.hovered_zone_id = None
        for z_id in self.valid_drop_zones:
            zone = self.zones.get(z_id)
            if zone and zone.rect.collidepoint(mouse_pos):
                self.hovered_zone_id = z_id
                break

        for zone in self.zones.values():
            zone.clear_ghost()
            zone.unignore_cards()
            if card in zone.cards:
                zone.ignore_card(card)

        if self.hovered_zone_id:
            visual_zone_id = self.hovered_zone_id
            if visual_zone_id == "PLAY_AREA":
                if card in self.game.state.active_player.hand:
                    is_p1 = (self.game.state.active_player ==
                             self.game.state.player1)
                    visual_zone_id = "BOARD_P1" if is_p1 else "BOARD_P2"
                else:
                    visual_zone_id = None

            if visual_zone_id:
                self.hovered_zone_id = visual_zone_id
                if visual_zone_id in self.zones:
                    self.zones[visual_zone_id].set_ghost(card)
        self._update_card_positions_from_zones()

    def _clear_ghosts(self):
        for zone in self.zones.values():
            zone.clear_ghost()
            zone.unignore_cards()
        self._update_card_positions_from_zones()

    def _update_card_positions_from_zones(self):
        view_map = {cv.card: cv for cv in self.card_views}
        for zone in self.zones.values():
            layout_data = zone.get_card_rects()
            for card_model, target_rect in layout_data:
                is_ghost = (self.dragged_card_view and card_model ==
                            self.dragged_card_view.card and zone.id == self.hovered_zone_id)
                if is_ghost:
                    self.current_ghost_rect = target_rect
                    continue
                if card_model in view_map:
                    view_map[card_model].rect = target_rect
                    if self.dragged_card_view and card_model == self.dragged_card_view.card:
                        self.dragged_card_view.origin_pos = target_rect.topleft

    # =========================================================================
    #  HELPERS DE CONSTRUCTION UI
    # =========================================================================

    def _refresh_ui_components(self):
        self.card_views.clear()
        self.ui_buttons.clear()
        state = self.game.state

        debug = self.app.config.debug_mode
        visual_idx = self._get_visual_player_idx()
        hide_p1 = (visual_idx == 1) and not debug
        hide_p2 = (visual_idx == 0) and not debug
        if self.app.config.game_mode == "PVE":
            hide_p2 = not debug

        self.zones["HAND_P1"].set_cards(state.player1.hand)
        self.zones["BOARD_P1"].set_cards(state.player1.board)
        self.zones["DISCARD_P1"].set_cards(state.player1.discard)
        self.zones["DECK_P1"].set_cards(state.player1.deck)  # Pioche P1

        self.zones["HAND_P2"].set_cards(state.player2.hand)
        self.zones["BOARD_P2"].set_cards(state.player2.board)
        self.zones["DISCARD_P2"].set_cards(state.player2.discard)
        self.zones["DECK_P2"].set_cards(state.player2.deck)  # Pioche P2

        for zone_id, zone in self.zones.items():
            card_positions = zone.get_card_rects()
            is_hidden = False
            if zone_id == "HAND_P1":
                is_hidden = hide_p1
            if zone_id == "HAND_P2":
                is_hidden = hide_p2
            if "DECK" in zone_id:
                is_hidden = True  # Pioches cachées

            for card, rect in card_positions:
                cv = CardView(card, rect.x, rect.y, rect.width,
                              rect.height, is_hidden=is_hidden)
                if "DISCARD" in zone_id:
                    p = state.player1 if "P1" in zone_id else state.player2
                    cv.metadata = {"action": "VIEW_DISCARD", "player": p}
                if card == state.pending_attacker:
                    cv.is_attacking = True
                self.card_views.append(cv)

        if state.active_request:
            self._create_selection_overlay_views()
        elif self.viewing_discard_pile:
            self._create_discard_inspection_views()

        self._refresh_highlights()
        self._create_ui_buttons()

    def _create_ui_buttons(self):
        font = self.app.res_manager.get_font(20, bold=True)
        self.ui_buttons.append(Button(self.width - 100, 20, 80, 40, "MENU", font, "CMD_MENU",
                                      bg_color=BTN_SURFACE, text_color=TEXT_PRIMARY, hover_color=BTN_HOVER))

        req = self.game.state.active_request
        if req and req.reason == "HUNTER_TARGET":
            cx = self.width // 2
            cy = self.height - 130
            self.ui_buttons.append(Button(cx - 100, cy, 200, 50, "ATTAQUE NORMALE", font, "SKIP_HUNTER",
                                          bg_color=BTN_PASS, hover_color=BTN_HOVER))
            return

        is_human_turn = not (self.app.config.game_mode ==
                             "PVE" and self.game.state.active_player_idx == 1)
        if is_human_turn and not self.game.state.winner:
            legal_moves = self.game.get_legal_moves()
            has_mindbug = any(m[0] == "MINDBUG" for m in legal_moves)
            has_pass = any(m[0] == "PASS" for m in legal_moves)
            has_no_block = any(m[0] == "NO_BLOCK" for m in legal_moves)

            btn_w, btn_h = 160, 50
            cx = self.width - btn_w - 20
            current_y = self.height // 2 - 60
            spacing = 60

            if has_mindbug:
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "MINDBUG !", font, "CMD_MINDBUG",
                                              bg_color=BTN_MINDBUG, hover_color=BTN_HOVER))
                current_y += spacing
            if has_no_block:
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "PAS DE BLOCK", font, "CMD_NO_BLOCK",
                                              bg_color=BTN_DANGER, hover_color=BTN_HOVER))
                current_y += spacing
            if has_pass:
                self.ui_buttons.append(Button(cx, current_y, btn_w, btn_h, "PASSER", font, "CMD_PASS",
                                              bg_color=BTN_PASS, hover_color=BTN_HOVER))

    def _refresh_highlights(self):
        if self.game.state.winner:
            return
        if self.app.config.game_mode == "PVE" and self.game.state.active_player_idx == 1:
            return

        moves = self.game.get_legal_moves()
        req = self.game.state.active_request
        ap = self.game.state.active_player
        valid_cards = set()

        for move in moves:
            action, idx = move[0], move[1]
            if action == "PLAY" and 0 <= idx < len(ap.hand):
                valid_cards.add(ap.hand[idx])
            elif action in ["ATTACK", "BLOCK"] and 0 <= idx < len(ap.board):
                valid_cards.add(ap.board[idx])

        if req:
            for c in req.candidates:
                valid_cards.add(c)

        for cv in self.card_views:
            if cv.card in valid_cards:
                cv.is_highlighted = True

    # =========================================================================
    #  OVERLAYS & MODALES
    # =========================================================================

    def _create_selection_overlay_views(self):
        req = self.game.state.active_request
        if not req or not req.candidates:
            return
        first = req.candidates[0]
        in_discard = any(first in p.discard for p in self.game.state.players)
        if in_discard:
            self._create_overlay_grid(req.candidates)

    def _create_discard_inspection_views(self):
        if self.viewing_discard_pile:
            self._create_overlay_grid(self.viewing_discard_pile)

    def _create_overlay_grid(self, cards):
        count = len(cards)
        if count == 0:
            return
        h = self.height * 0.22
        w = h * 0.714
        gap = 10
        total_w = count * w + (count - 1) * gap
        start_x = (self.width - total_w) // 2
        y = (self.height - h) // 2

        for i, card in enumerate(cards):
            x = start_x + i * (w + gap)
            cv = CardView(card, x, y, w, h)
            if self.game.state.active_request and card in self.game.state.active_request.candidates:
                cv.is_highlighted = True
            self.card_views.append(cv)

    def _init_error_ui(self):
        self.error_buttons = [Button(self.width // 2 - 100, self.height // 2 + 60, 200, 50, "RETOUR MENU",
                                     self.app.res_manager.get_font(24), "MENU", bg_color=BTN_DANGER, hover_color=BTN_HOVER)]

    def _open_confirm_menu(self):
        self.show_confirm_menu = True
        cx, cy = self.width // 2, self.height // 2
        font = self.app.res_manager.get_font(24)
        self.confirm_buttons = [
            Button(cx - 110, cy + 20, 100, 50, "OUI", font,
                   "CONFIRM_YES", bg_color=BTN_DANGER, hover_color=BTN_HOVER),
            Button(cx + 10, cy + 20, 100, 50, "NON", font, "CONFIRM_NO",
                   bg_color=BTN_SURFACE, hover_color=BTN_HOVER)
        ]

    def _execute_game_step(self, action):
        self.game.step(action[0], action[1])
        self._refresh_ui_components()

    def _handle_escape(self):
        if self.error_message:
            return "MENU"
        if self.viewing_discard_pile:
            self.viewing_discard_pile = None
            self._refresh_ui_components()
            return None
        if self.show_confirm_menu:
            self.show_confirm_menu = False
            return None
        if self.game.state.winner:
            return "MENU"
        self._open_confirm_menu()
        return None

    def _handle_modal_events(self, event, buttons):
        for btn in buttons:
            act = btn.handle_event(event)
            if act:
                return act
        return None

    def _handle_right_click(self, event):
        for cv in reversed(self.card_views):
            if cv.rect.collidepoint(event.pos) and not cv.is_hidden:
                self.zoomed_card = cv.card
                break

    def _get_card_view_under_mouse(self, pos):
        for cv in reversed(self.card_views):
            if cv.rect.collidepoint(pos) and not cv.is_hidden and cv.visible:
                return cv
        return None

    def _open_discard_pile(self, player):
        self.viewing_discard_pile = player.discard
        self.viewing_discard_owner_name = player.name
        self._refresh_ui_components()

    def _check_hotseat_curtain(self):
        if self.game.state.phase == Phase.INITIATIVE_BATTLE:
            self.show_curtain = False
            return

        if self.app.config.game_mode == "HOTSEAT" and not self.game.state.winner:
            visual_idx = self._get_visual_player_idx()
            if visual_idx != self.last_active_idx:
                self.show_curtain = True
                self.last_active_idx = visual_idx
                self.viewing_discard_pile = None
                self._refresh_ui_components()

    def _get_visual_player_idx(self):
        idx = self.game.state.active_player_idx
        req = self.game.state.active_request
        if req and self.game.state.phase == Phase.RESOLUTION_CHOICE:
            if req.selector == self.game.state.player1:
                return 0
            elif req.selector == self.game.state.player2:
                return 1
        return idx
