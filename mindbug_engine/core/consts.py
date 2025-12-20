from enum import Enum

class Phase(str, Enum):
    """
    Définit l'étape actuelle du jeu.
    Utilisé par le State et le TurnManager pour savoir quelles actions sont légales.
    """
    P1_MAIN = "P1_MAIN"                     # Tour principal du Joueur 1 (Peut Jouer ou Attaquer)
    P2_MAIN = "P2_MAIN"                     # Tour principal du Joueur 2
    MINDBUG_DECISION = "MINDBUG_DECISION"   # L'adversaire choisit de voler ou non la carte jouée
    BLOCK_DECISION = "BLOCK_DECISION"       # Le défenseur choisit de bloquer ou non l'attaquant
    RESOLUTION_CHOICE = "RESOLUTION_CHOICE" # Le jeu est en PAUSE : En attente d'une sélection (clic)
    GAME_OVER = "GAME_OVER"                 # Partie terminée

class Trigger(str, Enum):
    """
    Définit le moment de déclenchement d'un effet (Trigger).
    Correspond au champ 'trigger' dans le JSON des cartes.
    """
    ON_PLAY = "ON_PLAY"           # Se déclenche quand la carte arrive sur le plateau
    ON_DEATH = "ON_DEATH"         # Se déclenche quand la carte est détruite (Board -> Discard)
    ON_ATTACK = "ON_ATTACK"       # Se déclenche immédiatement lors de la déclaration d'attaque
    ON_BLOCK = "ON_BLOCK"         # Se déclenche quand cette carte bloque
    ON_BLOCKED = "ON_BLOCKED"     # Se déclenche quand cette carte (attaquante) est bloquée
    ON_UNBLOCKED = "ON_UNBLOCKED" # Se déclenche si cette carte (attaquante) n'est PAS bloquée
    PASSIVE = "PASSIVE"           # Effet continu/permanent tant que la carte est sur le plateau

class EffectType(str, Enum):
    """
    Définit le type d'action (Verbe) de l'effet.
    Correspond au champ 'type' dans la liste 'effects' du JSON.
    """
    MODIFY_STAT = "MODIFY_STAT"     # Modifier PV Joueur ou Puissance Créature
    DESTROY = "DESTROY"             # Détruire une carte (Board -> Discard)
    STEAL = "STEAL"                 # Voler le contrôle (Adversaire -> Moi)
    DISCARD = "DISCARD"             # Forcer la défausse (Main -> Discard)
    PLAY = "PLAY"                   # Jouer une carte hors-main (ex: depuis Discard)
    MOVE = "MOVE"                   # Déplacer une carte entre zones (ex: Discard -> Main)
    ADD_KEYWORD = "ADD_KEYWORD"     # Donner un mot-clé (ex: Gagne Furie)
    COPY_KEYWORDS = "COPY_KEYWORDS" # Copier les mots-clés d'autres cartes
    BAN = "BAN"                     # Interdire une mécanique (ex: "Ne peut pas bloquer")

class Keyword(str, Enum):
    """
    Les mots-clés standards du jeu Mindbug.
    """
    FRENZY = "FRENZY"   # Fureur : Peut attaquer une seconde fois si survit
    TOUGH = "TOUGH"     # Tenace : Ignore la première destruction (devient 'damaged')
    POISON = "POISON"   # Venimeux : Détruit toujours la créature adverse au combat
    HUNTER = "HUNTER"   # Chasseur : L'attaquant choisit qui bloque
    SNEAKY = "SNEAKY"   # Furtif : Ne peut être bloqué que par une créature Furtive

class Difficulty(str, Enum):
    """Niveaux de difficulté officiels."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class CardStatus(str, Enum):
    """
    Définit l'état visuel ou logique d'une carte sur le plateau.
    Ajouté pour corriger l'ImportError.
    """
    NORMAL = "NORMAL"
    DAMAGED = "DAMAGED"    # Pour les créatures TOUGH ayant déjà survécu à un coup
    EXHAUSTED = "EXHAUSTED" # Si vous implémentez une mécanique d'engagement
