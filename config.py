from settings import SettingsManager
from constants import PATH_DATA
from mindbug_engine.models import CardLoader

class GameConfig:
    def __init__(self):
        self.settings = SettingsManager()
        
        # 1. DÉCOUVERTE DYNAMIQUE
        # On demande au loader quels sets existent physiquement dans le JSON
        self.available_sets_in_db = CardLoader.get_available_sets(PATH_DATA)
        
        self.debug_mode = self.settings.debug_mode
        self.game_mode = self.settings.game_mode
        
        # 2. VALIDATION DES SETS ACTIFS
        # On récupère les sets sauvegardés par l'utilisateur
        saved_sets = self.settings.active_sets
        
        # On nettoie : si un set sauvegardé n'existe plus dans le JSON, on l'ignore
        valid_sets = [s for s in saved_sets if s in self.available_sets_in_db]
        
        # Si la liste est vide (premier lancement ou sets supprimés), on active tout par défaut
        if not valid_sets:
            self.active_sets = list(self.available_sets_in_db)
        else:
            self.active_sets = valid_sets

        self.active_card_ids = self.settings.active_card_ids 
        self.enable_sound = self.settings.enable_sound
        self.enable_effects = self.settings.enable_effects

    def save_settings(self):
        self.settings.game_mode = self.game_mode
        self.settings.debug_mode = self.debug_mode
        self.settings.active_sets = self.active_sets
        self.settings.active_card_ids = self.active_card_ids 
        self.settings.enable_sound = self.enable_sound
        self.settings.enable_effects = self.enable_effects
        
        self.settings.save()
