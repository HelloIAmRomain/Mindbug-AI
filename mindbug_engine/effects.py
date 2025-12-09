import random
from typing import TYPE_CHECKING
from .models import Card, Player

if TYPE_CHECKING:
    from .engine import MindbugGame

class EffectManager:
    """
    Catalogue des effets déclenchés par les cartes.
    """

    @staticmethod
    def apply_effect(game: 'MindbugGame', card: Card, owner: Player, opponent: Player):
        """
        Dispatche l'effet de la carte vers la bonne fonction.
        """
        if not card.ability:
            return

        code = card.ability.code
        val = card.ability.value
        condition = card.ability.condition
        
        print(f"✨ EFFET DÉCLENCHÉ : {code} (Val:{val}) pour {card.name}")

        # --- LISTE DES EFFETS ---
        if code == "HEAL":
            # Le moteur lit la "value" du JSON (ici 2) et l'ajoute aux PV actuels
            if card.ability.target == "SELF":
                owner.hp += val
                print(f"   -> {owner.name} est soigné de +{val} PV (Total: {owner.hp})")

        elif code == "DAMAGE":
            # "L'adversaire perd 1 PV"
            if card.ability.target == "OPP":
                opponent.hp -= val
                print(f"   -> {opponent.name} perd {val} PV (HP: {opponent.hp})")

        elif code == "STEAL_CREATURE":
            # "Volez une créature ennemie"
            EffectManager._effect_steal_creature(game, owner, opponent, val)

        elif code == "RECLAIM_DISCARD":
            # "Récupérez une carte de la défausse"
            EffectManager._effect_reclaim_discard(owner, val)
            
        elif code == "DISCARD_RANDOM":
            # "L'adversaire défausse au hasard"
            EffectManager._effect_discard_random(opponent, val)

        elif code == "DESTROY_CREATURE":
            # "Détruisez une créature ennemie"
            EffectManager._effect_destroy_creature(game, opponent, condition, val)
            
        elif code == "BLOCK_BAN":
            # Effet passif ou temporaire, souvent géré par rules.py ou un flag
            # Pour l'instant, on log juste
            pass

        # ... Ajouter les autres codes ici au besoin

    # --- IMPLÉMENTATIONS SPÉCIFIQUES ---

    @staticmethod
    def _effect_steal_creature(game, owner: Player, opponent: Player, count: int):
        if not opponent.board:
            print("   -> Rien à voler !")
            return
        
        # Pour l'instant : Vol aléatoire (Dans le futur : Choix UI/IA)
        # TODO: Implémenter la sélection manuelle via game.ask_choice()
        for _ in range(count):
            if opponent.board:
                target = random.choice(opponent.board) # Simplification temporaire
                opponent.board.remove(target)
                owner.board.append(target)
                print(f"   -> {owner.name} vole {target.name} !")

    @staticmethod
    def _effect_reclaim_discard(owner: Player, count: int):
        if not owner.discard:
            print("   -> Défausse vide.")
            return
            
        for _ in range(count):
            if owner.discard:
                # Récupère la dernière carte (LIFO) ou random ? Souvent choix.
                # Simplification : Dernière carte
                card = owner.discard.pop()
                owner.hand.append(card)
                card.reset() # Enlève les dégâts
                print(f"   -> {owner.name} récupère {card.name} de la défausse.")

    @staticmethod
    def _effect_discard_random(victim: Player, count: int):
        if not victim.hand:
            return
            
        for _ in range(count):
            if victim.hand:
                card = list(victim.hand)[random.randrange(len(victim.hand))] # Random securisé
                victim.hand.remove(card)
                victim.discard.append(card)
                print(f"   -> {victim.name} défausse {card.name} (Hasard).")

    @staticmethod
    def _effect_destroy_creature(game, victim: Player, condition: str, count: int):
        # Filtrage des cibles valides
        targets = victim.board
        if condition == "POWER_GE_6": # Tigrécureuil
            targets = [c for c in victim.board if c.power >= 6]
        
        if not targets:
            print("   -> Aucune cible valide pour la destruction.")
            return

        # Simplification : Destruction aléatoire parmi les valides
        # TODO: Choix utilisateur
        for _ in range(count):
            if targets:
                target = random.choice(targets)
                print(f"   -> {target.name} est détruit par effet !")
                # On utilise la méthode publique de l'engine si possible, ou on le fait à la main
                # Ici on le fait à la main pour éviter import circulaire complexe, 
                # mais idéalement game._destroy_card(target, victim)
                if target in victim.board:
                    victim.board.remove(target)
                    victim.discard.append(target)
                    target.reset()
