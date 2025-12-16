import pygame
from constants import *
from ..ui_elements import Button

class MenuScreen:
    """Écran principal du jeu : Jouer (IA/Local), Options, Quitter."""
    
    def __init__(self, screen, config, res_manager):
        self.screen = screen
        self.config = config
        self.res_manager = res_manager
        
        # Dimensions
        self.w, self.h = screen.get_size()
        
        # Polices (Attention à l'ordre : taille, style)
        self.font_title = self.res_manager.get_font(80, "title")
        self.font_btn = self.res_manager.get_font(32, "bold")
        
        self.buttons = []
        self._init_ui()

    def _init_ui(self):
        cx = self.w // 2
        cy = self.h // 2
        
        btn_w = 300
        btn_h = 60
        gap = 20
        
        # 1. BOUTON JOUER VS IA (Le nouveau mode principal)
        # On utilise COLOR_ACCENT (Bleu/Cyan) pour le mettre en valeur
        btn_pve = Button(
            rect=pygame.Rect(cx - btn_w//2, cy - 80, btn_w, btn_h),
            text="JOUER VS IA",
            font=self.font_btn,
            bg_color=COLOR_ACCENT, 
            text_color=COLOR_WHITE,
            hover_color=COLOR_HOVER,
            action="PLAY_PVE"
        )
        self.buttons.append(btn_pve)

        # 2. BOUTON PvP LOCAL (HOTSEAT)
        btn_hotseat = Button(
            rect=pygame.Rect(cx - btn_w//2, cy, btn_w, btn_h),
            text="PvP (LOCAL)",
            font=self.font_btn,
            bg_color=COLOR_BTN_PLAY,
            text_color=COLOR_WHITE,
            hover_color=COLOR_HOVER,
            action="PLAY_HOTSEAT"
        )
        self.buttons.append(btn_hotseat)

        # 3. BOUTON PARAMÈTRES
        btn_settings = Button(
            rect=pygame.Rect(cx - btn_w//2, cy + 80, btn_w, btn_h),
            text="PARAMÈTRES",
            font=self.font_btn,
            bg_color=COLOR_BTN_NORMAL,
            text_color=COLOR_WHITE,
            hover_color=COLOR_HOVER,
            action="SETTINGS"
        )
        self.buttons.append(btn_settings)
        
        # 4. BOUTON QUITTER
        btn_quit = Button(
            rect=pygame.Rect(cx - btn_w//2, cy + 160, btn_w, btn_h),
            text="QUITTER",
            font=self.font_btn,
            bg_color=COLOR_BTN_QUIT,
            text_color=COLOR_WHITE,
            hover_color=(255, 100, 100),
            action="QUIT"
        )
        self.buttons.append(btn_quit)

    def run(self):
        running = True
        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                # Clics
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        res = self._handle_click(event.pos)
                        if res: return res
            
            # Draw
            self._draw()
            pygame.display.flip()
            
        return "QUIT"

    def _handle_click(self, pos):
        """Détecte quel bouton est cliqué et configure le mode de jeu."""
        for btn in self.buttons:
            if btn.is_hovered(pos):
                
                if btn.action == "PLAY_PVE":
                    self.config.game_mode = "PVE" # <--- IMPORTANT
                    return "PLAY"
                
                elif btn.action == "PLAY_HOTSEAT":
                    self.config.game_mode = "HOTSEAT" # <--- IMPORTANT
                    return "PLAY"

                return btn.action 
        return None

    def _draw(self):
        # Fond sombre (cohérent avec settings)
        self.screen.fill((30, 30, 40))
        
        w, h = self.screen.get_size()
        
        # Titre
        title_surf = self.font_title.render("MINDBUG AI", True, COLOR_WHITE)
        title_rect = title_surf.get_rect(center=(w // 2, h * 0.15))
        self.screen.blit(title_surf, title_rect)
        
        # Boutons
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.draw(self.screen, mouse_pos)
        
        # Version
        font_small = self.res_manager.get_font(16, "body")
        ver_surf = font_small.render("v1.5.0", True, (100, 100, 100))
        self.screen.blit(ver_surf, (10, h - 30))
