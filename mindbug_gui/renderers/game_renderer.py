import pygame
from mindbug_gui.core.colors import (
    BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT,
    STATUS_OK, STATUS_CRIT, STATUS_WARN, BTN_SURFACE, BTN_BORDER
)
from mindbug_gui.core import layout_config as layout
from mindbug_gui.widgets.card_view import CardView


class GameRenderer:
    """
    Responsible for rendering the entire game state to the screen.
    Decouples Game Logic from Pygame Drawing.
    """

    def __init__(self, res_manager, width, height):
        self.res = res_manager
        self.width = width
        self.height = height

    def on_resize(self, width, height):
        self.width = width
        self.height = height

    def draw(self, surface, game_state, ui_context):
        """
        Draws a complete frame.
        """
        surface.fill(BG_COLOR)

        # 1. Blocking Modals
        if ui_context.get("error_message"):
            self._draw_error_modal(
                surface, ui_context["error_message"], ui_context.get("error_buttons", []))
            return

        if game_state.phase == "INITIATIVE_BATTLE" and hasattr(game_state, "initiative_duel") and game_state.initiative_duel:
            self._draw_initiative_screen(surface, game_state.initiative_duel)
            return

        if ui_context.get("show_curtain"):
            self._draw_curtain(surface, game_state.active_player.name)
            return

        # 2. HUD
        self._draw_hud(surface, game_state)

        # 3. Overlays
        if game_state.active_request or ui_context.get("viewing_discard_pile"):
            self._draw_overlay_bg(surface, ui_context)

        # 4. Debug Zones
        if ui_context.get("show_debug_zones"):
            self._draw_debug_zones(surface, ui_context.get("zones", {}))

        # 5. Card Rendering (Bottom Layer)
        card_views = ui_context.get("card_views", [])
        dragged_cv = ui_context.get("dragged_card_view")

        if dragged_cv and ui_context.get("hovered_zone_id"):
            self._draw_ghost_placeholder(
                surface, ui_context.get("current_ghost_rect"))

        for cv in card_views:
            if cv != dragged_cv:
                cv.draw(surface)

        # 6. Dragged Card (Top Layer)
        if dragged_cv:
            dragged_cv.draw(surface)

        self._draw_pile_counts(surface, game_state, ui_context)

        # 7. UI Widgets
        for btn in ui_context.get("ui_buttons", []):
            btn.draw(surface)

        # 8. Modals & Popups
        if ui_context.get("show_confirm_menu"):
            self._draw_confirm_modal(
                surface, ui_context.get("confirm_buttons", []))

        if ui_context.get("ai_thinking"):
            self._draw_ai_loader(surface)

        # 9. Zooms & Final Effects
        if game_state.pending_card and not game_state.winner:
            self._draw_pending_card_zoom(surface, game_state.pending_card)

        if ui_context.get("zoomed_card"):
            self._draw_zoomed_overlay(surface, ui_context["zoomed_card"])

        if game_state.winner:
            self._draw_winner_overlay(surface, game_state.winner.name)

    # --- INTERNAL DRAW METHODS ---

    def _draw_initiative_screen(self, surface, duel_cards):
        """
        Affiche les deux cartes du duel et le résultat.
        Utilise des dimensions relatives pour s'adapter au resize.
        """
        c1, c2 = duel_cards
        cx, cy = self.width // 2, self.height // 2

        # 1. Dimensions relatives (Responsive)
        # On réduit à 25% de la hauteur totale (laissant 50% pour le reste)
        card_h = int(self.height * 0.25)
        card_w = int(card_h * layout.CARD_ASPECT_RATIO)

        # Espacement vertical entre le centre et les cartes
        spacing = int(self.height * 0.05)

        # 2. Titre (Positionné à 10% du haut)
        font_size_title = int(self.height * 0.06)  # Police adaptative
        font_title = self.res.get_font(font_size_title, bold=True)
        title = font_title.render("BATAILLE POUR L'INITIATIVE", True, ACCENT)
        surface.blit(title, title.get_rect(center=(cx, self.height * 0.10)))

        # 3. Carte P2 (Adversaire - Haut)
        # Centre Y = Centre Écran - (Moitié Carte) - Espace
        rect_p2 = pygame.Rect(0, 0, card_w, card_h)
        rect_p2.center = (cx, cy - (card_h // 2) - spacing)

        cv2 = CardView(c2, rect_p2.x, rect_p2.y, card_w, card_h)
        cv2.draw(surface, override_power=c2.power)

        # Label J2 (À gauche de la carte)
        font_lbl = self.res.get_font(int(self.height * 0.03), bold=True)
        lbl_p2 = font_lbl.render("J2 (Adversaire)", True, TEXT_SECONDARY)
        surface.blit(lbl_p2, lbl_p2.get_rect(
            midright=(rect_p2.left - 20, rect_p2.centery)))

        # 4. Carte P1 (Vous - Bas)
        # Centre Y = Centre Écran + (Moitié Carte) + Espace
        rect_p1 = pygame.Rect(0, 0, card_w, card_h)
        rect_p1.center = (cx, cy + (card_h // 2) + spacing)

        cv1 = CardView(c1, rect_p1.x, rect_p1.y, card_w, card_h)
        cv1.draw(surface, override_power=c1.power)

        # Label J1 (À gauche de la carte)
        lbl_p1 = font_lbl.render("J1 (Vous)", True, TEXT_SECONDARY)
        surface.blit(lbl_p1, lbl_p1.get_rect(
            midright=(rect_p1.left - 20, rect_p1.centery)))

        # 5. Résultat (Positionné à 90% du haut, c'est-à-dire en bas)
        msg = ""
        col = TEXT_PRIMARY
        if c1.power == c2.power:
            msg = "ÉGALITÉ ! (Cliquez pour relancer)"
            col = STATUS_WARN
        elif c1.power > c2.power:
            msg = "P1 COMMENCE ! (Cliquez pour jouer)"
            col = STATUS_OK
        else:
            msg = "P2 COMMENCE ! (Cliquez pour jouer)"
            col = STATUS_CRIT

        font_res = self.res.get_font(int(self.height * 0.04), bold=True)
        txt = font_res.render(msg, True, col)
        surface.blit(txt, txt.get_rect(center=(cx, self.height * 0.90)))

    def _draw_hud(self, surface, state):
        font = self.res.get_font(24, bold=True)
        raw_phase = state.phase
        phase_name = raw_phase.name if hasattr(
            raw_phase, "name") else str(raw_phase)

        surface.blit(font.render(
            f"PHASE: {phase_name}", True, TEXT_PRIMARY), (20, 20))

        p1, p2 = state.player1, state.player2
        col_p2 = STATUS_CRIT if state.active_player_idx == 1 else TEXT_SECONDARY
        surface.blit(font.render(
            f"{p2.name} | PV: {p2.hp} | MB: {p2.mindbugs}", True, col_p2), (120, 60))

        col_p1 = STATUS_OK if state.active_player_idx == 0 else TEXT_SECONDARY
        surface.blit(font.render(
            f"{p1.name} | PV: {p1.hp} | MB: {p1.mindbugs}", True, col_p1), (120, self.height - 40))

    def _draw_pile_counts(self, surface, state, ui_context):
        font = self.res.get_font(36, bold=True)
        zones = ui_context.get("zones", {})

        def draw_deck_info(deck, zone_id):
            zone = zones.get(zone_id)
            if not zone:
                return

            count = len(deck) if deck is not None else 0
            cx, cy = zone.rect.center

            if count == 0:
                card_h = int(zone.rect.height * 0.9)
                card_w = int(card_h * layout.CARD_ASPECT_RATIO)
                empty_rect = pygame.Rect(0, 0, card_w, card_h)
                empty_rect.center = (cx, cy)
                pygame.draw.rect(surface, (30, 35, 45),
                                 empty_rect, border_radius=8)
                pygame.draw.rect(surface, (60, 60, 70),
                                 empty_rect, 2, border_radius=8)

            txt_shadow = font.render(str(count), True, (0, 0, 0))
            surface.blit(txt_shadow, txt_shadow.get_rect(
                center=(cx + 2, cy + 2)))

            txt = font.render(str(count), True, TEXT_PRIMARY)
            surface.blit(txt, txt.get_rect(center=(cx, cy)))

        draw_deck_info(state.player1.deck, "DECK_P1")
        draw_deck_info(state.player2.deck, "DECK_P2")

    def _draw_curtain(self, surface, player_name):
        surface.fill(BG_COLOR)
        font = self.res.get_font(50, bold=True)
        txt = font.render(f"TOUR DE {player_name}", True, ACCENT)
        surface.blit(txt, txt.get_rect(
            center=(self.width // 2, self.height // 2)))
        sub = self.res.get_font(24).render(
            "(Cliquez pour révéler)", True, TEXT_SECONDARY)
        surface.blit(sub, sub.get_rect(
            center=(self.width // 2, self.height // 2 + 50)))

    def _draw_overlay_bg(self, surface, ui_context):
        ov = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surface.blit(ov, (0, 0))

        title = "SÉLECTION"
        if ui_context.get("viewing_discard_pile"):
            title = f"DÉFAUSSE DE {ui_context.get('viewing_discard_owner_name')}"
        elif ui_context.get("is_selection_active"):
            title = "CHOISISSEZ UNE CIBLE"

        font = self.res.get_font(30, bold=True)
        txt = font.render(title, True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=(self.width // 2, 80)))

    def _draw_ghost_placeholder(self, surface, rect):
        if not rect:
            return
        color = (100, 255, 100)
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        s.fill((*color, 80))
        surface.blit(s, rect)
        pygame.draw.rect(surface, color, rect, 2, border_radius=8)

    def _draw_ai_loader(self, surface):
        rect = pygame.Rect(self.width - 200, 10, 180, 40)
        pygame.draw.rect(surface, BTN_SURFACE, rect, border_radius=10)
        pygame.draw.rect(surface, ACCENT, rect, 2, border_radius=10)
        txt = self.res.get_font(20).render(
            "L'IA réfléchit...", True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=rect.center))

    def _draw_pending_card_zoom(self, surface, card):
        self._draw_zoomed_overlay(surface, card, title="CARTE JOUÉE")

    def _draw_zoomed_overlay(self, surface, card, title=None):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        zoom_factor = 2.4
        h = self.height * layout.CARD_HEIGHT_PERCENT * zoom_factor
        w = h * layout.CARD_ASPECT_RATIO
        cx, cy = self.width // 2, self.height // 2

        if title:
            font = self.res.get_font(40, bold=True)
            lbl = font.render(title, True, ACCENT)
            surface.blit(lbl, lbl.get_rect(center=(cx, cy - h // 2 - 40)))

        temp_cv = CardView(card, cx - w // 2, cy - h // 2, int(w), int(h))
        temp_cv.draw(surface)

    def _draw_winner_overlay(self, surface, winner_name):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))

        font = self.res.get_font(60, bold=True)
        color = STATUS_OK if winner_name == "P1" else STATUS_CRIT
        txt = font.render(f"VICTOIRE : {winner_name} !", True, color)
        surface.blit(txt, txt.get_rect(
            center=(self.width // 2, self.height // 2)))

        sub = self.res.get_font(24).render(
            "Appuyez sur ECHAP pour quitter", True, TEXT_PRIMARY)
        surface.blit(sub, sub.get_rect(
            center=(self.width // 2, self.height // 2 + 60)))

    def _draw_confirm_modal(self, surface, buttons):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        box_w, box_h = 400, 200
        cx, cy = self.width // 2, self.height // 2
        rect = pygame.Rect(cx - box_w // 2, cy - box_h // 2, box_w, box_h)

        pygame.draw.rect(surface, BTN_SURFACE, rect, border_radius=12)
        pygame.draw.rect(surface, ACCENT, rect, 2, border_radius=12)

        font = self.res.get_font(30, bold=True)
        txt = font.render("QUITTER LA PARTIE ?", True, TEXT_PRIMARY)
        surface.blit(txt, txt.get_rect(center=(cx, cy - 40)))

        for btn in buttons:
            btn.draw(surface)

    def _draw_error_modal(self, surface, message, buttons):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        surface.blit(overlay, (0, 0))

        font = self.res.get_font(40, bold=True)
        font_msg = self.res.get_font(20)

        txt = font.render("ERREUR", True, STATUS_CRIT)
        surface.blit(txt, txt.get_rect(
            center=(self.width // 2, self.height // 2 - 80)))

        y = self.height // 2 - 20
        for line in message.split('\n'):
            msg = font_msg.render(line, True, TEXT_PRIMARY)
            surface.blit(msg, msg.get_rect(center=(self.width // 2, y)))
            y += 30

        for btn in buttons:
            btn.draw(surface)

    def _draw_debug_zones(self, surface, zones):
        font = self.res.get_font(20)
        for z_id, zone in zones.items():
            s = pygame.Surface(
                (zone.rect.width, zone.rect.height), pygame.SRCALPHA)
            color = (0, 255, 0, 50) if "P1" in z_id else (255, 0, 0, 50)
            if "PLAY" in z_id:
                color = (0, 0, 255, 50)
            s.fill(color)
            surface.blit(s, zone.rect)
            pygame.draw.rect(surface, (255, 255, 255), zone.rect, 2)
            surface.blit(font.render(z_id, True, (255, 255, 255)),
                         zone.rect.topleft)
