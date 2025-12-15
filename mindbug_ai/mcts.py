import math
import random
import time
from typing import List, Optional
from mindbug_engine.engine import MindbugGame

class MCTSNode:
    """
    Un nœud de l'arbre de recherche Monte Carlo.
    Représente un état du jeu à un instant T.
    """
    def __init__(self, game_state: MindbugGame, parent=None, move=None):
        self.game_state = game_state
        self.parent = parent
        self.move = move # Le coup qui a mené à cet état (ex: ("ATTACK", 0))
        
        self.children: List[MCTSNode] = []
        self.wins = 0.0
        self.visits = 0
        
        # Coups possibles non encore explorés à partir de cet état
        self.untried_moves = game_state.get_legal_moves()

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def is_terminal_node(self):
        return self.game_state.winner is not None

    def best_child(self, c_param=1.414):
        """
        Sélectionne le meilleur enfant selon la formule UCB1.
        UCB1 = (Wins / Visits) + C * sqrt(ln(ParentVisits) / Visits)
        """
        choices_weights = [
            (child.wins / child.visits) + c_param * math.sqrt((2 * math.log(self.visits) / child.visits))
            for child in self.children
        ]
        return self.children[choices_weights.index(max(choices_weights))]

class MCTS:
    """
    Moteur de recherche Monte Carlo.
    """
    def __init__(self, exploration_weight=1.41):
        self.exploration_weight = exploration_weight

    def search(self, root_game: MindbugGame, time_limit_ms=1000):
        """
        Exécute l'algorithme MCTS pendant un temps donné.
        Retourne le meilleur coup trouvé.
        """
        root_node = MCTSNode(root_game)
        end_time = time.time() * 1000 + time_limit_ms

        while (time.time() * 1000) < end_time:
            node = root_node

            # 1. SELECTION
            # On descend dans l'arbre jusqu'à trouver une feuille ou un nœud non étendu
            while node.is_fully_expanded() and not node.is_terminal_node():
                node = node.best_child(self.exploration_weight)

            # 2. EXPANSION
            # Si le nœud n'est pas terminal et a des coups non testés, on en crée un
            if not node.is_terminal_node() and not node.is_fully_expanded():
                move = node.untried_moves.pop()
                new_state = self._apply_move_on_clone(node.game_state, move)
                child_node = MCTSNode(new_state, parent=node, move=move)
                node.children.append(child_node)
                node = child_node

            # 3. SIMULATION (Rollout)
            # On joue au hasard jusqu'à la fin de la partie
            simulation_state = node.game_state.clone()
            self._rollout(simulation_state)

            # 4. BACKPROPAGATION
            # On remonte le résultat (1 si victoire IA, 0 sinon)
            # Attention : root_game.active_player est celui qui demande le coup (l'IA)
            # On doit vérifier si ce joueur a gagné dans la simulation.
            
            # Qui est l'IA qui réfléchit ?
            ai_player_idx = root_game.active_player_idx 
            
            winner_idx = -1
            if simulation_state.winner:
                if simulation_state.winner.name == "P1": winner_idx = 0
                elif simulation_state.winner.name == "P2": winner_idx = 1
            
            # Score : 1.0 si l'IA gagne, 0.0 sinon
            score = 1.0 if winner_idx == ai_player_idx else 0.0
            
            while node is not None:
                node.visits += 1
                node.wins += score
                node = node.parent

        # Fin du temps imparti, on retourne le coup le plus visité (le plus robuste)
        if not root_node.children:
            return None # Aucun coup possible ou temps trop court
            
        best_child = max(root_node.children, key=lambda c: c.visits)
        return best_child.move

    def _apply_move_on_clone(self, game_state, move):
        """Clone l'état et applique un coup."""
        clone = game_state.clone()
        # move est un tuple ("ATTACK", 0)
        action_type, idx = move
        clone.step(action_type, idx)
        return clone

    def _rollout(self, game_state):
        """Joue une partie au hasard jusqu'à la fin (très optimisé si possible)."""
        while game_state.winner is None:
            moves = game_state.get_legal_moves()
            if not moves:
                break # Should not happen unless stalemate
            
            # Random pur
            move = random.choice(moves)
            game_state.step(move[0], move[1])
