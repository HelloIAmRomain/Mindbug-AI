from mindbug_engine.core.consts import Difficulty
# On importe les status colors
from mindbug_gui.core.colors import STATUS_OK, STATUS_WARN, STATUS_CRIT, ACCENT

# Configuration de l'affichage des difficultés
# On lie les Enums aux Couleurs Sémantiques
DIFFICULTY_UI_CONFIG = {
    Difficulty.EASY: {
        "label": "DÉBUTANT",
        "desc": "Joue parfois au hasard",
        "color": STATUS_OK,      # Vert
        "next": Difficulty.MEDIUM
    },
    Difficulty.MEDIUM: {
        "label": "INTERMÉDIAIRE",
        "desc": "Joue sérieusement",
        "color": STATUS_WARN,    # Or/Jaune
        "next": Difficulty.HARD
    },
    Difficulty.HARD: {
        "label": "EXPERT",
        "desc": "Ne fait aucun cadeau",
        "color": STATUS_CRIT,    # Rouge
        "next": Difficulty.EXTREME
    },
    Difficulty.EXTREME: {
        "label": "DEMONIAQUE",
        "desc": "Prévoit 6 sec dans le futur",
        "color": ACCENT,         # Violet (Couleur Mindbug)
        "next": Difficulty.EASY  # Boucle le cycle
    }
}
