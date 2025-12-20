import random
from mindbug_engine.core.consts import Phase, Difficulty
from .interface import AgentInterface


class HeuristicAgent(AgentInterface):
    """
    Agent basé sur des règles expertes et une évaluation heuristique du plateau.
    Configuré via l'Enum Difficulty (EASY, MEDIUM, HARD).
    """

    # Configuration centralisée du comportement
    AI_PARAMS = {
        Difficulty.EASY: {"error_rate": 0.4, "smart_mindbug": False},
        Difficulty.MEDIUM: {"error_rate": 0.1, "smart_mindbug": True},
        Difficulty.HARD: {"error_rate": 0.0, "smart_mindbug": True},
    }

    def __init__(self, difficulty: Difficulty = Difficulty.MEDIUM):
        # Sécurité : conversion string -> Enum si nécessaire (provenant du JSON/Config)
        if isinstance(difficulty, str):
            try:
                difficulty = Difficulty(difficulty)
            except ValueError:
                difficulty = Difficulty.MEDIUM

        self.difficulty = difficulty
        self.params = self.AI_PARAMS[difficulty]

    @property
    def name(self) -> str:
        return f"Bot ({self.difficulty.value})"

    def get_action(self, game):
        """
        Point d'entrée principal.
        Dispatche la logique selon la phase du jeu.
        """
        legal_moves = game.get_legal_moves()
        if not legal_moves: return None

        # Raccourci vers la phase (via le State Proxy clean)
        current_phase = game.state.phase

        # 1. Décision Mindbug (Voler ou pas ?)
        if current_phase == Phase.MINDBUG_DECISION:
            return self._decide_mindbug(game, legal_moves)

        # 2. Décision de Sélection (Effets complexes)
        elif current_phase == Phase.RESOLUTION_CHOICE:
            return self._decide_selection(game, legal_moves)

        # 3. Phase de Jeu Principal (Jouer / Attaquer / Bloquer)
        return self._decide_best_move(game, legal_moves)

    # =========================================================================
    #  LOGIQUE DE DÉCISION
    # =========================================================================

    def _decide_mindbug(self, game, moves):
        """Décide d'utiliser un Mindbug selon la configuration de difficulté."""
        # 1. Vérification de base : Est-ce que le coup est dans la liste ?
        if ("MINDBUG", -1) not in moves:
            return ("PASS", -1)

        # 2. Vérification paranoïaque : A-t-on vraiment des Mindbugs ?
        me = game.state.active_player
        if me.mindbugs <= 0:
            return ("PASS", -1)

        # 3. Logique de décision
        pending_card = game.state.pending_card

        # Stratégie EASY : Vole seulement les très gros monstres, sans réfléchir au contexte
        if not self.params["smart_mindbug"]:
            return ("MINDBUG", -1) if pending_card.power >= 8 else ("PASS", -1)

        # Stratégie MEDIUM/HARD : Contextuelle
        threshold = 7

        # Si la partie est avancée (peu de cartes), on devient plus agressif
        cards_total = len(game.state.player1.hand) + len(game.state.player2.hand)
        if cards_total < 4:
            threshold = 6

        # TODO: Ajouter ici la lecture des Keywords (ex: Voler un POISON est souvent rentable)

        if pending_card.power >= threshold:
            return ("MINDBUG", -1)

        return ("PASS", -1)

    def _decide_selection(self, game, moves):
        """Choisit une cible pour un effet."""
        # Pour l'instant, choix aléatoire valide.
        # Amélioration future : Simuler chaque sélection pour voir laquelle donne le meilleur board.
        return random.choice(moves)

    def _decide_best_move(self, game, moves):
        """Simule chaque coup légal et évalue le plateau résultant."""

        # 1. Simulation d'erreur humaine (selon difficulté)
        if random.random() < self.params["error_rate"]:
            return random.choice(moves)

        # 2. Recherche du meilleur coup
        best_score = -float('inf')
        best_move = moves[0]

        for move in moves:
            # Optimisation : S'il n'y a qu'un choix, pas besoin de simuler
            if len(moves) == 1: return move

            # Simulation
            # On utilise clone() pour ne pas corrompre le vrai jeu
            sim_game = game.clone()

            try:
                # On joue le coup dans la simulation
                sim_game.step(move[0], move[1])

                # On évalue la situation APRES le coup
                # Note : on évalue toujours pour le joueur P2 (l'IA)
                score = self._evaluate_state(sim_game, player_idx=1)

                if score > best_score:
                    best_score = score
                    best_move = move

            except Exception as e:
                # Si la simulation crash (bug moteur rare), on ignore ce coup pour ne pas planter l'IA
                print(f"⚠️ Warning AI Simulation: {e}")
                continue

        return best_move

    # =========================================================================
    #  FONCTION D'ÉVALUATION (HEURISTIQUE)
    # =========================================================================

    def _evaluate_state(self, game, player_idx):
        """
        Donne un score à l'état du jeu du point de vue de player_idx.
        Plus le score est haut, plus la situation est favorable.
        """
        # Récupération sécurisée via .state
        p_me = game.state.player1 if player_idx == 0 else game.state.player2
        p_opp = game.state.player2 if player_idx == 0 else game.state.player1

        # Conditions de victoire immédiate
        if game.state.winner == p_me: return 1000
        if game.state.winner == p_opp: return -1000

        score = 0

        # 1. Différentiel de PV (Vital)
        score += (p_me.hp - p_opp.hp) * 50

        # 2. Puissance sur le plateau (Board Control)
        my_power = sum(c.power for c in p_me.board)
        opp_power = sum(c.power for c in p_opp.board)
        score += (my_power - opp_power) * 2

        # 3. Avantage de cartes (Card Advantage)
        score += (len(p_me.hand) - len(p_opp.hand)) * 10

        # 4. Mindbugs restants (Menace)
        score += (p_me.mindbugs - p_opp.mindbugs) * 15

        return score