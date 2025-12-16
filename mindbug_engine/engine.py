import random
import sys
import os
import json
from typing import Optional, List, Tuple

# Imports internes
from .models import Card, Player
from .rules import Phase, Keyword, CombatUtils
from .effects import EffectManager
from .combat import CombatManager
from .commands import (
    PlayCardCommand, AttackCommand, BlockCommand, NoBlockCommand,
    MindbugCommand, PassCommand, ResolveSelectionCommand
)
from .logger import log_info, log_debug, log_error

# Imports depuis la racine
from constants import PATH_DATA, resource_path


class MindbugGame:
    def __init__(self, active_card_ids=None, active_sets=None, verbose=True, deck_path=None):
        self.verbose = verbose
        if self.verbose:
            log_info("=== INITIALISATION DU MOTEUR ===")

        all_cards_loaded = self._load_cards_from_json(deck_path)

        if active_sets:
            all_cards = [c for c in all_cards_loaded if getattr(c, 'set', 'FIRST_CONTACT') in active_sets]
            if not all_cards: all_cards = list(all_cards_loaded)
        else:
            all_cards = list(all_cards_loaded)

        if active_card_ids:
            self.full_deck = [c for c in all_cards if c.id in active_card_ids]
            current_count = len(self.full_deck)
            if current_count < 20:
                selected_ids = set(c.id for c in self.full_deck)
                available_pool = [c for c in all_cards if c.id not in selected_ids]
                missing = 20 - current_count
                if len(available_pool) >= missing:
                    self.full_deck.extend(random.sample(available_pool, missing))
                else:
                    self.full_deck.extend(available_pool)
        else:
            self.full_deck = list(all_cards)

        self.all_cards_ref = list(all_cards)

        if len(self.full_deck) > 20:
            self.full_deck = random.sample(self.full_deck, 20)
        else:
            random.shuffle(self.full_deck)

        self.player1 = Player(name="P1")
        self.player2 = Player(name="P2")
        self.players = [self.player1, self.player2]

        self._setup_player(self.player1)
        self._setup_player(self.player2)

        self.active_player_idx = 0
        self.phase = Phase.P1_MAIN
        self.turn_count = 1
        self.winner = None

        self.pending_card: Optional[Card] = None
        self.pending_attacker: Optional[Card] = None
        self.selection_context = None

        self.end_turn_pending = False
        self.mindbug_replay_pending = False
        self.frenzy_candidate = None

        self.effect_manager = EffectManager()
        self.combat_manager = CombatManager(self)

    def _load_cards_from_json(self, specific_path=None):
        target_path = specific_path if specific_path else PATH_DATA
        if not os.path.exists(target_path):
            if not specific_path:
                log_error(f"⚠️ ERREUR CRITIQUE : Fichier de données introuvable : {target_path}")
            return []
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [Card.from_dict(c) for c in data]
        except Exception as e:
            log_error(f"⚠️ Erreur lors du chargement du JSON ({target_path}) : {e}")
            return []

    def log(self, message):
        if getattr(self, 'verbose', True):
            log_info(f"[GAME] {message}")

    def _setup_player(self, player):
        for _ in range(5):
            if self.full_deck: player.hand.append(self.full_deck.pop())
        for _ in range(5):
            if self.full_deck: player.deck.append(self.full_deck.pop())
        self.refill_hand(player)

    def refill_hand(self, player):
        while len(player.hand) < 5 and len(player.deck) > 0:
            card = player.deck.pop()
            player.hand.append(card)

    @property
    def active_player(self):
        return self.players[self.active_player_idx]

    @property
    def opponent(self):
        return self.players[1 - self.active_player_idx]

    def clone(self):
        new_game = MindbugGame.__new__(MindbugGame)
        new_game.verbose = False
        new_game.active_player_idx = self.active_player_idx
        new_game.phase = self.phase
        new_game.turn_count = self.turn_count
        new_game.winner = None
        new_game.end_turn_pending = self.end_turn_pending
        new_game.mindbug_replay_pending = self.mindbug_replay_pending

        new_game.player1 = self.player1.copy()
        new_game.player2 = self.player2.copy()
        new_game.players = [new_game.player1, new_game.player2]
        new_game.full_deck = [c.copy() for c in self.full_deck]
        new_game.all_cards_ref = self.all_cards_ref
        new_game.effect_manager = self.effect_manager

        from .combat import CombatManager
        new_game.combat_manager = CombatManager(new_game)

        if self.pending_card:
            new_game.pending_card = self.pending_card.copy()
        else:
            new_game.pending_card = None

        new_game.pending_attacker = self._find_card_copy(self.pending_attacker, new_game)
        new_game.frenzy_candidate = self._find_card_copy(self.frenzy_candidate, new_game)

        if self.selection_context:
            initiator_idx = 0 if self.selection_context["initiator"] == self.player1 else 1
            new_game.selection_context = {
                "effect_code": self.selection_context["effect_code"],
                "count": self.selection_context["count"],
                "initiator": new_game.players[initiator_idx],
                "candidates": [self._find_card_copy(c, new_game) for c in self.selection_context["candidates"]]
            }
        else:
            new_game.selection_context = None
        return new_game

    def _find_card_copy(self, original_card, new_game_instance):
        if original_card is None: return None
        all_new_cards = (
                new_game_instance.player1.hand + new_game_instance.player1.board + new_game_instance.player1.discard +
                new_game_instance.player2.hand + new_game_instance.player2.board + new_game_instance.player2.discard +
                new_game_instance.full_deck
        )
        if new_game_instance.pending_card:
            all_new_cards.append(new_game_instance.pending_card)
        for c in all_new_cards:
            if c.id == original_card.id and c.name == original_card.name and c.power == original_card.power:
                return c
        return None

    def calculate_real_power(self, card: Card) -> int:
        return self.combat_manager.calculate_real_power(card, self.active_player, self.opponent)

    def resolve_combat(self, blocker: Optional[Card]):
        attacker = self.pending_attacker
        attacker_owner = self.opponent
        att_dead, blk_dead = self.combat_manager.resolve_fight(attacker, blocker)
        self.pending_attacker = None

        if self.phase == Phase.RESOLUTION_CHOICE:
            self.log("   -> Combat interrupted (Selection required).")
            self.end_turn_pending = True
            return

            # Tentative d'activation Fureur
        if self._try_activate_frenzy(attacker, attacker_owner, att_dead):
            # Si fureur activée, on NE change PAS de joueur et on NE finit PAS le tour.
            # La méthode _try_activate_frenzy a déjà configuré le jeu pour la suite.
            return

            # Si pas de fureur (ou fin de fureur), on passe au tour suivant normalement
        self.switch_active_player()
        self.end_turn()

    def _try_activate_frenzy(self, attacker: Card, owner: Player, is_dead: bool) -> bool:
        """
        Active la Fureur : Relance immédiatement une attaque automatique.
        """
        survived = (not is_dead) and (attacker in owner.board)
        has_frenzy = Keyword.FRENZY.value in attacker.keywords
        # On vérifie si c'est déjà l'attaque bonus pour éviter les boucles infinies
        is_bonus_attack = (self.frenzy_candidate == attacker)

        self.frenzy_candidate = None

        if survived and has_frenzy and not is_bonus_attack:
            self.log(f"> 🔥 FRENZY ACTIVATED ! {attacker.name} attacks again automatically !")

            # 1. On marque la carte comme étant en cours de Fureur
            self.frenzy_candidate = attacker

            # 2. On configure l'attaquant pour le prochain combat
            self.pending_attacker = attacker

            # 3. On passe immédiatement en phase de décision de blocage
            self.phase = Phase.BLOCK_DECISION

            # 4. On s'assure que le joueur actif est le DEFENSEUR (celui qui doit bloquer)
            # owner = Attaquant. Si active_player == Attaquant, on switche vers le Défenseur.
            if self.active_player == owner:
                self.switch_active_player()

            # On retourne True pour dire à resolve_combat "Ne finis pas le tour !"
            return True

        return False

    def step(self, action_type: str, target_idx: int = -1, target_blocker_idx: int = -1):
        if self.winner:
            log_info("Action ignorée : La partie est déjà finie.")
            return

        if self.verbose:
            log_debug(
                f"▶ STEP REÇU : {action_type} (idx={target_idx}) | Phase: {self.phase} | Active: {self.active_player.name}")

        self.update_board_states()

        command = None
        if action_type == "PLAY":
            command = PlayCardCommand(target_idx)
        elif action_type == "ATTACK":
            command = AttackCommand(target_idx, target_blocker_idx)
        elif action_type == "BLOCK":
            command = BlockCommand(target_idx)
        elif action_type == "NO_BLOCK":
            command = NoBlockCommand()
        elif action_type == "MINDBUG":
            command = MindbugCommand()
        elif action_type == "PASS":
            command = PassCommand()
        elif action_type.startswith("SELECT_"):
            parts = action_type.split("_", 1)
            if len(parts) > 1: command = ResolveSelectionCommand(parts[1], target_idx)

        if command:
            try:
                command.execute(self)
                if self.verbose: log_debug(f"✔ Commande {action_type} exécutée avec succès.")
            except Exception as e:
                log_error(f"❌ CRASH dans command.execute : {e}")
                import traceback
                log_error(traceback.format_exc())
        else:
            log_error(f"❌ Commande inconnue ou invalide : {action_type}")

        self._check_win_condition()
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)

        if self.verbose:
            log_debug(f"   -> Nouvel état : Phase={self.phase}, Active={self.active_player.name}")

    def switch_active_player(self):
        old = self.active_player.name
        self.active_player_idx = 1 - self.active_player_idx
        if self.verbose:
            log_debug(f"🔄 Switch Player : {old} -> {self.active_player.name}")

    def end_turn(self):
        self.refill_hand(self.player1)
        self.refill_hand(self.player2)
        self.switch_active_player()
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN
        self.turn_count += 1
        self.log(f"--- Turn end. Turn of {self.active_player.name} ---")

    def execute_mindbug_replay(self):
        self.switch_active_player()
        self.log(f"> Turn returns to {self.active_player.name} (Replays turn).")
        self.phase = Phase.P1_MAIN if self.active_player_idx == 0 else Phase.P2_MAIN

    def put_card_on_board(self, player, card):
        player.board.append(card)
        opponent = self.player2 if player == self.player1 else self.player1
        is_silenced = False
        for opp_card in opponent.board:
            if opp_card.ability and opp_card.trigger == "PASSIVE" and opp_card.ability.code == "SILENCE_ON_PLAY":
                self.log(f"> Effect cancelled by {opp_card.name} (Silence) !")
                is_silenced = True
                break
        if not is_silenced and card.trigger == "ON_PLAY":
            self.effect_manager.apply_effect(self, card, player, opponent)

    def resolve_selection_effect(self, selected_card: Card):
        ctx = self.selection_context
        if not ctx: return
        effect = ctx["effect_code"]
        initiator = ctx["initiator"]
        self.log(f"> Target chosen : {selected_card.name}")

        if effect == "DESTROY_CREATURE" or effect == "DESTROY_IF_FEWER_ALLIES":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            self.combat_manager.apply_lethal_damage(selected_card, victim)

        elif effect == "STEAL_CREATURE":
            victim = self.player1 if selected_card in self.player1.board else self.player2
            if selected_card in victim.board:
                victim.board.remove(selected_card)
                initiator.board.append(selected_card)

        elif effect == "HUNTER_TARGET":
            self.log(f"   -> {initiator.name} forces {selected_card.name} to block !")
            self.selection_context = None
            if self.active_player_idx == 0:
                self.phase = Phase.P1_MAIN
            else:
                self.phase = Phase.P2_MAIN
            self.resolve_combat(selected_card)
            return

        elif effect == "RECLAIM_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                initiator.hand.append(selected_card)
                selected_card.reset()

        elif effect == "PLAY_FROM_OPP_DISCARD" or effect == "PLAY_FROM_MY_DISCARD":
            owner = self.player1 if selected_card in self.player1.discard else self.player2
            if selected_card in owner.discard:
                owner.discard.remove(selected_card)
                self.put_card_on_board(initiator, selected_card)
                selected_card.reset()

        ctx["count"] -= 1
        if ctx["count"] <= 0:
            self.log("   -> Selection end.")
            self.selection_context = None
            if self.mindbug_replay_pending:
                self.mindbug_replay_pending = False
                self.execute_mindbug_replay()
            elif self.end_turn_pending:
                self.end_turn_pending = False
                self.end_turn()
            else:
                if self.active_player_idx == 0:
                    self.phase = Phase.P1_MAIN
                else:
                    self.phase = Phase.P2_MAIN
        else:
            self.log(f"   -> Still {ctx['count']} target(s) to choose...")

    def update_board_states(self):
        for player in [self.player1, self.player2]:
            opponent = self.player2 if player == self.player1 else self.player1
            enemy_keywords = set()
            for card in opponent.board:
                enemy_keywords.update(card.keywords)
            for card in player.board:
                if card.ability and card.trigger == "PASSIVE" and card.ability.code == "COPY_ALL_KEYWORDS_FROM_ENEMIES":
                    target_keywords = ["HUNTER", "SNEAKY", "POISON", "FRENZY", "TOUGH"]
                    for kw in target_keywords:
                        if kw in enemy_keywords:
                            if kw not in card.keywords: card.keywords.append(kw)
                        else:
                            if kw in card.keywords and kw not in card.base_keywords:
                                card.keywords.remove(kw)

    def get_legal_moves(self) -> List[Tuple[str, int]]:
        self.update_board_states()
        moves = []
        player = self.active_player
        if self.winner: return []

        if self.phase in [Phase.P1_MAIN, Phase.P2_MAIN]:

            # Si une carte est en mode Fureur, on ne peut QU'attaquer avec elle.
            if self.frenzy_candidate:
                if self.frenzy_candidate in player.board:
                    idx = player.board.index(self.frenzy_candidate)
                    moves.append(("ATTACK", idx))
                    return moves  # <--- ON RETOURNE DIRECTEMENT, STOP.
                else:
                    # Sécurité : Si la carte a disparu (morte), on annule la fureur
                    self.frenzy_candidate = None

            # Tour normal (si pas de fureur)
            for i in range(len(player.hand)): moves.append(("PLAY", i))
            for i in range(len(player.board)): moves.append(("ATTACK", i))

        elif self.phase == Phase.MINDBUG_DECISION:
            moves.append(("PASS", -1))
            if player.mindbugs > 0: moves.append(("MINDBUG", -1))

        elif self.phase == Phase.BLOCK_DECISION:
            moves.append(("NO_BLOCK", -1))
            attacker = self.pending_attacker
            if attacker:
                for i, blocker in enumerate(player.board):
                    if CombatUtils.can_block(attacker, blocker):
                        moves.append(("BLOCK", i))

        elif self.phase == Phase.RESOLUTION_CHOICE:
            if self.selection_context:
                candidates = self.selection_context["candidates"]
                for i, card in enumerate(self.player1.board):
                    if card in candidates: moves.append(("SELECT_BOARD_P1", i))
                for i, card in enumerate(self.player2.board):
                    if card in candidates: moves.append(("SELECT_BOARD_P2", i))
                for i, card in enumerate(self.player1.discard):
                    if card in candidates: moves.append(("SELECT_DISCARD_P1", i))
                for i, card in enumerate(self.player2.discard):
                    if card in candidates: moves.append(("SELECT_DISCARD_P2", i))
        return moves

    def ask_for_selection(self, candidates: List[Card], effect_code: str, count: int, initiator: Player):
        if not candidates:
            self.log("   -> No target available (Selection cancelled).")
            return
        self.log(f"⌛ WAITING : {initiator.name} must choose a target for {effect_code}.")
        self.selection_context = {
            "candidates": candidates,
            "effect_code": effect_code,
            "count": count,
            "initiator": initiator
        }
        self.phase = Phase.RESOLUTION_CHOICE
        # Si ce n'est pas au tour de celui qui doit choisir (ex: Attaquant pendant le tour du Défenseur),
        # on force le changement de joueur actif immédiatement.
        if self.active_player != initiator:
            self.log(f"🔄 Handover to {initiator.name} for selection.")
            self.switch_active_player()

    def _check_win_condition(self):
        if self.player1.hp <= 0:
            self.winner = self.player2
        elif self.player2.hp <= 0:
            self.winner = self.player1

    def render(self):
        pass