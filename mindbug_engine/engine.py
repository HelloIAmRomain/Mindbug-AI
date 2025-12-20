import random
import traceback
import copy
from typing import Optional, List, Tuple, Any

from mindbug_engine.utils.logger import log_info, log_debug, log_error

# --- IMPORTS CORE ---
from mindbug_engine.core.models import Card, Player
from mindbug_engine.core.state import GameState
from mindbug_engine.core.consts import Phase, Keyword, Trigger

# --- IMPORTS INFRASTRUCTURE ---
from mindbug_engine.infrastructure.deck_factory import DeckFactory
from constants import PATH_DATA

# --- IMPORTS MANAGERS ---
from mindbug_engine.managers.turn_manager import TurnManager
from mindbug_engine.managers.combat_manager import CombatManager
from mindbug_engine.managers.effect_manager import EffectManager
from mindbug_engine.managers.query_manager import QueryManager
from mindbug_engine.managers.settings_manager import SettingsManager

# --- IMPORTS COMMANDS & BUILDER ---
from mindbug_engine.commands.command_factory import CommandFactory
from mindbug_engine.game_builder import GameBuilder


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
        # On utilise le chemin des données défini globalement ou dans config
        from mindbug_engine.infrastructure.deck_factory import DeckFactory
        from constants import PATH_DATA  # Assurez-vous que ce chemin est correct

        self.deck_factory = DeckFactory(PATH_DATA)

        # Création du deck basé sur les sets actifs de la configuration
        game_deck, all_cards_ref, used_sets = self.deck_factory.create_deck(
            active_sets=self.config.active_sets
        )

        # 3. État du Jeu (GameState)
        from mindbug_engine.core.models import Player
        from mindbug_engine.core.state import GameState

        # On crée les joueurs ici pour les injecter dans le State
        p1 = Player(name="P1")
        p2 = Player(name="P2")

        # Correction de l'appel : GameState(deck, player1, player2)
        self.state = GameState(game_deck, p1, p2)
        self.state.all_cards_ref = all_cards_ref

        # 4. Managers de Logique (Specialized Managers)
        # Chaque manager s'occupe d'un aspect précis des règles
        from mindbug_engine.managers.turn_manager import TurnManager
        from mindbug_engine.managers.effect_manager import EffectManager
        from mindbug_engine.managers.combat_manager import CombatManager
        from mindbug_engine.managers.query_manager import QueryManager

        # On initialise d'abord les managers qui n'ont pas de dépendances croisées critiques
        self.query_manager = QueryManager(self)
        self.turn_manager = TurnManager(self)

        # On crée le CombatManager AVANT l'EffectManager car l'EffectManager
        # y accède directement dans son __init__
        self.combat_manager = CombatManager(self)
        self.effect_manager = EffectManager(self)

        # Injection croisée finale pour être sûr que tout le monde se connaît
        self.combat_manager.effect_manager = self.effect_manager

        # 5. État d'exécution (Runtime flags)
        self.is_over = False
        self.history = []  # Pour un futur système de Replay / Undo

        if self.verbose:
            print(f"🎮 Jeu initialisé avec les sets : {used_sets}")
            print(f"🤖 Difficulté IA : {self.config.ai_difficulty.value}")

    def start_game(self):
        """
        Démarre la partie : Mélange, Distribution et Reset des stats.
        """
        # Utilisation du deck déjà initialisé dans self.state lors du __init__
        if not self.state.deck:
            log_error("Impossible de démarrer : Le deck est vide.")
            return

        if self.verbose:
            log_info(f"🎲 Démarrage de la partie... Deck: {len(self.state.deck)} cartes.")

        # 1. Mélange du deck initial
        random.shuffle(self.state.deck)

        # 2. Reset et distribution (5 cartes par joueur)
        self.state.player1.hand = []
        self.state.player2.hand = []

        for _ in range(5):
            if self.state.deck:
                self.state.player1.hand.append(self.state.deck.pop())
            if self.state.deck:
                self.state.player2.hand.append(self.state.deck.pop())

        # 3. Configuration des stats de départ
        self.state.turn_count = 1
        self.state.active_player_idx = 0
        self.state.phase = Phase.P1_MAIN
        self.state.winner = None

        for p in self.state.players:
            p.hp = 3
            p.mindbugs = 2
            p.board = []
            p.discard = []

        if self.verbose:
            log_info("✅ Partie prête. Tour du Joueur 1.")


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
        # Copier-coller votre méthode get_legal_moves existante ici
        # (Elle n'a pas changé avec le refacto Settings)
        self.update_board_states()
        if self.state.winner: return []

        moves = []
        ap = self.state.active_player
        phase = self.state.phase

        if self.state.frenzy_candidate:
            if self.state.frenzy_candidate in ap.board:
                idx = ap.board.index(self.state.frenzy_candidate)
                return [("ATTACK", idx)]
            else:
                self.state.frenzy_candidate = None

        if phase in [Phase.P1_MAIN, Phase.P2_MAIN]:
            moves.extend([("PLAY", i) for i in range(len(ap.hand))])
            moves.extend([("ATTACK", i) for i in range(len(ap.board))])
        elif phase == Phase.MINDBUG_DECISION:
            moves.append(("PASS", -1))
            if ap.mindbugs > 0: moves.append(("MINDBUG", -1))
        elif phase == Phase.BLOCK_DECISION:
            moves.append(("NO_BLOCK", -1))
            attacker = self.state.pending_attacker
            if attacker:
                from mindbug_engine.utils.combat_utils import CombatUtils
                for i, blocker in enumerate(ap.board):
                    if CombatUtils.can_block(attacker, blocker):
                        moves.append(("BLOCK", i))
        elif phase == Phase.RESOLUTION_CHOICE:
            req = self.state.active_request
            if req and req.candidates:
                selector = req.selector
                opp_selector = self.state.player2 if selector == self.state.player1 else self.state.player1
                for i, c in enumerate(selector.hand):
                    if c in req.candidates: moves.append(("SELECT_HAND", i))
                for i, c in enumerate(selector.board):
                    if c in req.candidates: moves.append(("SELECT_BOARD", i))
                for i, c in enumerate(selector.discard):
                    if c in req.candidates: moves.append(("SELECT_DISCARD", i))
                for i, c in enumerate(opp_selector.hand):
                    if c in req.candidates: moves.append(("SELECT_OPP_HAND", i))
                for i, c in enumerate(opp_selector.board):
                    if c in req.candidates: moves.append(("SELECT_OPP_BOARD", i))
                for i, c in enumerate(opp_selector.discard):
                    if c in req.candidates: moves.append(("SELECT_OPP_DISCARD", i))
        return moves

    def ask_for_selection(self, candidates: List[Any], reason: str, count: int, selector: Player, callback=None):
        self.query_manager.start_selection_request(candidates, reason, count, selector, callback)

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
                log_info("⚔️ Resuming Attack Sequence -> Moving to Block Phase.")
                self.state.phase = Phase.BLOCK_DECISION
                self.turn_manager.switch_active_player()
                return
            if self.state.active_player_idx == 0 and self.state.active_player != self.state.player1:
                self.turn_manager.switch_active_player()
            elif self.state.active_player_idx == 1 and self.state.active_player != self.state.player2:
                self.turn_manager.switch_active_player()
            if getattr(self.state, "end_turn_pending", False):
                self.state.end_turn_pending = False
            self.turn_manager.end_turn()

    def resolve_combat(self, blocker: Optional[Card]):
        attacker = self.state.pending_attacker
        if not attacker: return
        self.combat_manager.resolve_fight(attacker, blocker)
        self.update_board_states()
        if self.state.phase == Phase.RESOLUTION_CHOICE:
            log_info("⏸️ Combat resolution paused for Selection.")
            return
        self.state.pending_attacker = None
        att_owner = self.state.player1 if attacker in self.state.player1.board else self.state.player2
        is_alive = attacker in att_owner.board
        has_frenzy = Keyword.FRENZY in attacker.keywords
        if is_alive and has_frenzy and self.state.frenzy_candidate != attacker:
            log_info(f"🔥 FRENZY ! {attacker.name} prepares to attack again.")
            self.state.frenzy_candidate = attacker
            self.turn_manager.switch_active_player()
            self.state.phase = Phase.P1_MAIN if self.state.active_player_idx == 0 else Phase.P2_MAIN
            return
        self.state.frenzy_candidate = None
        self.turn_manager.switch_active_player()
        self.turn_manager.end_turn()

    def check_game_over(self):
        if self.state.player1.hp <= 0:
            self.state.winner = self.state.player2
            log_info(f"🏆 VICTOIRE : {self.state.player2.name} gagne la partie !")
        elif self.state.player2.hp <= 0:
            self.state.winner = self.state.player1
            log_info(f"🏆 VICTOIRE : {self.state.player1.name} gagne la partie !")

    def put_card_on_board(self, player: Player, card: Card):
        player.board.append(card)
        # Logique simplifiée de silence (à externaliser si besoin)
        opponent = self.state.player2 if player == self.state.player1 else self.state.player1
        is_silenced = False
        from mindbug_engine.core.consts import EffectType
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
        new_game = MindbugGame.__new__(MindbugGame)
        new_game.verbose = False
        new_game.deck_factory = self.deck_factory
        new_game.state = copy.deepcopy(self.state)
        new_game.turn_manager = TurnManager(new_game)
        new_game.query_manager = QueryManager(new_game)
        new_game.combat_manager = CombatManager(new_game)
        new_game.effect_manager = EffectManager(new_game)
        new_game.combat_manager.effect_manager = new_game.effect_manager
        # Settings et Builder ne sont pas critiques pour le clone (utilisé pour l'IA Combat)
        # mais on peut les ajouter si besoin.
        new_game.preconfigured_deck = self.preconfigured_deck
        return new_game