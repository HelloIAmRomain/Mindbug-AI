import random
from typing import List, TYPE_CHECKING
from .models import Card, Player

if TYPE_CHECKING:
    from .engine import MindbugGame

class EffectManager:
    @staticmethod
    def apply_effect(game: 'MindbugGame', card: Card, owner: Player, opponent: Player):
        if not card.ability: return

        code = card.ability.code
        val = card.ability.value
        condition_type = card.ability.condition
        threshold = card.ability.condition_value
        target_type = card.ability.target

        print(f"✨ EFFET : {code} (Val:{val}) pour {card.name}")

        if code == "HEAL":
            if target_type == "SELF": owner.hp += val
        elif code == "DAMAGE":
            if target_type == "OPP": opponent.hp -= val
        elif code == "DAMAGE_UNBLOCKED":
            opponent.hp -= val
        elif code == "SET_HP_EQUAL_OPPONENT":
            owner.hp = opponent.hp
        elif code == "SET_OPPONENT_HP_TO_ONE":
            if opponent.hp > 1: opponent.hp = 1
        
        elif code == "STEAL_CREATURE":
            EffectManager._resolve_steal_creature(game, owner, opponent, val, condition_type, threshold)
        elif code == "STEAL_CARD_HAND":
            EffectManager._resolve_steal_hand(game, owner, opponent, val)
        elif code == "RECLAIM_DISCARD":
            EffectManager._resolve_reclaim_discard(game, owner, val)
        elif code == "RECLAIM_ALL_DISCARD":
            EffectManager._resolve_reclaim_all_discard(owner)
        elif code == "PLAY_FROM_MY_DISCARD":
            EffectManager._resolve_play_my_discard(game, owner, val)
        
        elif code == "DISCARD_RANDOM" or code == "DISCARD_OPPONENT_CHOICE":
            EffectManager._resolve_discard_random(game, opponent, val)
        
        elif code == "DESTROY_CREATURE":
            EffectManager._resolve_destroy_creature(game, opponent, val, condition_type, threshold)
        elif code == "DESTROY_ALL_ENEMIES":
            EffectManager._resolve_destroy_all(game, opponent, condition_type, threshold)
        elif code == "DESTROY_IF_FEWER_ALLIES":
            if len(owner.board) < len(opponent.board):
                 EffectManager._resolve_destroy_creature(game, opponent, val, condition_type, threshold)
        elif code == "PLAY_FROM_OPP_DISCARD":
            EffectManager._resolve_play_opp_discard(game, owner, opponent, val)
        elif code == "OPPONENT_SACRIFICE":
            EffectManager._resolve_sacrifice(game, opponent, val)

    @staticmethod
    def _get_valid_targets(candidates: List[Card], condition_type: str, threshold: int) -> List[Card]:
        if not candidates: return []
        if not condition_type or condition_type in ["ALWAYS", "NONE", "CHOICE_USER"]: return candidates
        filtered = []
        for card in candidates:
            is_valid = False
            if condition_type == "MIN_POWER": 
                if card.power >= threshold: is_valid = True
            elif condition_type == "MAX_POWER": 
                if card.power <= threshold: is_valid = True
            elif condition_type == "EXACT_POWER": 
                if card.power == threshold: is_valid = True
            if is_valid: filtered.append(card)
        return filtered

    @staticmethod
    def _resolve_steal_creature(game, thief, victim, count, cond_type, threshold):
        candidates = EffectManager._get_valid_targets(victim.board, cond_type, threshold)
        if not candidates: return
        game.ask_for_selection(candidates, "STEAL_CREATURE", count, thief)

    @staticmethod
    def _resolve_destroy_creature(game, victim, count, cond_type, threshold):
        candidates = EffectManager._get_valid_targets(victim.board, cond_type, threshold)
        if not candidates: return
        initiator = game.active_player 
        game.ask_for_selection(candidates, "DESTROY_CREATURE", count, initiator)

    @staticmethod
    def _resolve_destroy_all(game, victim, cond_type, threshold):
        targets = EffectManager._get_valid_targets(victim.board, cond_type, threshold)
        for target in list(targets):
            game._destroy_card(target, victim)

    @staticmethod
    def _resolve_steal_hand(game, thief, victim, count):
        if not victim.hand: return
        for _ in range(count):
            if victim.hand:
                card = random.choice(victim.hand)
                victim.hand.remove(card)
                thief.hand.append(card)
                game.refill_hand(victim)

    @staticmethod
    def _resolve_reclaim_discard(game, owner, count):
        if not owner.discard: return
        game.ask_for_selection(owner.discard, "RECLAIM_DISCARD", count, owner)

    @staticmethod
    def _resolve_play_my_discard(game, owner, count):
        if not owner.discard: return
        game.ask_for_selection(owner.discard, "PLAY_FROM_MY_DISCARD", count, owner)

    @staticmethod
    def _resolve_reclaim_all_discard(owner):
        if not owner.discard: return
        for card in owner.discard:
            card.reset()
            owner.hand.append(card)
        owner.discard = []

    @staticmethod
    def _resolve_discard_random(game, victim, count):
        if not victim.hand: return
        for _ in range(count):
            if victim.hand:
                card = random.choice(victim.hand)
                victim.hand.remove(card)
                victim.discard.append(card)
                game.refill_hand(victim)

    @staticmethod
    def _resolve_play_opp_discard(game, player, opponent, count):
        if not opponent.discard: return
        game.ask_for_selection(opponent.discard, "PLAY_FROM_OPP_DISCARD", count, player)

    @staticmethod
    def _resolve_sacrifice(game, victim, count):
        if not victim.board: return
        for _ in range(count):
            target = random.choice(victim.board) # TODO: rendre interactif (ask_for_selection par victim)
            game._destroy_card(target, victim)
