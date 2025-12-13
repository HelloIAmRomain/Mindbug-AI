from constants import CARD_ASPECT_RATIO

class DynamicLayout:
    """
    Gestionnaire de mise en page (Version Optimisée V2).
    - Cartes plus grandes (20% hauteur).
    - Interface décalée pour éviter les chevauchements.
    - Espace central réduit au minimum.
    """
    
    def __init__(self, w, h):
        self.update(w, h)

    def update(self, w, h):
        self.screen_w = w
        self.screen_h = h
        
        # --- 1. DIMENSIONS VERTICALES (Le nerf de la guerre) ---
        
        # Zone réservée en haut (pour le Bouton Menu et le Texte Phase)
        # On descend tout le jeu de cette valeur pour ne rien cacher.
        self.header_h = int(h * 0.08) 
        
        # Marge bas (Barre des tâches)
        self.footer_h = int(h * 0.05)
        
        # Hauteur d'une carte : 20% de l'écran
        # (4 rangées * 20% = 80% de l'écran occupé par les cartes)
        self.card_h = int(h * 0.20)
        self.card_w = int(self.card_h * CARD_ASPECT_RATIO)
        
        # Ecart vertical entre Main et Plateau (très fin pour resserrer)
        self.row_gap = int(h * 0.02) 

        # --- 2. POSITIONS Y (Hauteur) ---
        
        # JOUEUR 2 (Adversaire - Haut)
        # Sa main commence juste sous le header
        self.p2_hand_y = self.header_h
        self.p2_piles_y = self.p2_hand_y
        
        # Son plateau est juste en dessous de sa main
        self.p2_board_y = self.p2_hand_y + self.card_h + self.row_gap
        
        # JOUEUR 1 (Vous - Bas)
        # Sa main est collée à la marge du bas
        self.p1_hand_y = h - self.card_h - self.footer_h
        self.p1_piles_y = self.p1_hand_y
        
        # Son plateau est juste au-dessus de sa main
        self.p1_board_y = self.p1_hand_y - self.card_h - self.row_gap

        # --- 3. POSITIONS X (Largeur) ---
        
        # Marges latérales pour les piles
        self.side_margin = int(w * 0.02)
        
        # Défausse à Gauche
        self.pile_left_x = self.side_margin
        
        # Pioche à Droite
        self.pile_right_x = w - self.side_margin - self.card_w
        
        # Ecart horizontal entre les cartes en main/board
        self.card_gap = int(w * 0.012) 

        # --- 4. HUD & TEXTES ---
        
        # Phase/Tour : Tout en haut à gauche (dans le header)
        self.hud_x = self.side_margin
        self.hud_phase_y = int(self.header_h * 0.2)
        self.hud_turn_y = int(self.header_h * 0.55)
        
        # STATS (PV/MB)
        # On les place à gauche, ALIGNÉES avec la pile de défausse
        # Mais verticalement situées ENTRE la main et le plateau pour être lisibles
        
        # Stats J2 : Entre sa main et son plateau
        self.stats_x = self.side_margin
        self.stats_p2_y = self.p2_hand_y + self.card_h + 20 # Juste sous sa main
        
        # Stats J1 : Entre sa main et son plateau
        self.stats_p1_y = self.p1_hand_y - 40 # Juste au dessus de sa main
        
        # Message Central ("Cliquez sur...")
        # Exactement au milieu de l'espace vide central
        center_void_y = (self.p2_board_y + self.card_h + self.p1_board_y) // 2
        self.msg_center_y = center_void_y

        # --- 5. BOUTONS ---
        
        # Bouton Menu (Haut Droite - Dans le header)
        self.btn_menu_w = int(w * 0.08)
        if self.btn_menu_w < 80: self.btn_menu_w = 80
        self.btn_menu_h = int(self.header_h * 0.6)
        
        self.btn_menu_x = w - self.side_margin - self.btn_menu_w
        self.btn_menu_y = int(self.header_h * 0.2)
        
        # Boutons Contextuels (Mindbug/Passer)
        # À droite, sous la pioche J2
        self.btn_w = int(w * 0.10)
        self.btn_h = int(h * 0.05)
        
        self.btn_ctx_x = w - int(w * 0.12)
        self.btn_ctx_y = h // 2
        
        # --- 6. POLICES ---
        self.font_size_small = max(10, int(h * 0.015))
        self.font_size_std = max(14, int(h * 0.020))
        self.font_size_title = max(18, int(h * 0.025))
        self.font_size_huge = max(24, int(h * 0.04))

    def get_row_start_x(self, count):
        """Centre horizontalement une rangée de cartes."""
        total_w = count * self.card_w + (count - 1) * self.card_gap
        return (self.screen_w - total_w) // 2
