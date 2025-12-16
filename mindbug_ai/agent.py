import random
import time
from mindbug_engine.rules import Phase
from mindbug_engine.logger import log_info, log_debug, log_error


class MindbugAgent:
    """
    IA Hybride : Probabiliste + Heuristique.
    Elle ne triche pas (ne regarde pas la main adverse réelle),
    mais elle 'compte les cartes' pour deviner ce que l'adversaire a probablement.
    """

    def __init__(self, name="DeepBug", level=5):
        self.name = name
        # Nombre de simulations max
        # L'IA s'arrêtera de toute façon au timeout, ce chiffre est une sécurité.
        self.simulations = level * 100
        self.max_depth = 5

        # Temps de réflexion alloué (en secondes)
        self.time_limit = 3.0

    def get_move(self, real_game):
        """Cerveau principal : décide du meilleur coup."""
        try:
            log_debug(f"🤖 [IA] Réfléchit... (Phase: {real_game.phase})")

            legal_moves = real_game.get_legal_moves()
            if not legal_moves:
                log_error("🤖 [IA] Aucun coup légal ! (Bug potentiel)")
                return None

            # Si un seul coup possible, pas besoin de réfléchir
            if len(legal_moves) == 1:
                log_info(f"🤖 [IA] Coup forcé : {legal_moves[0]}")
                return legal_moves[0]

            # 1. PHASE MINDBUG : Décision binaire rapide (Heuristique)
            if real_game.phase == Phase.MINDBUG_DECISION:
                decision = self._decide_mindbug(real_game, legal_moves)
                log_info(f"🤖 [IA] Décision Rapide Mindbug : {decision}")
                return decision

            # 2. AUTRES PHASES : Simulation (MCTS Simplifié)
            # Si on a plusieurs choix, on lance la simulation
            if len(legal_moves) > 1:
                best_move = self._search_best_move(real_game, legal_moves)
                log_info(f"🤖 [IA] Coup choisi après réflexion : {best_move}")
                return best_move

            return legal_moves[0]

        except Exception as e:
            log_error(f"🛑 [IA CRASH] : {e}")
            import traceback
            log_error(traceback.format_exc())
            # Sécurité : on joue au hasard pour ne pas bloquer le jeu
            if legal_moves:
                return random.choice(legal_moves)
            return None

    def _decide_mindbug(self, game, moves):
        """
        Décide de voler une carte ou non.
        Basé sur un score de dangerosité de la carte.
        """
        card = game.pending_card
        if not card: return ("PASS", -1)

        # Calcul de la valeur de la carte
        value = card.power
        if "POISON" in card.keywords: value += 5
        if "HUNTER" in card.keywords: value += 3
        if "TOUGH" in card.keywords: value += 2
        if "FRENZY" in card.keywords: value += 3

        # Seuil d'activation (plus bas en fin de partie)
        threshold = 7
        if len(game.player1.hand) + len(game.player2.hand) < 4:
            threshold = 6

        should_steal = value >= threshold

        # Les passifs sont souvent forts (ex: Kangisouris)
        if card.ability and card.trigger == "PASSIVE":
            should_steal = True

        if should_steal and ("MINDBUG", -1) in moves:
            log_debug(f"🤖 [IA] Mindbug sur {card.name} (Valeur estimée: {value})")
            return ("MINDBUG", -1)

        log_debug(f"🤖 [IA] Pas de Mindbug sur {card.name} (Valeur estimée: {value})")
        return ("PASS", -1)

    def _search_best_move(self, real_game, legal_moves):
        """
        Simule X parties avec des mains adverses probables pour choisir le meilleur coup.
        """
        scores = {move: 0 for move in legal_moves}

        # On récupère toutes les cartes qu'on ne voit pas
        unknown_pool = self._get_unknown_cards(real_game)
        start_time = time.time()
        sim_count = 0

        # Boucle de simulation
        for i in range(self.simulations):
            # Time cap : On laisse du temps pour réfléchir, mais on coupe si trop long
            if time.time() - start_time > self.time_limit:
                break

            sim_count += 1

            # 1. Déterminisation : On imagine une main adverse possible
            sim_game = self._determinize_game(real_game, unknown_pool)

            # 2. Test des coups
            for move in legal_moves:
                try:
                    test_game = sim_game.clone()
                    test_game.step(move[0], move[1])

                    # 3. Rollout rapide (quelques coups au hasard)
                    final_score = self._rollout(test_game, depth=3)
                    scores[move] += final_score
                except Exception as e:
                    # Si une simulation plante, on l'ignore et on continue
                    continue

        log_debug(f"🤖 [IA] A réfléchi {time.time() - start_time:.2f}s ({sim_count} simulations)")

        # On prend le coup qui a le meilleur score moyen
        best_move = max(scores, key=scores.get)
        return best_move

    def _rollout(self, game, depth):
        """Joue au hasard pendant 'depth' tours."""
        current_depth = 0
        while not game.winner and current_depth < depth:
            moves = game.get_legal_moves()
            if not moves: break

            # Petite heuristique : on préfère jouer/attaquer que passer/ne pas bloquer si possible
            # (Sauf si Mindbug Decision où Pass est souvent valide)
            move = random.choice(moves)
            game.step(move[0], move[1])
            current_depth += 1

        return self._evaluate_state(game, game.player2)

    def _evaluate_state(self, game, ai_player):
        """Donne une note à la situation actuelle (Point de vue IA)."""
        if game.winner == ai_player: return 1000
        if game.winner: return -1000

        opponent = game.player1 if ai_player == game.player2 else game.player2
        score = 0

        # 1. PV (Très important)
        score += (ai_player.hp - opponent.hp) * 50

        # 2. Puissance brute sur le board
        my_power = sum(c.power for c in ai_player.board)
        opp_power = sum(c.power for c in opponent.board)
        score += (my_power - opp_power)

        # 3. Bonus Mots-clés
        for c in ai_player.board:
            if "POISON" in c.keywords: score += 5
            if "TOUGH" in c.keywords: score += 2

        for c in opponent.board:
            if "POISON" in c.keywords: score -= 5

        # 4. Mindbugs restants (Avantage tactique)
        score += (ai_player.mindbugs - opponent.mindbugs) * 15

        return score

    def _get_unknown_cards(self, game):
        """Récupère la liste des cartes que l'IA ne connait pas."""
        # On suppose que game.all_cards_ref contient toutes les cartes du deck initial
        all_cards = getattr(game, 'all_cards_ref', [])
        visible_ids = set()

        # Tout ce qui est visible pour l'IA (y compris ce qu'elle a vu passer en défausse)
        visible_ids.update(c.id for c in game.player2.hand)
        visible_ids.update(c.id for c in game.player2.board)
        visible_ids.update(c.id for c in game.player1.board)
        visible_ids.update(c.id for c in game.player1.discard)
        visible_ids.update(c.id for c in game.player2.discard)

        # Inconnues = Tout - Visible
        unknowns = [c for c in all_cards if c.id not in visible_ids]
        return unknowns

    def _determinize_game(self, real_game, unknown_pool):
        """Crée un monde hypothétique cohérent pour la simulation."""
        sim_game = real_game.clone()

        if not unknown_pool:
            return sim_game

        pool = list(unknown_pool)
        random.shuffle(pool)

        # On remplit la main de l'adversaire (P1) avec des cartes du pool inconnu
        num_cards_opp = len(real_game.player1.hand)

        if len(pool) >= num_cards_opp:
            new_hand = pool[:num_cards_opp]
            sim_game.player1.hand = [c.copy() for c in new_hand]
            # Le reste irait techniquement dans les pioches, mais pour une simu courte c'est moins grave

        return sim_game