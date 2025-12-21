import pytest
from mindbug_engine.core.models import Card, Player
from mindbug_engine.core.state import GameState
from mindbug_ai.mcts.determinizer import Determinizer

# --- FIXTURES ---


@pytest.fixture
def determinizer_setup():
    """Prépare un état de jeu contrôlé pour tester le mélange."""
    # 1. Création des cartes (IDs simples pour le suivi)
    # P1 (IA/Observer) : Main connue
    h1 = [Card(f"p1_h_{i}", "H1", 1) for i in range(5)]

    # P2 (Adversaire) : Main cachée
    h2 = [Card(f"p2_h_{i}", "H2", 1) for i in range(5)]

    # Pioche : Cachée
    deck = [Card(f"deck_{i}", "D", 1) for i in range(10)]

    # Board : Public
    b1 = [Card("p1_b", "B1", 1)]
    b2 = [Card("p2_b", "B2", 1)]

    p1 = Player("IA")
    p1.hand = h1
    p1.board = b1

    p2 = Player("Humain")
    p2.hand = h2
    p2.board = b2

    state = GameState(deck, p1, p2)

    # On retourne tout ce qu'il faut pour vérifier
    return state, h1, h2, deck

# --- TESTS ---


def test_determinizer_preserves_visible_information(determinizer_setup):
    """Vérifie que ce que l'IA voit (sa main, les boards) NE BOUGE PAS."""
    state, original_h1, original_h2, original_deck = determinizer_setup

    det = Determinizer()

    # L'IA (Joueur 0) imagine un monde possible
    new_state = det.determinize(state, observer_idx=0)

    # 1. Ma main ne doit pas changer
    assert new_state.player1.hand == original_h1

    # 2. Les plateaux ne doivent pas changer
    assert new_state.player1.board == state.player1.board
    assert new_state.player2.board == state.player2.board


def test_determinizer_shuffles_hidden_information(determinizer_setup):
    """Vérifie que la main adverse et la pioche sont bien mélangées entre elles."""
    state, original_h1, original_h2, original_deck = determinizer_setup

    det = Determinizer()

    # On fait une déterminisation
    new_state = det.determinize(state, observer_idx=0)

    # 1. La taille des zones doit être préservée (Règle fondamentale)
    assert len(new_state.player2.hand) == 5
    assert len(new_state.deck) == 10

    # 2. Le contenu GLOBAL (Main P2 + Deck) doit être le même (pas de création/suppression)
    original_hidden_set = {c.id for c in original_h2 + original_deck}
    new_hidden_set = {c.id for c in new_state.player2.hand + new_state.deck}
    assert original_hidden_set == new_hidden_set

    # 3. La main adverse a-t-elle changé ? (Probabiliste mais quasi-certain)
    # Il est possible que des cartes du deck soient arrivées dans la main P2
    # ou que l'ordre ait changé.

    # On vérifie juste qu'on a pas EXACTEMENT la même liste d'objets dans le même ordre
    # (Note : Pour un test unitaire strict, on pourrait mocker random.shuffle,
    # mais ici on veut vérifier que la logique permet le changement).

    # Si le shuffle fonctionne, il est statistiquement impossible que
    # la main P2 soit identique ET le deck identique à l'original
    # (sauf coup de chance cosmique, ou bug).

    is_identical = (new_state.player2.hand == original_h2) and (
        new_state.deck == original_deck)
    assert not is_identical, "Le Determinizer n'a pas mélangé les cartes cachées !"


def test_determinizer_handles_empty_deck(determinizer_setup):
    """Vérifie que ça ne plante pas si la pioche est vide (Fin de partie)."""
    state, _, _, _ = determinizer_setup
    state.deck = []  # On vide la pioche

    det = Determinizer()
    new_state = det.determinize(state, observer_idx=0)

    assert len(new_state.deck) == 0
    # La main adverse doit juste être mélangée sur elle-même (ordre changé)
    assert len(new_state.player2.hand) == 5
