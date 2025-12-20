import pygame
from mindbug_gui.screens.base_screen import BaseScreen
from mindbug_gui.widgets.buttons import Button

# Imports propres depuis le core
from mindbug_gui.core.colors import (
    BG_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT,
    BTN_PLAY, BTN_PVP, BTN_SETTINGS, BTN_QUIT, BTN_HOVER
)


class MenuScreen(BaseScreen):
    def __init__(self, app):
        super().__init__(app)
        self.res = app.res_manager
        self.widgets = []
        self._init_ui()

    def on_resize(self, w, h):
        super().on_resize(w, h)
        self._init_ui()

    def _init_ui(self):
        self.widgets.clear()

        cx = self.width // 2
        cy = self.height // 2

        # --- TITRE & SOUS-TITRE ---
        font_title = self.res.get_font(80, bold=True)
        font_sub = self.res.get_font(30, bold=True)

        self.title_surf = font_title.render("MINDBUG", True, TEXT_PRIMARY)
        self.title_rect = self.title_surf.get_rect(center=(cx, cy - 180))

        self.subtitle_surf = font_sub.render("ONLINE", True, ACCENT)
        self.subtitle_rect = self.subtitle_surf.get_rect(center=(cx, cy - 120))

        # --- BOUTONS ---
        font_btn = self.res.get_font(24, bold=True)
        w_btn, h_btn = 320, 55
        spacing = 25
        start_y = cy - 40

        # 1. PvE
        self.widgets.append(Button(
            x=cx - w_btn // 2, y=start_y,
            width=w_btn, height=h_btn,
            text="JOUER SOLO (VS IA)",
            font=font_btn,
            action="START_PVE",  # Action explicite
            bg_color=BTN_PLAY, hover_color=BTN_HOVER
        ))

        # 2. PvP (Local)
        self.widgets.append(Button(
            x=cx - w_btn // 2, y=start_y + h_btn + spacing,
            width=w_btn, height=h_btn,
            text="JOUER À DEUX (LOCAL)",
            font=font_btn,
            action="START_PVP",  # Action explicite
            bg_color=BTN_PVP, hover_color=BTN_HOVER
        ))

        # 3. Settings
        self.widgets.append(Button(
            x=cx - w_btn // 2, y=start_y + (h_btn + spacing) * 2,
            width=w_btn, height=h_btn,
            text="PARAMÈTRES",
            font=font_btn,
            action="GOTO_SETTINGS",
            bg_color=BTN_SETTINGS, hover_color=BTN_HOVER
        ))

        # 4. Quit
        self.widgets.append(Button(
            x=cx - w_btn // 2, y=start_y + (h_btn + spacing) * 3,
            width=w_btn, height=h_btn,
            text="QUITTER",
            font=font_btn,
            action="QUIT_APP",
            bg_color=BTN_QUIT, hover_color=BTN_HOVER
        ))

    def handle_events(self, events):
        for event in events:
            for widget in self.widgets:
                action = widget.handle_event(event)
                if action:
                    return action  # On remonte l'action brute au contrôleur
        return None

    def update(self, dt):
        mouse_pos = pygame.mouse.get_pos()
        for w in self.widgets:
            w.update(dt, mouse_pos)

    def draw(self, surface):
        surface.fill(BG_COLOR)
        surface.blit(self.title_surf, self.title_rect)
        surface.blit(self.subtitle_surf, self.subtitle_rect)

        for w in self.widgets:
            w.draw(surface)

        # Version
        ver = self.res.get_font(16).render("v3.1 - Stable", True, TEXT_SECONDARY)
        surface.blit(ver, (15, self.height - 25))