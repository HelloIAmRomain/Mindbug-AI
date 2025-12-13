import pygame
from constants import FPS_CAP
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase
from .renderer import GameRenderer

class MindbugGUI:
    """
    CONTROLEUR : Gère la boucle de jeu, les entrées utilisateurs (souris/clavier)
    et fait le lien entre le Moteur (Engine) et la Vue (Renderer).
    """
    def __init__(self, config, screen=None):
        """
        Initialise le contrôleur.
        """
        # 1. Récupération de l'écran
        if screen is not None:
            self.screen = screen
        else:
            self.screen = pygame.display.get_surface()

        self.clock = pygame.time.Clock()
        self.config = config
        
        # 2. Initialisation du Moteur (Modèle)
        self.game = MindbugGame(active_card_ids=self.config.active_card_ids)
        
        # 3. Initialisation du Rendu (Vue)
        self.renderer = GameRenderer(self.screen, self.game, debug_mode=self.config.debug_mode)
        
        # 4. États de l'interface
        self.viewing_discard_owner = None # Si non None, affiche l'overlay défausse
        self.is_paused = False            # Si True, jeu figé + popup

        # 5. Gestion des Modes de Jeu (HOTSEAT)
        self.last_active_player = self.game.active_player
        self.show_curtain = False
        
        # Si on lance en Hotseat, on active le rideau dès le début
        if getattr(self.config, "game_mode", "HOTSEAT") == "HOTSEAT":
             self.show_curtain = True

    def run(self):
        """Boucle principale de la phase de jeu."""
        running = True
        
        # Premier rendu pour initialiser les click_zones
        self.renderer.render_all(self.viewing_discard_owner, self.is_paused, self.show_curtain)
        pygame.display.flip()

        while running:
            
            # --- 0. LOGIQUE HOTSEAT (Changement de tour) ---
            if getattr(self.config, "game_mode", "HOTSEAT") == "HOTSEAT":
                if self.game.active_player != self.last_active_player:
                    self.show_curtain = True
                    self.last_active_player = self.game.active_player
                    self.viewing_discard_owner = None # Fermer les overlays
                    # On annule aussi le zoom si actif
                    self.renderer.zoomed_card = None 
            
            # --- 1. BOUCLE D'ÉVÉNEMENTS ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                
                # Gestion du redimensionnement fenêtre
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)

                # Gestion du Rideau (prioritaire sur tout le reste)
                elif self.show_curtain:
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                        self.show_curtain = False
                
                # Gestion des Inputs Jeu (Souris/Clavier)
                else:
                    action = self._handle_input(event)
                    if action == "MENU": return "MENU"
                    if action == "QUIT": return "QUIT"

            # --- 2. LOGIQUE AUTOMATIQUE (Auto-Défausse) ---
            self._handle_auto_discard_view()

            # --- 3. RENDU ---
            self.renderer.render_all(
                viewing_discard_owner=self.viewing_discard_owner,
                is_paused=self.is_paused,
                show_curtain=self.show_curtain
            )
            
            pygame.display.flip()
            self.clock.tick(FPS_CAP)
        
        return "MENU"

    def _handle_resize(self, w, h):
        """Gère le redimensionnement de la fenêtre."""
        self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
        self.renderer.handle_resize(w, h)
        # Rendu immédiat pour éviter écran noir pendant le drag
        self.renderer.render_all(self.viewing_discard_owner, self.is_paused, self.show_curtain)
        pygame.display.flip()

    def _handle_auto_discard_view(self):
        """Ouvre automatiquement la défausse si le jeu demande d'en choisir une carte."""
        if self.game.phase == Phase.RESOLUTION_CHOICE and self.game.selection_context:
            candidates = self.game.selection_context.get("candidates", [])
            if candidates and not self.viewing_discard_owner:
                sample = candidates[0]
                if sample in self.game.player1.discard:
                    self.viewing_discard_owner = self.game.player1
                elif sample in self.game.player2.discard:
                    self.viewing_discard_owner = self.game.player2

    def _handle_input(self, event):
        """Traite les événements bruts (Clavier + Souris avec Zoom)."""
        
        # --- A. CLAVIER ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.is_paused: self.is_paused = False
                elif self.viewing_discard_owner: self.viewing_discard_owner = None
                elif self.renderer.zoomed_card: self.renderer.zoomed_card = None # Echap ferme le zoom
                else: self.is_paused = True
            return None

        # --- B. SOURIS (Clic Enfoncé) ---
        elif event.type == pygame.MOUSEBUTTONDOWN:
            
            # >>> 1. CLIC DROIT : ACTIVER LE ZOOM <<<
            if event.button == 3: 
                mouse_pos = pygame.mouse.get_pos()
                
                for zone in self.renderer.click_zones:
                    if zone["rect"].collidepoint(mouse_pos) and zone["index"] != -1:
                        
                        # --- SECURITE : VÉRIFICATION DE LA VISIBILITÉ ---
                        z_type = zone["type"]
                        is_hidden = False
                        
                        # Si on n'est pas en mode debug, on vérifie les mains adverses
                        if not getattr(self.config, "debug_mode", False):
                            # Si c'est la main du J1 mais que c'est au tour du J2
                            if "HAND_P1" in z_type and self.game.active_player != self.game.player1:
                                is_hidden = True
                            # Si c'est la main du J2 mais que c'est au tour du J1
                            elif "HAND_P2" in z_type and self.game.active_player != self.game.player2:
                                is_hidden = True
                        
                        # Si la carte est cachée, on ne fait RIEN (on ne zoome pas)
                        if is_hidden:
                            continue 
                        # -----------------------------------------------

                        card_found = self._get_card_from_zone(z_type, zone["index"])
                        if card_found:
                            self.renderer.zoomed_card = card_found
                return None

            # >>> 2. CLIC GAUCHE : ACTION OU FERMER ZOOM <<<
            elif event.button == 1:
                # Si un zoom est actif, le clic gauche le ferme
                if self.renderer.zoomed_card:
                    self.renderer.zoomed_card = None
                    return None
                
                # Sinon, c'est un clic normal de jeu
                return self._handle_click(event.pos)

        # --- C. SOURIS (Clic Relâché) ---
        elif event.type == pygame.MOUSEBUTTONUP:
            # >>> 3. RELÂCHEMENT CLIC DROIT : FERMER LE ZOOM <<<
            # (Optionnel : permet l'effet "Maintenir pour voir")
            if event.button == 3:
                self.renderer.zoomed_card = None

        return None

    def _get_card_from_zone(self, zone_type, index):
        """Helper pour récupérer l'objet Carte depuis un type de zone et un index."""
        if index == -1: return None
        
        if "HAND_P1" in zone_type: return self.game.player1.hand[index]
        if "BOARD_P1" in zone_type: return self.game.player1.board[index]
        if "HAND_P2" in zone_type: return self.game.player2.hand[index]
        if "BOARD_P2" in zone_type: return self.game.player2.board[index]
        
        # Gestion Overlay Défausse
        if "OVERLAY_CARD" in zone_type and self.viewing_discard_owner:
            try:
                return self.viewing_discard_owner.discard[index]
            except IndexError:
                return None
                
        return None

    def _handle_click(self, pos):
        """
        Gère la logique métier des clics gauches (Jouer, Passer, etc.).
        """
        # --- 1. GESTION MENU PAUSE ---
        if self.is_paused:
            for zone in self.renderer.click_zones:
                if zone["rect"].collidepoint(pos):
                    if zone["type"] == "CONFIRM_QUIT": return "MENU"
                    if zone["type"] == "CANCEL_QUIT": 
                        self.is_paused = False
            return None # Bloque le reste

        # --- 2. BOUTON MENU SYSTÈME ---
        for zone in self.renderer.click_zones:
            if zone["type"] == "TOGGLE_MENU" and zone["rect"].collidepoint(pos):
                self.is_paused = True
                return None

        if self.game.winner: return None

        # --- 3. LOGIQUE DU JEU ---
        legal_moves = self.game.get_legal_moves()
        
        for zone in self.renderer.click_zones:
            if zone["rect"].collidepoint(pos):
                action_type = zone["type"]
                idx = zone["index"]
                
                # A. INTERACTION OVERLAY DÉFAUSSE
                if self.viewing_discard_owner:
                    if action_type == "OVERLAY_CARD":
                        is_p1 = (self.viewing_discard_owner == self.game.player1)
                        key = "SELECT_DISCARD_P1" if is_p1 else "SELECT_DISCARD_P2"
                        if (key, idx) in legal_moves:
                            self.game.step(key, idx)
                            self.viewing_discard_owner = None 
                        return None
                    continue # Ignore les autres clics si overlay ouvert

                if self.viewing_discard_owner: continue

                # B. OUVERTURE DÉFAUSSES
                if action_type == "DISCARD_PILE_P1":
                    self.viewing_discard_owner = self.game.player1
                    return None
                elif action_type == "DISCARD_PILE_P2":
                    self.viewing_discard_owner = self.game.player2
                    return None

                # C. BOUTONS
                if action_type == "BTN_MINDBUG": 
                    if ("MINDBUG", -1) in legal_moves: self.game.step("MINDBUG", -1)
                    return None
                elif action_type == "BTN_PASS": 
                    if ("PASS", -1) in legal_moves: self.game.step("PASS", -1)
                    return None
                elif action_type == "BTN_NO_BLOCK": 
                    if ("NO_BLOCK", -1) in legal_moves: self.game.step("NO_BLOCK", -1)
                    return None

                # D. CARTES (MAIN & BOARD)
                is_p1_zone = "P1" in action_type
                zone_owner = self.game.player1 if is_p1_zone else self.game.player2
                engine_action = None

                # D1 : Ciblage
                if self.game.phase == Phase.RESOLUTION_CHOICE:
                    candidate = (f"SELECT_{action_type}", idx)
                    if candidate in legal_moves:
                        engine_action = candidate

                # D2 : Action Joueur Actif
                elif zone_owner == self.game.active_player:
                    if "HAND" in action_type:
                        if ("PLAY", idx) in legal_moves: engine_action = ("PLAY", idx)
                    elif "BOARD" in action_type:
                        if self.game.phase == Phase.BLOCK_DECISION:
                            if ("BLOCK", idx) in legal_moves: engine_action = ("BLOCK", idx)
                        elif self.game.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
                             if ("ATTACK", idx) in legal_moves: engine_action = ("ATTACK", idx)

                if engine_action:
                    self.game.step(engine_action[0], engine_action[1])
                    return None

        # --- 4. CLIC DANS LE VIDE (Fermer Overlay) ---
        if self.viewing_discard_owner:
            self.viewing_discard_owner = None
            
        return None
