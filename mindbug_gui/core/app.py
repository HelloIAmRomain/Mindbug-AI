import pygame
import sys
from .colors import BG_COLOR
from mindbug_engine.core.config import ConfigurationService
from .resource_manager import ResourceManager

# Imports pour le scan des données
from mindbug_engine.infrastructure.card_loader import CardLoader
from constants import PATH_DATA

from mindbug_engine.utils.logger import log_info, log_debug, log_error


class MindbugApp:
    """
    Classe principale de l'application (Contrôleur racine).
    Gère la fenêtre, la boucle principale, la configuration et la navigation.
    """

    def __init__(self):
        pygame.display.init()
        pygame.font.init()

        # Config UI (Résolution, Fullscreen) - Garder Config pour ça
        self.config = ConfigurationService()

        # Initialisation des Données (Sets de cartes)
        self._init_game_data()

        # Configuration Fenêtre
        w, h = getattr(self.config, "resolution", (1280, 720))
        flags = pygame.RESIZABLE

        # Support Fullscreen si défini dans config
        if getattr(self.config, "fullscreen", False):
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption("Mindbug AI - V2.0")

        # 5. Moteur de rendu & Ressources
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = 60
        self.res_manager = ResourceManager()

        self.current_screen = None

    def _init_game_data(self):
        """
        Scan le fichier JSON pour découvrir les extensions disponibles.
        Met à jour la config (pour l'écran Settings) et valide les sets actifs.
        """
        try:
            log_info(f"Chargement des données depuis : {PATH_DATA}")
            all_cards = CardLoader.load_from_json(PATH_DATA)

            # Extraction des sets uniques (triés alphabétiquement)
            available_sets = sorted(list(set(c.set for c in all_cards if hasattr(c, 'set'))))

            # Injection dans la config (variable volatile)
            self.config.available_sets_in_db = available_sets
            log_debug(f"Sets détectés : {available_sets}")

            # Validation : Si les sets actifs configurés n'existent plus, on reset
            valid_active = [s for s in self.config.active_sets if s in available_sets]

            if not valid_active and available_sets:
                log_debug("⚠️ Aucun set actif valide. Reset sur le premier set disponible.")
                self.config.active_sets = [available_sets[0]]
            elif valid_active:
                self.config.active_sets = valid_active

        except Exception as e:
            log_error(f"❌ ERREUR CRITIQUE chargement données : {e}")
            # Fallback pour ne pas crasher l'UI
            self.config.available_sets_in_db = ["First Contact"]
            self.config.active_sets = ["First Contact"]

    def set_screen(self, screen_instance):
        """Change l'écran actif."""
        self.current_screen = screen_instance
        if hasattr(self.current_screen, "on_enter"):
            self.current_screen.on_enter()

    def run(self):
        """Boucle principale (Game Loop)."""
        while self.running:
            dt = self.clock.tick(self.fps)

            # 1. Gestion des événements système
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._shutdown()
                    return
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)

            # 2. Gestion de l'écran courant
            if self.current_screen:
                # A. Input (retourne une action string ou None)
                action = self.current_screen.handle_events(events)
                if action:
                    self._handle_global_action(action)

                if self.running:  # Si on n'a pas quitté entre temps
                    # B. Update Logique
                    self.current_screen.update(dt)

                    # C. Rendu
                    self.screen.fill(BG_COLOR)
                    self.current_screen.draw(self.screen)

            pygame.display.flip()

        self._shutdown()

    def _handle_global_action(self, action):
        """
        Routeur de navigation centralisé (Controller).
        Reçoit des commandes textuelles (Intentions) et exécute la logique associée.
        Utilise des imports locaux pour éviter les cycles de dépendances.
        """
        if not action:
            return

        # =================================================================
        # 1. LOGIQUE DE JEU (Mise à jour du Modèle + Lancement)
        # =================================================================

        if action == "START_PVE":
            # Le bouton "Jouer Solo" a été cliqué
            self.config.game_mode = "PVE"
            self.config.save()  # On mémorise la préférence
            self._start_game()

        elif action == "START_PVP":
            # Le bouton "Jouer Local" a été cliqué -> Mode HOTSEAT
            self.config.game_mode = "HOTSEAT"
            self.config.save()
            self._start_game()

        # =================================================================
        # 2. NAVIGATION (Changement de Vue)
        # =================================================================

        elif action == "GOTO_SETTINGS":
            from mindbug_gui.screens.settings_screen import SettingsScreen
            self.set_screen(SettingsScreen(self))

        elif action == "MENU":
            from mindbug_gui.screens.menu_screen import MenuScreen
            self.set_screen(MenuScreen(self))

        # =================================================================
        # 3. SYSTÈME
        # =================================================================

        elif action == "QUIT_APP":
            self.running = False

    def _start_game(self):
        """Instancie et lance l'écran de jeu."""
        from mindbug_gui.screens.game_screen import GameScreen
        # Note : GameScreen lira la config (sets, difficulté) via self.app.config
        self.set_screen(GameScreen(self))

    def _handle_resize(self, w, h):
        """Gère le redimensionnement manuel de la fenêtre (souris)."""
        # On ne fait rien en plein écran pour éviter les conflits
        if not self.config.fullscreen:
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            if self.current_screen:
                self.current_screen.on_resize(w, h)

    def _shutdown(self):
        log_info("Fermeture de l'application...")
        pygame.quit()
        sys.exit()

    def apply_display_mode(self):
        """
        Applique le mode fenêtre ou plein écran selon la configuration.
        Utilise le mode 'Desktop Fullscreen' pour ne pas changer la résolution de l'OS.
        """
        # Récupération de la résolution cible pour le mode fenêtré
        target_res = getattr(self.config, "resolution", (1280, 720))

        if self.config.fullscreen:
            # (0, 0) indique à Pygame d'utiliser la résolution courante du bureau
            # C'est la méthode la plus sûre ("Desktop Fullscreen")
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            # Retour au mode fenêtré redimensionnable
            self.screen = pygame.display.set_mode(target_res, pygame.RESIZABLE)

        # IMPORTANT : On doit prévenir l'écran actuel que la taille a changé
        # pour qu'il recalcule la position des boutons/cartes
        if self.current_screen:
            w, h = self.screen.get_size()
            self.current_screen.on_resize(w, h)