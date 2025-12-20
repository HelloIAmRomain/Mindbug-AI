from settings import SettingsManager
from constants import PATH_DATA
from mindbug_engine.infrastructure.card_loader import CardLoader

class GameConfig:
    """
    Façade de configuration utilisée par le jeu.
    Fait le lien entre les Settings (disque) et la logique runtime (sets valides).
    """
    def __init__(self):
        self.settings = SettingsManager()

        # 1. DÉCOUVERTE DYNAMIQUE
        # On demande au loader quels sets existent physiquement dans le JSON
        self.available_sets_in_db = CardLoader.get_available_sets(PATH_DATA)

        # 2. CHARGEMENT & VALIDATION INITIALE
        self.load_settings()

    def load_settings(self):
        """Rafraîchit la config depuis le manager."""
        self.settings.load()
        
        self.debug_mode = self.settings.debug_mode
        self.game_mode = self.settings.game_mode
        self.ai_difficulty = self.settings.ai_difficulty # <--- NOUVEAU
        
        # Audio / FX
        self.enable_sound = self.settings.enable_sound
        self.enable_effects = self.settings.enable_effects
        
        # Deck Builder
        self.active_card_ids = self.settings.active_card_ids

        # Gestion des Sets (Nettoyage si des sets ont été supprimés du JSON)
        saved_sets = self.settings.active_sets
        valid_sets = [s for s in saved_sets if s in self.available_sets_in_db]

        # Si aucun set valide (ou premier lancement), on active tout par défaut
        if not valid_sets:
            self.active_sets = list(self.available_sets_in_db)
        else:
            self.active_sets = valid_sets

    def save_settings(self):
        """Pousse les valeurs actuelles vers le manager et sauvegarde sur disque."""
        self.settings.game_mode = self.game_mode
        self.settings.debug_mode = self.debug_mode
        self.settings.ai_difficulty = self.ai_difficulty # <--- NOUVEAU
        
        self.settings.active_sets = self.active_sets
        self.settings.active_card_ids = self.active_card_ids
        
        self.settings.enable_sound = self.enable_sound
        self.settings.enable_effects = self.enable_effects

        self.settings.save()
