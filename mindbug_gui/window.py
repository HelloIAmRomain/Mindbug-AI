import pygame
from constants import FPS_CAP
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase
from .renderer import GameRenderer
from .resource_manager import ResourceManager

class MindbugGUI:
    """
    CONTROLEUR PRINCIPAL (JEU).
    
    Responsabilités :
    1. Initialiser le Moteur (Engine), la Vue (Renderer) et les Ressources.
    2. Gérer la boucle de jeu (Game Loop).
    3. Traiter les entrées (Souris/Clavier) et les convertir en actions de jeu.
    """
    
    def __init__(self, config, screen=None):
        self.config = config
        self.clock = pygame.time.Clock()

        # 1. Initialisation Pygame & Écran
        if not pygame.get_init():
            pygame.init()

        if screen:
            self.screen = screen
        else:
            w, h = self.config.settings.resolution
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            pygame.display.set_caption("Mindbug AI")

        # 2. Gestionnaire de Ressources (Centralisé)
        self.res_manager = ResourceManager()

        # 3. Initialisation du Moteur (Engine)
        # On récupère les sets actifs depuis la config (gérée par settings.py)
        active_sets = getattr(self.config, "active_sets", None)
        self.game = MindbugGame(
            active_card_ids=self.config.active_card_ids,
            active_sets=active_sets
        )
        
        # 4. Initialisation du Rendu (Renderer)
        # On lui passe le resource manager pour qu'il ne charge pas ses propres images
        self.renderer = GameRenderer(self.screen, self.game, self.config, self.res_manager)
        
        # 5. États de l'interface
        self.viewing_discard_owner = None # Overlay défausse actif ?
        self.is_paused = False            # Menu Echap actif ?

        # 6. Gestion du Mode Hotseat (Rideau)
        self.last_active_player = self.game.active_player
        self.show_curtain = False
        
        if self.config.game_mode == "HOTSEAT" and not self.config.debug_mode:
             self.show_curtain = True

    def run(self):
        """Boucle principale de la partie."""
        running = True
        
        # Premier rendu initial
        self.renderer.render_all(self.viewing_discard_owner, self.is_paused, self.show_curtain)
        pygame.display.flip()

        while running:
            # --- A. Gestion du Tour (Hotseat) ---
            self._handle_hotseat_turn_change()

            # --- B. Gestion des Événements ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)

                elif self.show_curtain:
                    # N'importe quelle touche enlève le rideau
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                        self.show_curtain = False
                
                else:
                    # Input Jeu standard
                    action = self._handle_input(event)
                    if action == "MENU": return "MENU"
                    if action == "QUIT": return "QUIT"

            # --- C. Logique UI Automatique ---
            self._handle_auto_discard_view()

            # --- D. Rendu ---
            self.renderer.render_all(
                viewing_discard_owner=self.viewing_discard_owner,
                is_paused=self.is_paused,
                show_curtain=self.show_curtain
            )
            
            pygame.display.flip()
            self.clock.tick(FPS_CAP)
        
        return "MENU"

    # -------------------------------------------------------------------------
    # GESTION ÉVÉNEMENTS & INPUTS
    # -------------------------------------------------------------------------

    def _handle_resize(self, w, h):
        """Met à jour la fenêtre et notifie le renderer."""
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.renderer.handle_resize(w, h)
        # Force un rendu immédiat
        self.renderer.render_all(self.viewing_discard_owner, self.is_paused, self.show_curtain)
        pygame.display.flip()

    def _handle_hotseat_turn_change(self):
        """Active le rideau si le joueur actif change (en mode Hotseat)."""
        if getattr(self.config, "game_mode", "HOTSEAT") == "HOTSEAT" and not self.config.debug_mode:
            if self.game.active_player != self.last_active_player:
                self.show_curtain = True
                self.last_active_player = self.game.active_player
                self.viewing_discard_owner = None
                self.renderer.zoomed_card = None 

    def _handle_input(self, event):
        """Dispatche les événements Clavier/Souris."""
        
        # 1. CLAVIER (Echap)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.is_paused: 
                    self.is_paused = False
                elif self.viewing_discard_owner: 
                    self.viewing_discard_owner = None
                elif self.renderer.zoomed_card: 
                    self.renderer.zoomed_card = None
                else: 
                    self.is_paused = True
            return None

        # 2. SOURIS (Clic)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Clic Droit : Zoom
            if event.button == 3: 
                self._try_zoom_card(pygame.mouse.get_pos())
            # Clic Gauche : Action
            elif event.button == 1:
                if self.renderer.zoomed_card:
                    self.renderer.zoomed_card = None # Clic ferme le zoom
                else:
                    return self._handle_left_click(event.pos)

        # 3. SOURIS (Relâchement)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3: # Relâcher le clic droit ferme le zoom
                self.renderer.zoomed_card = None

        return None

    def _try_zoom_card(self, mouse_pos):
        """Tente de zoomer sur une carte sous la souris (si visible)."""
        for zone in self.renderer.click_zones:
            if zone["rect"].collidepoint(mouse_pos) and zone["index"] != -1:
                
                # Vérification Visibilité (Anti-Triche)
                z_type = zone["type"]
                can_see_everything = self.config.debug_mode or (getattr(self.config, "game_mode", "") == "DEV")
                
                if not can_see_everything:
                    # En Hotseat, on ne peut pas zoomer la main adverse
                    if "HAND_P1" in z_type and self.game.active_player != self.game.player1: return
                    if "HAND_P2" in z_type and self.game.active_player != self.game.player2: return

                card = self._get_card_from_zone(z_type, zone["index"])
                if card:
                    self.renderer.zoomed_card = card
                return

    def _handle_left_click(self, pos):
        """Gère la logique principale des clics (Interface & Jeu)."""
        
        # A. Menu Pause (Prioritaire)
        if self.is_paused:
            for zone in self.renderer.click_zones:
                if zone["rect"].collidepoint(pos):
                    if zone["type"] == "CONFIRM_QUIT": return "MENU"
                    if zone["type"] == "CANCEL_QUIT": self.is_paused = False
            return None

        # B. Bouton Menu Système (Engrenage)
        for zone in self.renderer.click_zones:
            if zone["type"] == "TOGGLE_MENU" and zone["rect"].collidepoint(pos):
                self.is_paused = True
                return None

        if self.game.winner: return None

        # C. Actions de Jeu
        legal_moves = self.game.get_legal_moves()
        
        for zone in self.renderer.click_zones:
            if zone["rect"].collidepoint(pos):
                action_type = zone["type"]
                idx = zone["index"]
                
                # --- Cas 1 : Overlay Défausse ---
                if self.viewing_discard_owner:
                    if action_type == "OVERLAY_CARD":
                        is_p1 = (self.viewing_discard_owner == self.game.player1)
                        key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
                        if (key, idx) in legal_moves:
                            self.game.step(key, idx)
                            self.viewing_discard_owner = None 
                    continue # On ignore les clics hors overlay
                
                # --- Cas 2 : Interaction Standard ---
                if self.viewing_discard_owner: continue # Sécurité

                # Ouverture Défausses
                if action_type == "DISCARD_PILE_P1":
                    self.viewing_discard_owner = self.game.player1
                    return None
                elif action_type == "DISCARD_PILE_P2":
                    self.viewing_discard_owner = self.game.player2
                    return None

                # Boutons UI
                if action_type == "BTN_MINDBUG" and ("MINDBUG", -1) in legal_moves:
                    self.game.step("MINDBUG", -1)
                    return None
                elif action_type == "BTN_PASS" and ("PASS", -1) in legal_moves:
                    self.game.step("PASS", -1)
                    return None
                elif action_type == "BTN_NO_BLOCK" and ("NO_BLOCK", -1) in legal_moves:
                    self.game.step("NO_BLOCK", -1)
                    return None

                # Cartes (Main / Plateau)
                engine_action = self._resolve_card_click(action_type, idx, legal_moves)
                if engine_action:
                    self.game.step(engine_action[0], engine_action[1])
                    return None

        # D. Clic dans le vide (Fermer Overlay)
        if self.viewing_discard_owner:
            self.viewing_discard_owner = None
            
        return None

    def _resolve_card_click(self, action_type, idx, legal_moves):
        """Traduit un clic sur une carte en action moteur."""
        # 1. Sélection (Ciblage)
        if self.game.phase == Phase.RESOLUTION_CHOICE:
            candidate = (f"SELECT_{action_type}", idx)
            if candidate in legal_moves:
                return candidate

        # 2. Action du Joueur Actif
        is_p1_zone = "P1" in action_type
        zone_owner = self.game.player1 if is_p1_zone else self.game.player2
        
        if zone_owner == self.game.active_player:
            if "HAND" in action_type and ("PLAY", idx) in legal_moves:
                return ("PLAY", idx)
            elif "BOARD" in action_type:
                if self.game.phase == Phase.BLOCK_DECISION and ("BLOCK", idx) in legal_moves:
                    return ("BLOCK", idx)
                elif self.game.phase in [Phase.P1_MAIN, Phase.P2_MAIN] and ("ATTACK", idx) in legal_moves:
                    return ("ATTACK", idx)
        
        return None

    # -------------------------------------------------------------------------
    # UTILITAIRES
    # -------------------------------------------------------------------------

    def _handle_auto_discard_view(self):
        """Ouvre automatiquement la défausse si une sélection y est requise."""
        if self.game.phase == Phase.RESOLUTION_CHOICE and self.game.selection_context:
            candidates = self.game.selection_context.get("candidates", [])
            if candidates and not self.viewing_discard_owner:
                # On regarde où est la première carte candidate pour ouvrir la bonne pile
                sample = candidates[0]
                if sample in self.game.player1.discard:
                    self.viewing_discard_owner = self.game.player1
                elif sample in self.game.player2.discard:
                    self.viewing_discard_owner = self.game.player2

    def _get_card_from_zone(self, zone_type, index):
        """Récupère l'objet Card depuis la zone et l'index (pour le Zoom)."""
        if index == -1: return None
        
        if "HAND_P1" in zone_type: return self.game.player1.hand[index]
        if "BOARD_P1" in zone_type: return self.game.player1.board[index]
        if "HAND_P2" in zone_type: return self.game.player2.hand[index]
        if "BOARD_P2" in zone_type: return self.game.player2.board[index]
        
        if "OVERLAY_CARD" in zone_type and self.viewing_discard_owner:
            try:
                return self.viewing_discard_owner.discard[index]
            except IndexError:
                return None
                
        return None
