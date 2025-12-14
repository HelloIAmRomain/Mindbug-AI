import pygame
from constants import *
from mindbug_gui.components import Button

class MenuScreen:
    """Écran principal du jeu : Jouer (Local), Options, Quitter."""
    
    def __init__(self, screen, config, res_manager):
        self.screen = screen
        self.config = config
        self.res_manager = res_manager
        self.clock = pygame.time.Clock()
        
        # Polices via Resource Manager
        self.font_title = self.res_manager.get_font(80, bold=True)
        self.font_btn = self.res_manager.get_font(40, bold=True)
        
        self.buttons = []
        self._init_layout()

    def _init_layout(self):
        w, h = self.screen.get_size()
        cx = w // 2
        cy = h // 2
        
        btn_w = int(w * 0.25) 
        btn_h = int(h * 0.10) 
        if btn_h > 80: btn_h = 80
        
        gap = int(btn_h * 1.2)
        
        self.buttons = [
            Button(
                (cx - btn_w//2, cy - gap, btn_w, btn_h),
                "PvP (LOCAL)", self.font_btn, "PLAY_HOTSEAT",
                color=COLOR_BTN_PLAY
            ),
            Button(
                (cx - btn_w//2, cy, btn_w, btn_h), 
                "PARAMÈTRES", self.font_btn, "SETTINGS",
                color=COLOR_BTN_NORMAL
            ),
            Button(
                (cx - btn_w//2, cy + gap, btn_w, btn_h), 
                "QUITTER", self.font_btn, "QUIT", 
                color=COLOR_BTN_QUIT
            )
        ]

    def run(self):
        """Boucle d'affichage du Menu."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self._init_layout() 
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return "QUIT"
                
                for btn in self.buttons:
                    if btn.is_clicked(event):
                        if btn.action_id == "PLAY_HOTSEAT":
                            self.config.game_mode = "HOTSEAT"
                            return "PLAY"
                        return btn.action_id

            self.screen.fill(COLOR_BG_MENU)
            
            w, h = self.screen.get_size()
            
            title = self.font_title.render("MINDBUG AI", True, COLOR_BLACK)
            title_rect = title.get_rect(center=(w // 2, h * 0.15))
            self.screen.blit(title, title_rect)
            
            for btn in self.buttons:
                btn.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS_CAP)
            
        return "QUIT"
