from enum import Enum, auto
from dataclasses import dataclass

# --- 1. CONFIGURATION GLOBALE ---
@dataclass
class GameConfig:
    STARTING_HP: int = 3
    STARTING_MINDBUGS: int = 2
    HAND_SIZE: int = 5
    
    # Si True: On distribue 10 cartes par joueur (5 main, 5 pioche)
    # Si False: On pioche dans un deck infini (pour tests)
    USE_COMPETITIVE_SETUP: bool = True 

# LES PHASES DU JEU
class Phase(Enum):
    SETUP = auto()          
    P1_MAIN = auto()        # Tour du J1
    P2_MAIN = auto()        # Tour du J2
    MINDBUG_DECISION = auto() # Adversaire peut voler
    BLOCK_DECISION = auto()   # Adversaire peut bloquer
    RESOLUTION = auto()     # Application des dégâts
    GAME_OVER = auto()

# LES MOTS-CLÉS
class Keyword(Enum):
    POISON = "POISON"
    HUNTER = "HUNTER"
    SNEAKY = "SNEAKY"
    TOUGH = "TOUGH"
    FRENZY = "FRENZY"

# TYPES DE DÉCLENCHEURS (TRIGGERS)
class TriggerType(Enum):
    ON_PLAY = "ON_PLAY"
    ON_ATTACK = "ON_ATTACK"
    ON_BLOCK = "ON_BLOCK"
    ON_DEATH = "ON_DEATH"
    PASSIVE = "PASSIVE"


class CombatUtils:
    """
    Bibliothèque de fonctions statiques pour résoudre les conflits.
    """

    @staticmethod
    def can_block(attacker_card, blocker_card) -> bool:
        """
        Vérifie si un blocage est légal (Gestion du Furtif/Sneaky).
        """
        if Keyword.SNEAKY.value in attacker_card.keywords:
            # Un furtif ne peut être bloqué QUE par un furtif
            if Keyword.SNEAKY.value not in blocker_card.keywords:
                return False
        return True

    @staticmethod
    def simulate_combat(attacker, blocker):
        """
        Retourne le résultat théorique du combat SANS modifier l'état du jeu.
        Returns: (attacker_defeated, blocker_defeated)
        """
        att_dead = False
        blk_dead = False
        
        # 1. Comparaison de Puissance
        if attacker.power > blocker.power:
            blk_dead = True
        elif blocker.power > attacker.power:
            att_dead = True
        else:
            # Égalité
            att_dead = True
            blk_dead = True
            
        # 2. Gestion du Poison (Tue quoi qu'il arrive)
        if Keyword.POISON.value in attacker.keywords:
            blk_dead = True
        if Keyword.POISON.value in blocker.keywords:
            att_dead = True
            
        return att_dead, blk_dead
