import pygame
import os
from constants import * # Import colors and paths
from .components import Button, Toggle, CardThumbnail
from mindbug_engine.models import CardLoader

class MenuScreen:
    """Écran principal du jeu : Jouer (Local), Options, Quitter."""
    
    def __init__(self, screen, config):
        self.screen = screen
        self.config = config
        self.clock = pygame.time.Clock()
        
        # Initialisation unique des polices
        self.font_title = pygame.font.SysFont("Arial", 80, bold=True)
        self.font_btn = pygame.font.SysFont("Arial", 40, bold=True)
        
        self.buttons = []
        self._init_layout() # Calcul des positions initiales

    def _init_layout(self):
        """Recalcule la position des éléments selon la taille actuelle de la fenêtre."""
        w, h = self.screen.get_size()
        cx = w // 2
        cy = h // 2
        
        # Dimensions relatives (ex: 25% de la largeur)
        btn_w = int(w * 0.25) 
        btn_h = int(h * 0.10) 
        if btn_h > 80: btn_h = 80 # Max height
        
        gap = int(btn_h * 1.2)
        
        self.buttons = [
            # NOUVEAU : Bouton Jouer Local (Hotseat)
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
            # 1. Gestion des Événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                # --- GESTION DU REDIMENSIONNEMENT ---
                elif event.type == pygame.VIDEORESIZE:
                    # On applique la nouvelle taille
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    # On recalcule les positions des boutons
                    self._init_layout() 
                
                # Raccourci Clavier
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return "QUIT"
                
                # Clics Boutons
                for btn in self.buttons:
                    if btn.is_clicked(event):
                        # GESTION DES MODES DE JEU
                        if btn.action_id == "PLAY_HOTSEAT":
                            self.config.game_mode = "HOTSEAT"
                            return "PLAY" # Le main.py lancera le jeu
                        
                        return btn.action_id

            # 2. Dessin
            self.screen.fill(COLOR_BG_MENU)
            
            w, h = self.screen.get_size()
            
            # Titre (Centré haut, relatif)
            title = self.font_title.render("MINDBUG AI", True, COLOR_BLACK)
            title_rect = title.get_rect(center=(w // 2, h * 0.15))
            self.screen.blit(title, title_rect)
            
            # Boutons
            for btn in self.buttons:
                btn.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS_CAP)
            
        return "QUIT"


class SettingsScreen:
    """Écran de configuration et de sélection de deck."""
    
    def __init__(self, screen, config):
        self.screen = screen
        self.config = config
        self.clock = pygame.time.Clock()
        
        self.font = pygame.font.SysFont("Arial", 20)
        self.font_title = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_popup = pygame.font.SysFont("Arial", 30, bold=True)
        
        self.is_confirming = False
        
        # Données (chargement une seule fois)
        self.all_cards = CardLoader.load_deck(PATH_DATA)
        self.img_cache = self._load_images()
        
        # UI Elements (initialisés dans _init_layout)
        self.toggles = []
        self.thumbnails = []
        self.btn_back = None
        self.btn_yes = None
        self.btn_no = None
        
        self._init_layout()

    def _load_images(self):
        cache = {}
        if os.path.exists(PATH_ASSETS):
            for card in self.all_cards:
                if not card.image_path: 
                    cache[card.image_path] = None
                    continue
                path = os.path.join(PATH_ASSETS, card.image_path)
                if os.path.exists(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        cache[card.image_path] = img
                    except: cache[card.image_path] = None
                else: cache[card.image_path] = None
        return cache

    def _init_layout(self):
        """Recalcule la grille et les boutons selon la taille d'écran."""
        w, h = self.screen.get_size()
        cx, cy = w // 2, h // 2
        
        # --- OPTIONS (Toggles) ---
        opt_y = int(h * 0.15)
        col1_x = int(w * 0.2)
        col2_x = int(w * 0.6)
        
        self.toggles = [
            Toggle(col1_x, opt_y, "Mode Debug (Voir mains)", self.font, initial_value=self.config.debug_mode),
            Toggle(col1_x, opt_y + 50, "Effets Sonores (Bientôt)", self.font, initial_value=self.config.enable_sound),
            Toggle(col2_x, opt_y, "Animations (Bientôt)", self.font, initial_value=self.config.enable_effects),
        ]
        
        # --- DECK BUILDER (Grille) ---
        start_x = int(w * 0.05)
        start_y = int(h * 0.35)
        
        # Calcul taille miniature dynamique
        cards_per_row = 12
        total_gap = (cards_per_row + 1) * 10
        avail_w = w - (start_x * 2)
        
        thumb_w = (avail_w - total_gap) // cards_per_row
        if thumb_w < 40: thumb_w = 40 # Minimum vital
        thumb_h = int(thumb_w * 1.4)
        
        gap_x = 10
        gap_y = 10
        
        # Recréation des thumbnails
        self.thumbnails = []
        for i, card in enumerate(self.all_cards):
            r = i // cards_per_row
            c = i % cards_per_row
            x = start_x + c * (thumb_w + gap_x)
            y = start_y + r * (thumb_h + gap_y)
            
            # Stop si on dépasse le bouton retour en bas
            if y + thumb_h > h - 80: break 

            is_sel = True
            if self.config.active_card_ids: 
                is_sel = card.id in self.config.active_card_ids
            
            self.thumbnails.append(CardThumbnail(
                card, x, y, thumb_w, thumb_h, self.img_cache, is_sel
            ))

        # --- BOUTONS ---
        btn_w, btn_h = 250, 50
        self.btn_back = Button(
            (cx - btn_w//2, h - 70, btn_w, btn_h), 
            "VALIDER & RETOUR", self.font, "BACK",
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
                
                # --- REDIMENSIONNEMENT ---
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self._init_layout()
                
                # --- MODE POPUP ---
                if self.is_confirming:
                    if self.btn_yes.is_clicked(event):
                        self.save_config()
                        return "MENU"
                    if self.btn_no.is_clicked(event):
                        self.is_confirming = False
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                         self.is_confirming = False
                    continue 

                # --- MODE NORMAL ---
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.is_confirming = True 
                    continue
                
                if self.toggles[0].handle_event(event):
                    self.config.debug_mode = self.toggles[0].value
                
                for thumb in self.thumbnails:
                    thumb.handle_event(event)
                
                if self.btn_back.is_clicked(event):
                    self.is_confirming = True

            # DESSIN
            self.screen.fill(COLOR_BG_MENU)
            
            w, h = self.screen.get_size()
            
            # Titres (Positions relatives)
            t_opt = self.font_title.render("Options", True, COLOR_BLACK)
            self.screen.blit(t_opt, (w * 0.05, h * 0.05))
            
            t_deck = self.font_title.render("Sélection des Cartes", True, COLOR_BLACK)
            self.screen.blit(t_deck, (w * 0.05, h * 0.28))
            
            nb_sel = sum(1 for t in self.thumbnails if t.is_selected)
            txt_count = self.font.render(f"Sélectionnées : {nb_sel} / {len(self.all_cards)}", True, (100, 100, 100))
            self.screen.blit(txt_count, (w * 0.4, h * 0.30))

            for tog in self.toggles: tog.draw(self.screen)
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
        self.config.debug_mode = self.toggles[0].value
        selected_ids = [t.card.id for t in self.thumbnails if t.is_selected]
        if len(selected_ids) == len(self.all_cards) or len(selected_ids) == 0:
            self.config.active_card_ids = []
        else:
            self.config.active_card_ids = selected_ids
