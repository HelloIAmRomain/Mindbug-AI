import pygame
from constants import COLOR_WHITE, COLOR_BLACK, COLOR_HOVER, COLOR_ACCENT, COLOR_BTN_NORMAL, COLOR_BTN_PLAY
from ..ui_elements import Button

class SettingsScreen:
    def __init__(self, screen, config, res_manager):
        self.screen = screen
        self.config = config
        self.res_manager = res_manager
        
        self.w, self.h = screen.get_size()
        
        # Polices
        self.font_title = self.res_manager.get_font(60, bold=True)
        self.font_sub = self.res_manager.get_font(30, bold=True)
        self.font_btn = self.res_manager.get_font(24, bold=True)
        self.font_small = self.res_manager.get_font(20, bold=False)

        self.buttons = []
        self._init_ui()
        
        # Slider Logic (Positionné en bas)
        self.slider_rect = pygame.Rect(self.w//2 - 150, 500, 300, 20)
        self.dragging_slider = False
    
    def _init_ui(self):
        self.buttons = [] # Reset
        cx = self.w // 2
        
        # --- 1. BOUTON RETOUR (Haut Gauche) ---
        btn_back = Button(
            rect=pygame.Rect(20, 20, 120, 40),
            text="< Retour",
            font=self.font_btn,
            bg_color=COLOR_BLACK,
            text_color=COLOR_WHITE,
            hover_color=COLOR_HOVER,
            action="MENU"
        )
        self.buttons.append(btn_back)
        
        # --- 2. GESTION DES SETS (Extensions) ---
        # On affiche un bouton bascule par Set trouvé dans la base de données
        y_set = 150
        
        # On récupère la liste des sets dispos via la config
        avail_sets = getattr(self.config, "available_sets_in_db", ["FIRST_CONTACT"])
        
        for set_id in avail_sets:
            is_active = set_id in self.config.active_sets
            
            # Couleur : Vert si actif, Gris si inactif
            color = COLOR_BTN_PLAY if is_active else (100, 100, 100)
            status_txt = "[ON]" if is_active else "[OFF]"
            
            btn_set = Button(
                rect=pygame.Rect(cx - 200, y_set, 400, 50),
                text=f"{set_id} {status_txt}",
                font=self.font_btn,
                bg_color=color,
                text_color=COLOR_WHITE,
                hover_color=COLOR_HOVER,
                action=f"TOGGLE_SET:{set_id}" # Action dynamique
            )
            self.buttons.append(btn_set)
            y_set += 60

        # --- 3. MODE DEBUG ---
        y_debug = y_set + 40
        debug_txt = "Mode Debug : ON" if self.config.debug_mode else "Mode Debug : OFF"
        color_debug = (50, 150, 50) if self.config.debug_mode else (150, 50, 50)
        
        btn_debug = Button(
            rect=pygame.Rect(cx - 150, y_debug, 300, 50),
            text=debug_txt,
            font=self.font_btn,
            bg_color=color_debug,
            text_color=COLOR_WHITE,
            hover_color=COLOR_HOVER,
            action="TOGGLE_DEBUG"
        )
        self.buttons.append(btn_debug)

        # Note: Le slider est géré manuellement dans draw/handle_input

    def run(self):
        running = True
        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                # Souris
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # Slider ?
                        if self.slider_rect.inflate(20, 20).collidepoint(event.pos):
                            self.dragging_slider = True
                            self._update_slider_value(event.pos[0])
                        # Boutons ?
                        else:
                            res = self._handle_click(event.pos)
                            if res == "MENU": return "MENU"
                            # Si c'est un toggle, on reste sur l'écran et on rafraichit l'UI
                            if res == "REFRESH": 
                                self._init_ui() 

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.dragging_slider = False

                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_slider:
                        self._update_slider_value(event.pos[0])

            # Draw
            self._draw()
            pygame.display.flip()
            
        return "MENU"

    def _update_slider_value(self, mouse_x):
        x_min = self.slider_rect.left
        width = self.slider_rect.width
        rel_x = max(0, min(width, mouse_x - x_min))
        ratio = rel_x / width
        new_val = 1 + round(ratio * 9)
        
        if new_val != self.config.ai_difficulty:
            self.config.ai_difficulty = new_val
            self.config.save_settings()

    def _handle_click(self, pos):
        """Gère les clics et retourne 'MENU', 'REFRESH' ou None."""
        for btn in self.buttons:
            if btn.is_hovered(pos):
                
                if btn.action == "MENU":
                    return "MENU"
                
                elif btn.action == "TOGGLE_DEBUG":
                    self.config.debug_mode = not self.config.debug_mode
                    self.config.save_settings()
                    return "REFRESH" # Recharger les couleurs
                
                elif btn.action.startswith("TOGGLE_SET:"):
                    set_id = btn.action.split(":")[1]
                    if set_id in self.config.active_sets:
                        # On empêche de désactiver le dernier set (pour éviter deck vide)
                        if len(self.config.active_sets) > 1:
                            self.config.active_sets.remove(set_id)
                    else:
                        self.config.active_sets.append(set_id)
                    
                    self.config.save_settings()
                    return "REFRESH"
                    
        return None

    def _draw(self):
        self.screen.fill((30, 30, 40))
        cx = self.w // 2
        
        # Titre
        title = self.font_title.render("PARAMÈTRES", True, COLOR_WHITE)
        self.screen.blit(title, (cx - title.get_width()//2, 30))
        
        # Sous-titre Sets
        sub_sets = self.font_sub.render("EXTENSIONS ACTIVES", True, (200, 200, 200))
        self.screen.blit(sub_sets, (cx - sub_sets.get_width()//2, 110))
        
        # Boutons
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.draw(self.screen, mouse_pos)
            
        # --- SLIDER IA ---
        self._draw_slider()

    def _draw_slider(self):
        val = self.config.ai_difficulty
        
        # Description
        desc = ""
        color_desc = COLOR_WHITE
        if val <= 3: 
            desc = "(Débutant)"
            color_desc = (100, 255, 100)
        elif val <= 7: 
            desc = "(Intermédiaire)"
            color_desc = (255, 255, 100)
        else: 
            desc = "(Expert - Lent)"
            color_desc = (255, 100, 100)
            
        label = self.font_sub.render(f"Niveau de l'IA : {val}", True, COLOR_WHITE)
        sub_label = self.font_small.render(desc, True, color_desc)
        
        cx = self.w // 2
        # Position du texte (au dessus du slider)
        self.screen.blit(label, (cx - label.get_width()//2, 450))
        self.screen.blit(sub_label, (cx - sub_label.get_width()//2, 480))
        
        # Barre
        pygame.draw.rect(self.screen, (60, 60, 60), self.slider_rect, border_radius=10)
        ratio = (val - 1) / 9
        fill_width = ratio * self.slider_rect.width
        fill_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, fill_width, self.slider_rect.height)
        pygame.draw.rect(self.screen, COLOR_ACCENT, fill_rect, border_radius=10)
        
        # Curseur
        knob_x = self.slider_rect.x + fill_width
        knob_y = self.slider_rect.centery
        pygame.draw.circle(self.screen, COLOR_WHITE, (int(knob_x), int(knob_y)), 12)
        pygame.draw.circle(self.screen, (200, 200, 200), (int(knob_x), int(knob_y)), 12, 2)
