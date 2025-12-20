"""
Configuration des dimensions et proportions.
Mise à jour : Centrage optimisé et cartes légèrement plus grandes.
"""

# --- DIMENSIONS CARTES ---
CARD_ASPECT_RATIO = 0.714
# On augmente un peu la taille pour que ce soit plus lisible
CARD_HEIGHT_PERCENT = 0.22

# --- POSITIONS VERTICALES (Y) ---
# L'objectif est d'avoir les deux plateaux (Board P1 et P2) centrés autour de 0.50 (le milieu)

# Joueur 2 (Haut)
# La main P2 dépasse juste un peu du haut pour montrer la présence de l'adversaire
P2_HAND_Y_PERCENT = 0.02
P2_PILE_Y_PERCENT = 0.02

# Le plateau P2 descend un peu pour se rapprocher du centre
P2_BOARD_Y_PERCENT = 0.26

# Joueur 1 (Bas)
# Le plateau P1 remonte un peu pour laisser juste un "couloir" de jeu au milieu
P1_BOARD_Y_PERCENT = 0.52

# La main P1 est calée en bas, avec une petite marge
P1_HAND_Y_PERCENT = 0.76
P1_PILE_Y_PERCENT = 0.76

# Résultat :
# Espace "No Man's Land" (Play Area) entre 0.48 (fin board P2) et 0.52 (début board P1)
# C'est serré mais dynamique !

# --- POSITIONS HORIZONTALES (X) ---
PILE_MARGIN_PERCENT = 0.03 # Un peu plus de marge sur les côtés

# --- AUTRES ---
MARGIN_PERCENT = 0.02
GAP_PERCENT = 0.015       # Un peu plus d'espace entre les cartes
ANIMATION_SPEED = 18      # Un peu plus rapide
ZOOM_FACTOR = 2.4         # Zoom confortable