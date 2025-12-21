import time
import random
from mindbug_ai.interface import AgentInterface
from mindbug_ai.mcts.node import MCTSNode
from mindbug_ai.mcts.determinizer import Determinizer
from mindbug_engine.core.consts import Phase
from mindbug_engine.utils.logger import log_info


class MCTSAgent(AgentInterface):
    """
    Agent basé sur ISMCTS (Information Set Monte Carlo Tree Search).
    Gère l'incertitude par déterminisation (imagination de mains adverses)
    et utilise des simulations guidées par heuristique.
    """

    def __init__(self, simulation_time=2.0):
        # Temps max de réflexion (secondes)
        self.simulation_time = simulation_time
        self.determinizer = Determinizer()
        self.root = None

    @property
    def name(self) -> str:
        return "MindBot (MCTS)"

    def get_action(self, game):
        """
        Point d'entrée : Lance les simulations et retourne le meilleur coup.
        """
        # 1. Analyse initiale
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None
        if len(legal_moves) == 1:
            return legal_moves[0]  # Optimisation : Pas le choix

        # 2. Création de la racine
        # La racine représente l'état ACTUEL (avant que l'IA ne joue)
        # On passe 'game' pour initialiser les untried_moves
        self.root = MCTSNode(parent=None, state=game)

        # Le joueur qui a mené à la racine est l'adversaire (c'est à nous de jouer)
        self.root.player_just_moved = 1 - game.state.active_player_idx

        ai_player_idx = game.state.active_player_idx  # C'est nous

        # 3. Boucle MCTS
        end_time = time.time() + self.simulation_time
        iterations = 0

        while time.time() < end_time:
            # --- A. DETERMINIZATION ---
            # On clone le jeu pour travailler sur une copie jetable
            sim_game = game.clone()

            # On imagine une main adverse cohérente (mélange des cartes cachées)
            self.determinizer.determinize(
                sim_game.state, observer_idx=ai_player_idx)

            node = self.root

            # --- B. SELECTION ---
            # On descend dans l'arbre tant qu'on connaît le chemin (nœud totalement étendu)
            while node.untried_moves == [] and node.children:
                node = node.uct_select_child()
                sim_game.step(node.move[0], node.move[1])

            # --- C. EXPANSION ---
            if node.untried_moves:
                move = random.choice(node.untried_moves)
                player_who_moves = sim_game.state.active_player_idx
                sim_game.step(move[0], move[1])
                # On passe l'info explicite au nœud
                node = node.add_child(move, sim_game, player_who_moves)
                if move in node.parent.untried_moves:
                    node.parent.untried_moves.remove(move)

            # --- D. SIMULATION (ROLLOUT) ---
            # On joue de manière semi-aléatoire jusqu'à la fin de la partie
            depth = 0
            while sim_game.state.winner is None and depth < 50:
                # Politique heuristique pour éviter les parties absurdes
                move = self._heuristic_rollout_policy(sim_game)
                if not move:
                    break
                sim_game.step(move[0], move[1])
                depth += 1

            # --- E. BACKPROPAGATION ---
            # On remonte le résultat
            winner = sim_game.state.winner

            while node is not None:
                win_score = 0.0
                if winner:
                    # Si le joueur qui a joué pour arriver ici a gagné
                    winner_idx = 0 if winner == sim_game.state.player1 else 1
                    if node.player_just_moved == winner_idx:
                        win_score = 1.0

                node.update(win_score)
                node = node.parent

            iterations += 1

        # 4. Décision Finale
        if not self.root.children:
            return random.choice(legal_moves)  # Fallback

        # On choisit l'enfant le plus visité (critère de robustesse)
        best_node = max(self.root.children, key=lambda c: c.visits)

        log_info(
            f"🤖 MCTS: {iterations} sims. Choix: {best_node.move} (Win: {best_node.wins}/{best_node.visits} = {best_node.wins/best_node.visits:.1%})")
        return best_node.move

    def _heuristic_rollout_policy(self, game):
        """
        Choisit un coup semi-intelligent pour la simulation.
        Évite que la simulation soit trop chaotique (Instinct de survie + Tueur).
        """
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        # 1. INSTINCT DE TUEUR : Si je peux gagner, je le fais
        opp = game.state.player2 if game.state.active_player_idx == 0 else game.state.player1
        if opp.hp <= 1:
            for move in legal_moves:
                if move[0] == "ATTACK":
                    # Simplification : toute attaque est bonne à prendre si l'adversaire est low
                    return move

        # 2. INSTINCT DE SURVIE : Si je dois bloquer, je bloque
        if game.state.phase == "BLOCK_DECISION":
            block_moves = [m for m in legal_moves if m[0] == "BLOCK"]
            if block_moves:
                # On bloque au hasard plutôt que de mourir (NO_BLOCK)
                # Cela évite que l'IA perde bêtement en simulation
                return random.choice(block_moves)

        # 3. ÉCONOMIE MINDBUG : On ne Mindbug pas n'importe quoi
        if game.state.phase == "MINDBUG_DECISION":
            pending = game.state.pending_card
            # Si la carte est faible (< 6), on passe souvent
            if pending and pending.power < 6 and random.random() < 0.8:
                return ("PASS", -1)

        # 4. Par défaut : Hasard
        return random.choice(legal_moves)
