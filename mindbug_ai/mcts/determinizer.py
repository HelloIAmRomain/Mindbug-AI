import random
from copy import deepcopy


class Determinizer:
    """
    Responsable de la création d'états de jeu hypothétiques (Determinization)
    pour gérer l'information incomplète (Main adverse et Pioche inconnues).
    """

    def determinize(self, game_state, observer_idx):
        """
        Mélange les cartes inconnues (Main adverse + Pioche) et les redistribue.
        Cela crée un état "Possible" sur lequel on peut simuler.

        Args:
            game_state (GameState): L'état actuel du jeu (cloné).
            observer_idx (int): L'index du joueur qui réfléchit (l'IA).

        Returns:
            GameState: L'état modifié avec une main adverse et une pioche mélangées.
        """
        # On identifie les rôles
        opponent = game_state.player2 if observer_idx == 0 else game_state.player1

        # 1. Collecte de toutes les cartes cachées
        # (Pour l'observateur, la main de l'adversaire et la pioche sont interchangeables)
        hidden_pool = []
        hidden_pool.extend(opponent.hand)
        hidden_pool.extend(game_state.deck)

        # 2. Mélange (Shuffle)
        random.shuffle(hidden_pool)

        # 3. Redistribution
        # On remplit la main de l'adversaire pour qu'elle ait le même nombre de cartes qu'avant
        target_hand_size = len(opponent.hand)
        new_opp_hand = []

        for _ in range(target_hand_size):
            if hidden_pool:
                new_opp_hand.append(hidden_pool.pop())

        # 4. Application
        opponent.hand = new_opp_hand
        game_state.deck = hidden_pool  # Le reste retourne dans la pioche

        return game_state
