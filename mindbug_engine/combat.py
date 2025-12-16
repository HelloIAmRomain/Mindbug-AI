from typing import Optional
from .models import Card, Player
from .rules import Keyword, CombatUtils


class CombatManager:
    """Gère les règles de combat, les calculs de puissance et la mort des créatures."""

    def __init__(self, game):
        self.game = game

    def calculate_real_power(self, card: Card, active_player: Player, opponent: Player) -> int:
        """Calcule la puissance dynamique d'une carte (bonus, passifs)."""
        current = card.power

        # Détermine le propriétaire de la carte
        card_owner = self.game.player1 if card in self.game.player1.board else self.game.player2
        is_my_turn = (card_owner == active_player)

        # 1. Ally Bonus (ex: +1 par autre fourmi)
        for ally in card_owner.board:
            if ally == card: continue
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES":
                current += ally.ability.value

        # 2. Turn Bonus (ex: +2 si c'est mon tour)
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_IF_MY_TURN":
            if is_my_turn: current += card.ability.value

        # 3. Ally Turn Bonus (ex: Kangourou booste les autres si c'est son tour)
        for ally in card_owner.board:
            if ally == card: continue
            if ally.ability and ally.trigger == "PASSIVE" and ally.ability.code == "BOOST_ALLIES_IF_MY_TURN":
                if is_my_turn: current += ally.ability.value

        # 4. Yeti (Boost si seul)
        if card.ability and card.trigger == "PASSIVE" and card.ability.code == "BOOST_AND_FRENZY_IF_ALONE":
            if len(card_owner.board) == 1: current += card.ability.value

        # 5. Enemy Debuff (ex: -1 aux ennemis)
        # On détermine le plateau adverse par rapport au propriétaire de la carte
        opp_board = self.game.player2.board if card_owner == self.game.player1 else self.game.player1.board

        for enemy in opp_board:
            if enemy.ability and enemy.trigger == "PASSIVE" and enemy.ability.code == "DEBUFF_ENEMIES":
                current += enemy.ability.value

        return max(0, current)

    def resolve_fight(self, attacker: Card, blocker: Optional[Card]):
        """Résout le combat et applique les dégâts/morts."""
        attacker_owner = self.game.player1 if attacker in self.game.player1.board else self.game.player2
        defender_owner = self.game.player2 if attacker_owner == self.game.player1 else self.game.player1

        # Calcul des puissances
        att_power = self.calculate_real_power(attacker, self.game.active_player, self.game.opponent)

        if blocker is None:
            damage_applied = False

            # Vérification Trigger spécifique (ex: Turboustique)
            # On cherche si la carte a une capacité qui se déclenche quand non bloquée
            if attacker.ability and attacker.trigger == "ON_ATTACK_UNBLOCKED":
                # On délègue à l'EffectManager
                self.game.effect_manager.apply_effect(self.game, attacker, attacker_owner, defender_owner)
                damage_applied = True

            # Sinon, dégât standard (-1 PV)
            if not damage_applied:
                self.game.log(f"> No block ! {defender_owner.name} loses 1 HP.")
                defender_owner.hp -= 1
            return False, False  # (Attacker Dead?, Blocker Dead?)

        blk_power = self.calculate_real_power(blocker, self.game.opponent, self.game.active_player)
        self.game.log(f"> Combat : {attacker.name} ({att_power}) vs {blocker.name} ({blk_power})")

        # Simulation règles de base (Power)
        # On utilise CombatUtils pour comparer les forces
        att_dead, blk_dead = CombatUtils.simulate_combat(attacker, blocker, override_att_power=att_power,
                                                         override_blk_power=blk_power)

        # Mots-clés Poison (Tue toujours si l'adversaire n'est pas déjà mort par force)
        if Keyword.POISON.value in attacker.keywords: blk_dead = True
        if Keyword.POISON.value in blocker.keywords: att_dead = True

        # Application des morts
        if att_dead: self.apply_lethal_damage(attacker, attacker_owner)
        if blk_dead: self.apply_lethal_damage(blocker, defender_owner)

        return att_dead, blk_dead

    def apply_lethal_damage(self, card: Card, owner: Player):
        """Gère TOUGH (Tenace/Bouclier) ou détruit la carte."""
        if Keyword.TOUGH.value in card.keywords and not card.is_damaged:
            self.game.log(f"> {card.name} uses TOUGH shield ! It survives but is damaged.")
            card.is_damaged = True
        else:
            self.game.log(f"> {card.name} is destroyed.")
            self.destroy_card(card, owner)

    def destroy_card(self, card: Card, owner: Player):
        """Retire du plateau, met au cimetière, déclenche effets de mort."""
        if card in owner.board:
            owner.board.remove(card)
            owner.discard.append(card)
            card.reset()  # Reset stats (dégâts, bonus temporaires)

            # Déclenchement effet ON_DEATH (ex: Requin)
            if card.trigger == "ON_DEATH":
                opponent = self.game.player2 if owner == self.game.player1 else self.game.player1
                self.game.effect_manager.apply_effect(self.game, card, owner, opponent)