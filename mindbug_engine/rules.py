from enum import Enum, auto
from dataclasses import dataclass

@dataclass
class GameConfig:
    STARTING_HP: int = 3
    STARTING_MINDBUGS: int = 2
    HAND_SIZE: int = 5
    USE_COMPETITIVE_SETUP: bool = True 

class Phase(Enum):
    SETUP = auto()          
    P1_MAIN = auto()        
    P2_MAIN = auto()        
    MINDBUG_DECISION = auto() 
    BLOCK_DECISION = auto()   
    RESOLUTION = auto()     
    RESOLUTION_CHOICE = auto() # Attente action du joueur
    GAME_OVER = auto()

class Keyword(Enum):
    POISON = "POISON"
    HUNTER = "HUNTER"
    SNEAKY = "SNEAKY"
    TOUGH = "TOUGH"
    FRENZY = "FRENZY"

class TriggerType(Enum):
    ON_PLAY = "ON_PLAY"
    ON_ATTACK = "ON_ATTACK"
    ON_BLOCK = "ON_BLOCK"
    ON_DEATH = "ON_DEATH"
    PASSIVE = "PASSIVE"

class CombatUtils:
    @staticmethod
    def can_block(attacker_card, blocker_card) -> bool:
        """
        Vérifie si un blocage est légal.
        Gère Furtif (Sneaky) et les conditions dynamiques de Block Ban.
        """
        # 1. Gestion FURTIF (Sneaky)
        if Keyword.SNEAKY.value in attacker_card.keywords:
            if Keyword.SNEAKY.value not in blocker_card.keywords:
                return False

        # 2. Gestion BLOCK_BAN (Attaquant interdit le blocage)
        # Ex: Oursabeille (Ne peut être bloqué par <= 6)
        if attacker_card.ability and attacker_card.ability.code == "BLOCK_BAN":
            cond_type = attacker_card.ability.condition
            threshold = attacker_card.ability.condition_value
            
            # Condition "MAX_POWER" : Inblocable si Bloqueur.power <= X
            if cond_type == "MAX_POWER":
                if blocker_card.power <= threshold:
                    return False
            
            # Condition "MIN_POWER" : Inblocable si Bloqueur.power >= X
            elif cond_type == "MIN_POWER":
                if blocker_card.power >= threshold:
                    return False

            # Condition "ALWAYS" : Totalement inblocable
            elif cond_type == "ALWAYS":
                return False

        # Note: BLOCK_BAN_FOR_ENEMIES (Pachypoulpe) nécessiterait de vérifier les passifs
        # présents sur le plateau de l'attaquant. Ce n'est pas couvert ici par simplicité.

        return True

    @staticmethod
    def simulate_combat(attacker, blocker):
        """
        Retourne le résultat théorique (att_dead, blk_dead)
        """
        att_dead = False
        blk_dead = False
        
        # 1. Puissance
        if attacker.power > blocker.power:
            blk_dead = True
        elif blocker.power > attacker.power:
            att_dead = True
        else:
            att_dead = True
            blk_dead = True
            
        # 2. Poison
        if Keyword.POISON.value in attacker.keywords:
            blk_dead = True
        if Keyword.POISON.value in blocker.keywords:
            att_dead = True
            
        return att_dead, blk_dead
