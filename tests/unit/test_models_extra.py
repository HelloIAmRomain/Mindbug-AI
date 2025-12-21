from mindbug_engine.core.models import SelectionRequest, CardEffect, Card, Player


def test_selectionrequest_repr_uses_selector_name():
    selector = type("S", (), {"name": "Chooser"})()
    req = SelectionRequest(
        candidates=[1, 2], count=1, reason="pick", selector=selector)
    s = repr(req)
    assert "Chooser" in s
    assert "pick" in s


def test_cardeffect_copy_and_repr_is_independent():
    e = CardEffect("MODIFY", target={"k": 1}, condition={
                   "c": True}, params={"p": 5})
    r = repr(e)
    assert "MODIFY" in r
    assert "T:" in r

    c = e.copy()
    assert c.type == e.type
    # modify original's target shouldn't change copy
    e.target["k"] = 99
    assert c.target["k"] == 1


def test_card_from_dict_defaults_and_effects_and_image():
    data = {
        "id": "card1",
        "name": "Card One",
        "power": 4,
        "effects": [{"type": "MOVE", "target": {"zone": "board"}}],
    }
    c = Card.from_dict(data)
    assert c.id == "card1"
    assert c.name == "Card One"
    assert c.base_power == 4
    assert len(c.effects) == 1
    assert c.image_path.endswith("card1.jpg")


def test_card_reset_refresh_and_copy_and_repr():
    c = Card(id="c2", name="Toughie", power=5, keywords=["TOUGH", "FRENZY"])
    c.is_damaged = True
    c.power = 2
    # repr marks damaged
    assert "*" in repr(c)

    # refresh_state should restore base_power and remove TOUGH when damaged
    c.refresh_state()
    assert c.power == c.base_power
    assert "TOUGH" not in c.keywords

    # reset should clear damage and set keywords to base
    c.is_damaged = True
    c.reset()
    assert c.is_damaged is False
    assert c.power == c.base_power

    # copy should produce an independent object
    c2 = c.copy()
    assert c2 is not c
    assert c2.id == c.id
    c2.name = "Other"
    assert c.name == "Toughie"


def test_player_copy_and_repr_and_collections_are_copied():
    p = Player("Alice")
    p.hp = 7
    p.mindbugs = 3
    card = Card(id="x", name="X", power=1)
    p.deck.append(card)
    p.hand.append(card)
    p.board.append(card)
    p.discard.append(card)

    s = repr(p)
    assert "Alice" in s

    p2 = p.copy()
    assert p2 is not p
    assert p2.name == p.name
    # collections should be new lists with new card copies
    assert p2.deck is not p.deck
    assert len(p2.deck) == len(p.deck)
    assert p2.deck[0].id == p.deck[0].id
    # modifying copy's card shouldn't change original
    p2.deck[0].name = "Changed"
    assert p.deck[0].name == "X"
