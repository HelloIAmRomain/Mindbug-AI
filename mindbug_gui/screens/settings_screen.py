import pygame
from constants import *
from mindbug_gui.components import Button, Toggle, CardThumbnail
from mindbug_engine.loaders import CardLoader

class SettingsScreen:
    """Écran de configuration, gestion des Sets et sélection de deck."""
    
    def __init__(self, screen, config, res_manager):
        self.screen = screen
        self.config = config
        self.res_manager = res_manager
        self.clock = pygame.time.Clock()
        
        self.font = self.res_manager.get_font(20)
        self.font_title = self.res_manager.get_font(40, bold=True)
        self.font_popup = self.res_manager.get_font(30, bold=True)
        
        self.is_confirming = False
        
        # Données
        self.all_cards = CardLoader.load_deck(PATH_DATA)
        self.available_sets = sorted(list(set(c.set for c in self.all_cards)))
        
        # UI Elements
        self.toggles_options = []
        self.toggles_sets = []
        self.thumbnails = []
        self.btn_back = None
        self.btn_yes = None
        self.btn_no = None
        
        self._init_layout()

    def _init_layout(self):
        w, h = self.screen.get_size()
        cx, cy = w // 2, h // 2
        
        # --- OPTIONS ---
        opt_y = int(h * 0.12)
        col1_x = int(w * 0.15)
        
        self.toggles_options = [
            Toggle(col1_x, opt_y, "Mode Debug (Voir mains)", self.font, initial_value=self.config.debug_mode),
            Toggle(col1_x, opt_y + 40, "Effets Sonores", self.font, initial_value=self.config.enable_sound),
            Toggle(col1_x, opt_y + 80, "Animations", self.font, initial_value=self.config.enable_effects),
        ]
        
        # --- SETS ---
        col_set_x = int(w * 0.55) 
        set_y = opt_y
        
        existing_states = {t.set_id: t.value for t in self.toggles_sets} if self.toggles_sets else {}
        
        self.toggles_sets = []
        for set_name in self.available_sets:
            if set_name in existing_states:
                is_active = existing_states[set_name]
            else:
                is_active = set_name in self.config.active_sets

            display_name = set_name.replace("_", " ").title()
            label = f"Set : {display_name}"
            
            tog = Toggle(col_set_x, set_y, label, self.font, initial_value=is_active)
            tog.set_id = set_name
            
            self.toggles_sets.append(tog)
            set_y += 40
            
        # --- GRILLE ---
        start_x = int(w * 0.05)
        start_y = int(h * 0.35)
        
        active_visual_sets = [t.set_id for t in self.toggles_sets if t.value]
        cards_to_show = [c for c in self.all_cards if c.set in active_visual_sets]

        cards_per_row = 12
        total_gap = (cards_per_row + 1) * 10
        avail_w = w - (start_x * 2)
        
        thumb_w = (avail_w - total_gap) // cards_per_row
        if thumb_w < 40: thumb_w = 40
        thumb_h = int(thumb_w * 1.4)
        
        gap_x = 10
        gap_y = 10
        
        self.thumbnails = []
        for i, card in enumerate(cards_to_show):
            r = i // cards_per_row
            c = i % cards_per_row
            x = start_x + c * (thumb_w + gap_x)
            y = start_y + r * (thumb_h + gap_y)
            
            if y + thumb_h > h - 80: break 

            is_sel = True
            if self.config.active_card_ids: 
                is_sel = card.id in self.config.active_card_ids
            
            img = self.res_manager.get_image(card.image_path)
            fake_cache = {card.image_path: img}
            
            self.thumbnails.append(CardThumbnail(
                card, x, y, thumb_w, thumb_h, fake_cache, is_sel
            ))

        # --- BOUTONS ---
        btn_w, btn_h = 250, 50
        self.btn_back = Button(
            (cx - btn_w//2, h - 70, btn_w, btn_h), 
            "SAUVEGARDER & RETOUR", self.font, "BACK",
            color=COLOR_BTN_NORMAL
        )

        self.btn_yes = Button((cx - 110, cy + 40, 100, 50), "OUI", self.font_popup, "YES", color=COLOR_BTN_PLAY)
        self.btn_no = Button((cx + 10, cy + 40, 100, 50), "NON", self.font_popup, "NO", color=COLOR_BTN_QUIT)

    def run(self):
        """Boucle d'affichage des Paramètres."""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_config()
                    return "QUIT"
                
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self._init_layout()
                
                sets_changed = False
                for t_set in self.toggles_sets:
                    if t_set.handle_event(event):
                        sets_changed = True
                
                if sets_changed:
                    self._init_layout()
                    continue 

                if self.is_confirming:
                    if self.btn_yes.is_clicked(event):
                        self.save_config()
                        return "MENU"
                    if self.btn_no.is_clicked(event):
                        self.is_confirming = False
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                         self.is_confirming = False
                    continue 

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.is_confirming = True 
                    continue
                
                for tog in self.toggles_options: tog.handle_event(event)
                for thumb in self.thumbnails: thumb.handle_event(event)
                
                if self.btn_back.is_clicked(event):
                    self.is_confirming = True

            # DESSIN
            self.screen.fill(COLOR_BG_MENU)
            w, h = self.screen.get_size()
            
            t_opt = self.font_title.render("Options & Extensions", True, COLOR_BLACK)
            self.screen.blit(t_opt, (w * 0.05, h * 0.05))
            
            t_deck = self.font_title.render("Cartes Actives", True, COLOR_BLACK)
            self.screen.blit(t_deck, (w * 0.05, h * 0.28))
            
            nb_sel = sum(1 for t in self.thumbnails if t.is_selected)
            txt_count = self.font.render(f"Sélectionnées : {nb_sel} / {len(self.thumbnails)} (Total affiché)", True, (100, 100, 100))
            self.screen.blit(txt_count, (w * 0.4, h * 0.30))

            for tog in self.toggles_options: tog.draw(self.screen)
            for tog in self.toggles_sets: tog.draw(self.screen)
            
            for thumb in self.thumbnails: thumb.draw(self.screen)
            self.btn_back.draw(self.screen)
            
            if self.is_confirming:
                self.draw_popup()

            pygame.display.flip()
            self.clock.tick(FPS_CAP)

    def draw_popup(self):
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0,0))
        
        box_w, box_h = 500, 250
        cx, cy = w // 2, h // 2
        rect = pygame.Rect(cx - box_w//2, cy - box_h//2, box_w, box_h)
        
        pygame.draw.rect(self.screen, COLOR_BG_MENU, rect, border_radius=20)
        pygame.draw.rect(self.screen, COLOR_BLACK, rect, 4, border_radius=20)
        
        txt1 = self.font_title.render("Sauvegarder", True, COLOR_BLACK)
        txt2 = self.font.render("et retourner au menu ?", True, (50,50,50))
        
        t1_rect = txt1.get_rect(center=(cx, cy - 40))
        t2_rect = txt2.get_rect(center=(cx, cy))
        
        self.screen.blit(txt1, t1_rect)
        self.screen.blit(txt2, t2_rect)
        
        self.btn_yes.draw(self.screen)
        self.btn_no.draw(self.screen)

    def save_config(self):
        self.config.debug_mode = self.toggles_options[0].value
        self.config.enable_sound = self.toggles_options[1].value
        self.config.enable_effects = self.toggles_options[2].value
        
        new_active_sets = [t.set_id for t in self.toggles_sets if t.value]
        if not new_active_sets:
            if "FIRST_CONTACT" in self.available_sets:
                new_active_sets = ["FIRST_CONTACT"]
            elif self.available_sets:
                new_active_sets = [self.available_sets[0]]
        self.config.active_sets = new_active_sets

        visible_selected = {t.card.id for t in self.thumbnails if t.is_selected}
        previous_selected = set(self.config.active_card_ids) if self.config.active_card_ids else set()
        visible_ids = {t.card.id for t in self.thumbnails}
        hidden_selected = previous_selected - visible_ids
        final_ids = list(visible_selected.union(hidden_selected))
        
        if len(final_ids) == len(self.all_cards) or len(final_ids) == 0:
            self.config.active_card_ids = []
        else:
            self.config.active_card_ids = final_ids

        self.config.save_settings()
