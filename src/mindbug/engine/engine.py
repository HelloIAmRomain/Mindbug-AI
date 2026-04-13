import random
import traceback
import copy
import pickle
from typing import Optional, List, Tuple, Any

from mindbug.engine.utils.logger import log_info, log_debug, log_error

# --- IMPORTS CORE ---
from mindbug.engine.core.models import Card, Player
from mindbug.engine.core.state import GameState
from mindbug.engine.core.consts import Phase, Keyword, Trigger

# --- IMPORTS INFRASTRUCTURE ---
from mindbug.engine.infrastructure.deck_factory import DeckFactory
from mindbug.constants import PATH_DATA

# --- IMPORTS MANAGERS ---
from mindbug.engine.managers.turn_manager import TurnManager
from mindbug.engine.managers.combat_manager import CombatManager
from mindbug.engine.managers.effect_manager import EffectManager
from mindbug.engine.managers.query_manager import QueryManager

# --- IMPORTS COMMANDS & BUILDER ---
from mindbug.engine.commands.command_factory import CommandFactory


class MindbugGame:
    """
    Moteur principal du jeu Mindbug.
    Gère le cycle de vie d'une partie, la coordination entre les managers
    et l'application des règles.
    """

    def __init__(self, config: 'ConfigurationService'):
        """
        Initialise une nouvelle instance de jeu.
        Args:
            config: Instance du service de configuration centralisé.
        """
        # 1. Configuration et Debug
        self.config = config
        self.verbose = config.debug_mode

        # 2. Infrastructure (Données et Deck)
        self.deck_factory = DeckFactory(PATH_DATA)

        # Création du deck basé sur les sets actifs de la configuration
        # DeckFactory doit être configuré pour demander 22 cartes (20 + 2 pour initiative)
        game_deck, all_cards_ref, used_sets = self.deck_factory.create_deck(
            active_sets=self.config.active_sets
        )
        # Exposition pour l'UI ou le debug
        self.used_sets = used_sets

        # 3. État du Jeu (GameState)
        p1 = Player(name="P1")
        p2 = Player(name="P2")

        self.state = GameState(game_deck, p1, p2)
        self.state.all_cards_ref = all_cards_ref

        # 4. Managers de Logique
        self.query_manager = QueryManager(self)
        self.turn_manager = TurnManager(self)
        self.combat_manager = CombatManager(self)
        self.effect_manager = EffectManager(self)

        # Injection croisée finale
        self.combat_manager.effect_manager = self.effect_manager

        # 5. État d'exécution
        self.is_over = False
        self.history = []

        if self.verbose:
            log_info(f"🎮 Jeu initialisé avec les sets : {used_sets}")
            log_info(f"🤖 Difficulté IA : {self.config.ai_difficulty.value}")

    def start_game(self):
        """
        Démarre la partie :
        1. Phase d'Initiative (Duel de 2 cartes).
        2. Distribution (Mains + Pioches Perso) après résolution.
        """
        if not self.state.deck:
            log_error("Impossible de démarrer : Le deck est vide.")
            return

        if self.verbose:
            log_info(
                f"🎲 Démarrage... Deck Global: {len(self.state.deck)} cartes.")

        # 1. Mélange initial
        random.shuffle(self.state.deck)

        # 2. Reset des joueurs
        for p in self.state.players:
            p.hand = []
            p.deck = []
            p.board = []
            p.discard = []
            p.hp = 3
            p.mindbugs = 2

        # 3. Lancement de la séquence d'initiative
        # On a besoin d'au moins 22 cartes (20 jeu + 2 décision)
        if len(self.state.deck) >= 22:
            self.state.phase = Phase.INITIATIVE_BATTLE
            self._draw_initiative_cards()
            log_info("🎲 Phase Initiative : En attente de résolution...")
        else:
            # Fallback (Deck trop petit, ex: tests) : P1 commence direct
            log_info(
                "⚠️ Deck < 22 cartes. Règle d'initiative ignorée (P1 commence).")
            self._distribute_and_start(starter_idx=0)

    def _draw_initiative_cards(self):
        """Pioche 2 cartes pour le duel."""
        c1 = self.state.deck.pop()  # Pour P1
        c2 = self.state.deck.pop()  # Pour P2
        self.state.initiative_duel = (c1, c2)
        log_info(
            f"⚔️ Duel : P1 tire {c1.name} ({c1.power}) vs P2 tire {c2.name} ({c2.power})")

    def resolve_initiative_step(self):
        """
        Appelé via la commande CONFIRM_INITIATIVE (clic bouton/écran).
        Gère la résolution du duel : Égalité ou Victoire.
        """
        if not self.state.initiative_duel:
            return

        c1, c2 = self.state.initiative_duel

        # Cas 1 : Égalité -> On remet et on recommence
        if c1.power == c2.power:
            log_info("   -> ÉGALITÉ ! Remélange...")
            self.state.deck.append(c1)
            self.state.deck.append(c2)
            random.shuffle(self.state.deck)
            self._draw_initiative_cards()  # On repioche immédiatement pour affichage
            return

        # Cas 2 : Vainqueur trouvé
        winner_idx = 0 if c1.power > c2.power else 1
        log_info(
            f"   -> {'P1' if winner_idx == 0 else 'P2'} gagne l'initiative !")

        # Les cartes du duel sont définitivement écartées (ni deck, ni défausse)
        self.state.initiative_duel = None

        # On lance la vraie partie
        self._distribute_and_start(winner_idx)

    def _distribute_and_start(self, starter_idx):
        """Distribution finale et démarrage du jeu."""
        p1 = self.state.player1
        p2 = self.state.player2

        # 1. Distribution des MAINS (5 cartes chacun)
        for _ in range(5):
            if self.state.deck:
                p1.hand.append(self.state.deck.pop())
            if self.state.deck:
                p2.hand.append(self.state.deck.pop())

        # 2. Distribution des PIOCHES PERSONNELLES (5 cartes chacun)
        while self.state.deck:
            if len(p1.deck) < 5:
                p1.deck.append(self.state.deck.pop())
            elif len(p2.deck) < 5:
                p2.deck.append(self.state.deck.pop())
            else:
                break  # Sécurité

        self.state.turn_count = 1
        self.state.active_player_idx = starter_idx
        self.state.phase = Phase.P1_MAIN if starter_idx == 0 else Phase.P2_MAIN
        self.state.winner = None

        if self.verbose:
            log_info(
                f"✅ Partie lancée. Joueur actif : {self.state.active_player.name}")
            log_info(f"   P1 Deck: {len(p1.deck)}, P2 Deck: {len(p2.deck)}")

    def step(self, action_type: str, index: int = -1):
        if self.state.winner:
            log_info("⚠️ Action ignorée : Partie terminée.")
            return

        if self.verbose:
            log_info(f"▶ STEP : {action_type} (idx={index})")

        self.update_board_states()

        try:
            command = CommandFactory.create(action_type, index, self)
            if command:
                command.execute(self)
            else:
                log_debug(f"❌ Commande inconnue ou invalide : {action_type}")
        except Exception as e:
            log_error(f"❌ CRASH EXECUTION : {e}")
            if self.verbose:
                traceback.print_exc()
            return

        self.turn_manager.check_win_condition()

    def get_legal_moves(self) -> List[Tuple[str, int]]:
        self.update_board_states()
        if self.state.winner:
            return []

        moves = []
        ap = self.state.active_player
        phase = self.state.phase

        # --- FIX FRENZY (State Persistence) ---
        if self.state.frenzy_candidate:
            # On vérifie si la carte est toujours en jeu (sur un board)
            in_p1 = self.state.frenzy_candidate in self.state.player1.board
            in_p2 = self.state.frenzy_candidate in self.state.player2.board

            if in_p1 or in_p2:
                owner = self.state.player1 if in_p1 else self.state.player2
                # Si c'est à nous de jouer, on force l'attaque
                if ap == owner:
                    idx = ap.board.index(self.state.frenzy_candidate)
                    return [("ATTACK", idx)]
                # Sinon (tour adversaire pour bloquer), on garde le frenzy_candidate actif
            else:
                # Carte disparue
                self.state.frenzy_candidate = None

        if phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            moves.extend([("PLAY", i) for i in range(len(ap.hand))])
            moves.extend([("ATTACK", i) for i in range(len(ap.board))])
        elif phase == Phase.MINDBUG_DECISION:
            moves.append(("PASS", -1))
            if ap.mindbugs > 0:
                moves.append(("MINDBUG", -1))
        elif phase == Phase.BLOCK_DECISION:
            moves.append(("NO_BLOCK", -1))
            attacker = self.state.pending_attacker
            if attacker:
                from mindbug.engine.utils.combat_utils import CombatUtils
                for i, blocker in enumerate(ap.board):
                    if CombatUtils.can_block(attacker, blocker):
                        moves.append(("BLOCK", i))
        elif phase == Phase.RESOLUTION_CHOICE:
            req = self.state.active_request
            if req and req.candidates:
                selector = req.selector
                opp_selector = self.state.player2 if selector == self.state.player1 else self.state.player1

                # Helper pour ajouter les indices valides
                def add_indices(collection, type_str):
                    for i, c in enumerate(collection):
                        if c in req.candidates:
                            moves.append((type_str, i))

                add_indices(selector.hand, "SELECT_HAND")
                add_indices(selector.board, "SELECT_BOARD")
                add_indices(selector.discard, "SELECT_DISCARD")
                add_indices(opp_selector.hand, "SELECT_OPP_HAND")
                add_indices(opp_selector.board, "SELECT_OPP_BOARD")
                add_indices(opp_selector.discard, "SELECT_OPP_DISCARD")

        elif phase == Phase.INITIATIVE_BATTLE:
            # Seule action possible : Confirmer/Continuer
            pass

        return moves

    def ask_for_selection(self, candidates: List[Any], reason: str, count: int, selector: Player, callback=None):
        self.query_manager.start_selection_request(
            candidates, reason, count, selector, callback)

    def execute_mindbug_replay(self):
        log_info("🔄 REPLAY ! The original player draws and plays again.")
        self.turn_manager.switch_active_player()
        self.turn_manager.refill_hand(self.state.active_player)
        self.state.phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN

    def resolve_selection_effect(self, selected_object: Any):
        is_completed = self.query_manager.resolve_selection([selected_object])
        if is_completed and self.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("▶️ Resuming flow after selection.")

            if getattr(self.state, "mindbug_replay_pending", False):
                self.state.mindbug_replay_pending = False
                self.execute_mindbug_replay()
                return

            if self.state.pending_attacker:
                attacker = self.state.pending_attacker
                att_owner = self.state.player1 if attacker in self.state.player1.board else self.state.player2
                defender = self.state.player2 if att_owner == self.state.player1 else self.state.player1

                # Fix : HUNTER doit encore se déclencher après l'effet ON_ATTACK
                if self.state.hunter_pending:
                    self.state.hunter_pending = False
                    has_targets = len(defender.board) > 0
                    if has_targets:
                        from functools import partial
                        from mindbug.engine.commands.definitions import AttackCommand
                        callback = partial(AttackCommand._on_hunter_target_selected, self)
                        candidates = list(defender.board) + ["NO_HUNT"]
                        self.ask_for_selection(
                            candidates=candidates,
                            reason="HUNTER_TARGET",
                            count=1,
                            selector=att_owner,
                            callback=callback
                        )
                        return
                    # Si plus de cibles après l'ON_ATTACK (cible détruite), attaque directe
                    log_info("   -> No Hunter targets left, resolving as direct attack.")
                    self.resolve_combat(blocker=None)
                    return

                log_info("⚔️ Resuming Attack Sequence -> Moving to Block Phase.")
                self.state.phase = Phase.BLOCK_DECISION
                self.turn_manager.switch_active_player()
                return

            if getattr(self.state, "end_turn_pending", False):
                self.state.end_turn_pending = False
                self.turn_manager.end_turn()

    def resolve_combat(self, blocker: Optional[Card]):
        attacker = self.state.pending_attacker
        if not attacker:
            return

        self.combat_manager.resolve_fight(attacker, blocker)
        self.update_board_states()

        # Si le combat a déclenché une sélection (ex: On Death), on pause
        if self.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("⏸️ Combat resolution paused for Selection.")
            return

        self.state.pending_attacker = None

        # Vérification victoire (Si l'attaque a tué le joueur, on arrête tout)
        self.turn_manager.check_win_condition()
        if self.state.winner:
            return

        # Gestion Frenzy
        att_owner = self.state.player1 if attacker in self.state.player1.board else self.state.player2
        is_alive = attacker in att_owner.board
        has_frenzy = Keyword.FRENZY in attacker.keywords

        # Si la carte est vivante, a Fureur et n'a pas encore utilisé son bonus (c'est la 1ère attaque)
        if is_alive and has_frenzy and self.state.frenzy_candidate != attacker:
            log_info(f"🔥 FRENZY ! {attacker.name} prepares to attack again.")
            self.state.frenzy_candidate = attacker

            # On redonne la main à l'attaquant
            self.turn_manager.switch_active_player()
            self.state.phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN

            # AUTO ATTACK frenzy
            # On déclare immédiatement la seconde attaque pour éviter un clic inutile
            att_idx = att_owner.board.index(attacker)
            log_info(f"⚡ Auto-Attack triggered for Frenzy.")
            self.step("ATTACK", att_idx)

            return

        self.state.frenzy_candidate = None
        self.turn_manager.switch_active_player()
        self.turn_manager.end_turn()

    def check_game_over(self):
        # Délégation au TurnManager
        self.turn_manager.check_win_condition()

    def put_card_on_board(self, player: Player, card: Card):
        player.board.append(card)

        # Vérification des effets de banissement (Silence)
        opponent = self.state.player2 if player == self.state.player1 else self.state.player1
        is_silenced = False
        from mindbug.engine.core.consts import EffectType

        for opp_card in opponent.board:
            if opp_card.trigger == Trigger.PASSIVE:
                for eff in opp_card.effects:
                    if eff.type == EffectType.BAN and eff.params.get("action") == "TRIGGER_ON_PLAY":
                        is_silenced = True
                        break

        if not is_silenced and card.trigger == Trigger.ON_PLAY:
            self.effect_manager.apply_effect(card, player, opponent)

    def update_board_states(self):
        for p in self.state.players:
            for c in p.board:
                c.refresh_state()
        self.effect_manager.apply_passive_effects()

    def clone(self):
        """
        Crée une copie profonde et légère du jeu pour la simulation IA.
        Optimisé via pickle et __getstate__.
        """
        new_game = MindbugGame.__new__(MindbugGame)
        new_game.verbose = False

        # Copie par référence des éléments immuables ou statiques
        new_game.config = self.config
        new_game.deck_factory = self.deck_factory

        # OPTIMISATION MAJEURE : Pickle est ~5-10x plus rapide que deepcopy pour ce cas
        new_game.state = pickle.loads(pickle.dumps(self.state))

        # Reconstruction des managers (rapide)
        new_game.turn_manager = TurnManager(new_game)
        new_game.query_manager = QueryManager(new_game)
        new_game.combat_manager = CombatManager(new_game)
        new_game.effect_manager = EffectManager(new_game)

        # Ré-injection des dépendances croisées
        new_game.combat_manager.effect_manager = new_game.effect_manager

        return new_game
