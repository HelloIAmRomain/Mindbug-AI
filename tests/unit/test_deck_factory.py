import random
from types import SimpleNamespace

from mindbug_engine.infrastructure.deck_factory import DeckFactory
from mindbug_engine.core.models import Card
from mindbug_engine.infrastructure import card_loader


def make_card(i, set_name="SET"):
    return Card(id=f"c{i}", name=f"Card{i}", power=1, set_id=set_name)


def test_create_deck_not_enough_cards(monkeypatch, tmp_path):
    # Monkeypatch CardLoader.load_from_json to return few cards
    monkeypatch.setattr(card_loader.CardLoader, "load_from_json", lambda p: [
                        make_card(i) for i in range(5)])

    df = DeckFactory(str(tmp_path / "dummy.json"))
    game_deck, candidates, used_sets = df.create_deck()

    assert game_deck == candidates
    assert len(candidates) == 5
    assert used_sets == ['SET']


def test_create_deck_with_active_sets_and_sampling(monkeypatch, tmp_path):
    # Create 25 cards across two sets
    cards = [make_card(i, set_name="Alpha") for i in range(
        25)] + [make_card(100 + i, set_name="Beta") for i in range(5)]
    monkeypatch.setattr(card_loader.CardLoader,
                        "load_from_json", lambda p: cards)

    df = DeckFactory(str(tmp_path / "dummy.json"))

    # If no active_sets provided, first sorted key should be 'ALPHA'
    game_deck, candidates, used_sets = df.create_deck()
    assert len(candidates) >= 25

    # On attend 22 cartes (20 jeu + 2 initiative)
    assert len(game_deck) == 22
    assert "ALPHA" in used_sets

    # Providing explicit active_sets filters to that set
    game_deck2, candidates2, used_sets2 = df.create_deck(active_sets=["Beta"])
    assert all(c.set == "Beta" for c in candidates2)


def test_create_deck_with_active_card_ids_overrides(monkeypatch, tmp_path):
    cards = [make_card(i, set_name="Alpha") for i in range(15)]
    monkeypatch.setattr(card_loader.CardLoader,
                        "load_from_json", lambda p: cards)
    df = DeckFactory(str(tmp_path / "dummy.json"))

    # Choose a subset by ids
    chosen_ids = [cards[0].id, cards[2].id]
    game_deck, candidates, used_sets = df.create_deck(
        active_card_ids=chosen_ids)
    assert set(c.id for c in candidates) == set(chosen_ids)
