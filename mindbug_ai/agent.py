import random
from .mcts import MCTS

class MindbugAgent:
    """
    L'Agent IA qui joue au jeu.
    Il utilise la Déterminisation (Brouillage des infos cachées) 
    puis le MCTS pour choisir son coup.
    """
    def __init__(self, name="Robot", level=5):
        self.name = name
        # Le niveau correspond au temps de réflexion en ms
        # Niveau 1 = 100ms (Très rapide, joue mal)
        # Niveau 5 = 1000ms (Réfléchi)
        # Niveau 10 = 5000ms (Expert)
        self.time_limit_ms = level * 200 
        self.mcts = MCTS()

    def get_move(self, real_game):
        """
        Analyse le jeu réel et retourne le meilleur coup (tuple action).
        """
        # 1. CLONAGE
        # On ne touche jamais au jeu réel pour ne pas le casser
        sim_game = real_game.clone()
        
        # 2. DÉTERMINISATION (Anti-Triche)
        # L'IA ne doit pas savoir ce qu'il y a exactement dans la main adverse.
        # On mélange donc les cartes inconnues (Main Adverse + Pioches)
        self._determinize_hidden_information(sim_game)
        
        # 3. RÉFLEXION (MCTS)
        best_move = self.mcts.search(sim_game, time_limit_ms=self.time_limit_ms)
        
        return best_move

    def _determinize_hidden_information(self, game):
        """
        Mélange les zones d'informations cachées pour l'IA.
        Hypothèse : L'IA est le joueur actif dans 'game'.
        """
        ai_player = game.active_player
        opponent = game.opponent
        
        # Quelles sont les cartes que l'IA ne connait pas précisément ?
        # - La main de l'adversaire
        # - La pioche de l'adversaire
        # - Sa propre pioche (l'ordre est inconnu)
        # - La pioche commune (si le moteur l'utilise encore, ici ce sont les decks joueurs)
        
        # On rassemble toutes ces cartes dans un "Pool d'Inconnues"
        hidden_pool = opponent.hand + opponent.deck + ai_player.deck
        
        # On mélange ce pool (C'est ici que la magie opère)
        random.shuffle(hidden_pool)
        
        # On redistribue les cartes au hasard en respectant les quantités
        # 1. Main de l'adversaire (doit garder le même nombre de cartes)
        nb_opp_hand = len(opponent.hand)
        opponent.hand = hidden_pool[:nb_opp_hand]
        remaining = hidden_pool[nb_opp_hand:]
        
        # 2. Pioche de l'adversaire
        nb_opp_deck = len(opponent.deck)
        opponent.deck = remaining[:nb_opp_deck]
        
        # 3. Pioche de l'IA
        ai_player.deck = remaining[nb_opp_deck:]
        
        # Maintenant, 'game' est un monde hypothétique cohérent où 
        # l'IA ne triche pas (elle ne sait pas si la carte X est en main ou dans le deck).
