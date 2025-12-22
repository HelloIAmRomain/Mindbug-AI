import time
import random
import logging
from mindbug_ai.interface import AgentInterface
from mindbug_ai.mcts.node import MCTSNode
from mindbug_ai.mcts.determinizer import Determinizer
from mindbug_engine.core.consts import Phase, Keyword


class MCTSAgent(AgentInterface):
    """
    Agent basé sur ISMCTS (Information Set Monte Carlo Tree Search).
    Version v4 : Gestion dynamique des Mindbugs selon le stade de la partie.
    """

    def __init__(self, simulation_time=2.0):
        self.simulation_time = simulation_time
        self.determinizer = Determinizer()
        self.root = None

    @property
    def name(self) -> str:
        return "MindBot (MCTS v4)"

    def get_action(self, game):
        # ... (Code MCTS inchangé : Selection, Expansion, Backpropagation ...)
        # Je remets le code standard pour ne pas alourdir la réponse
        # L'important est la méthode _heuristic_rollout_policy plus bas

        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None
        if len(legal_moves) == 1:
            return legal_moves[0]

        self.root = MCTSNode(parent=None, state=game)
        self.root.player_just_moved = 1 - game.state.active_player_idx
        ai_player_idx = game.state.active_player_idx

        logger = logging.getLogger("MindbugLogger")
        original_level = logger.level
        logger.setLevel(logging.CRITICAL)

        try:
            end_time = time.time() + self.simulation_time
            iterations = 0

            while time.time() < end_time:
                sim_game = game.clone()
                if not sim_game.state.active_request:
                    self.determinizer.determinize(
                        sim_game.state, observer_idx=ai_player_idx)

                node = self.root
                while node.untried_moves == [] and node.children:
                    node = node.uct_select_child()
                    sim_game.step(node.move[0], node.move[1])

                if node.untried_moves:
                    move = random.choice(node.untried_moves)
                    player_who_moves = sim_game.state.active_player_idx
                    sim_game.step(move[0], move[1])
                    node = node.add_child(move, sim_game, player_who_moves)
                    if move in node.parent.untried_moves:
                        node.parent.untried_moves.remove(move)

                depth = 0
                while sim_game.state.winner is None and depth < 50:
                    move = self._heuristic_rollout_policy(sim_game)
                    if not move:
                        break
                    sim_game.step(move[0], move[1])
                    depth += 1

                winner = sim_game.state.winner
                while node is not None:
                    win_score = 0.0
                    if winner:
                        winner_idx = 0 if winner == sim_game.state.player1 else 1
                        if node.player_just_moved == winner_idx:
                            win_score = 1.0
                    node.update(win_score)
                    node = node.parent

                iterations += 1

        finally:
            logger.setLevel(original_level)

        if not self.root.children:
            return random.choice(legal_moves)
        best_node = max(self.root.children, key=lambda c: c.visits)

        print(f"🤖 MCTS: {iterations} sims. Choix: {best_node.move} (Win: {best_node.wins}/{best_node.visits} = {best_node.wins/best_node.visits:.1%})")
        return best_node.move

    def _heuristic_rollout_policy(self, game):
        """
        Politique de simulation "Experte" (Playout Policy).
        """
        legal_moves = game.get_legal_moves()
        if not legal_moves:
            return None

        ap = game.state.active_player
        opp = game.state.player2 if ap == game.state.player1 else game.state.player1

        # --- 1. INSTINCT DE TUEUR ---
        if opp.hp <= 1:
            for m in legal_moves:
                if m[0] == "ATTACK":
                    return m

        # --- 2. PHASE DE MINDBUG (LOGIQUE DYNAMIQUE) ---
        if game.state.phase == Phase.MINDBUG_DECISION:
            card = game.state.pending_card
            if card:
                # A. Cas Inutiles
                if card.name == "Sirène mystérieuse" and ap.hp >= opp.hp:
                    return ("PASS", -1)
                if card.name == "Giraffodile" and len(ap.discard) == 0:
                    return ("PASS", -1)

                # B. Calcul du Score de Menace de la carte
                # Base = Puissance
                threat_score = card.power

                # Bonus Mots-clés
                keywords = card.keywords
                if Keyword.POISON in keywords:
                    threat_score += 3  # Tueur de géants
                if Keyword.HUNTER in keywords:
                    threat_score += 2  # Contrôle
                if Keyword.FRENZY in keywords:
                    threat_score += 2  # Double attaque
                if Keyword.TOUGH in keywords:
                    threat_score += 1   # Résistance

                # C. Définition du Seuil d'Exigence (Threshold)
                # Plus l'adversaire a de cartes en main, plus on est exigeant (on attend mieux).
                opp_hand_size = len(opp.hand)
                current_mindbugs = ap.mindbugs

                required_score = 100  # Par défaut impossible

                if current_mindbugs == 2:
                    if opp_hand_size >= 3:  # Début de partie
                        # Je veux du TRES lourd (ex: 7+Poison, ou 9+)
                        required_score = 9
                    else:  # Milieu de partie
                        # Je prends les bonnes cartes (8, ou 6+Bonus)
                        required_score = 8

                elif current_mindbugs == 1:
                    if opp_hand_size >= 2:  # Il reste encore des menaces cachées
                        # Je garde mon joker pour le Boss final (Gorillion, Hydra, ou combo mortel)
                        required_score = 10
                    else:  # Fin de partie (Dernière ou avant-dernière carte)
                        required_score = 7  # Je ne laisse pas passer une carte correcte

                # D. Décision
                if threat_score >= required_score:
                    # Petite part d'aléatoire (5%) pour ne pas être robotique
                    if random.random() < 0.95:
                        return ("MINDBUG", -1)

                return ("PASS", -1)

        # --- 3. PHASE DE BLOCAGE ---
        if game.state.phase == Phase.BLOCK_DECISION:
            block_moves = [m for m in legal_moves if m[0] == "BLOCK"]
            if not block_moves:
                return ("NO_BLOCK", -1)

            attacker = game.state.pending_attacker
            if not attacker:
                return random.choice(legal_moves)

            if Keyword.POISON in attacker.keywords:
                # Bloquer le poison avec le plus faible
                return min(block_moves, key=lambda m: ap.board[m[1]].power)

            # Utiliser TOUGH si possible
            for m in block_moves:
                blocker = ap.board[m[1]]
                if Keyword.TOUGH in blocker.keywords and not blocker.is_damaged:
                    return m

            if random.random() < 0.8:  # On bloque souvent
                return random.choice(block_moves)
            return ("NO_BLOCK", -1)

        # --- 4. PHASE D'ATTAQUE ---
        attack_moves = [m for m in legal_moves if m[0] == "ATTACK"]
        for m in attack_moves:
            attacker = ap.board[m[1]]
            # Attaque gratuite SNEAKY
            if Keyword.SNEAKY in attacker.keywords:
                has_sneaky_blocker = any(
                    Keyword.SNEAKY in c.keywords for c in opp.board)
                if not has_sneaky_blocker:
                    return m

            # Attaque gratuite POISON (si l'autre n'a pas de petite créature pour absorber)
            if Keyword.POISON in attacker.keywords:
                # Si l'adversaire n'a que des grosses créatures (>4), c'est rentable
                if all(c.power > 4 for c in opp.board):
                    return m

        return random.choice(legal_moves)
