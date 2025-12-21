import json
from mindbug_engine.infrastructure import card_loader as cl


def test_load_missing_file_logs_and_returns_empty(tmp_path, monkeypatch):
    path = tmp_path / "nope.json"

    logged = {}

    def fake_log(msg):
        logged['msg'] = msg

    monkeypatch.setattr(cl, "log_error", fake_log)

    res = cl.CardLoader.load_from_json(str(path))
    assert res == []
    assert "Fichier introuvable" in logged.get('msg', "")


def test_load_valid_card_copies_and_calls_from_dict(tmp_path, monkeypatch):
    path = tmp_path / "cards.json"
    data = [{"name": "C1", "copies": 2}]
    path.write_text(json.dumps(data), encoding="utf-8")

    created = []

    def fake_from_dict(item):
        created.append(item.get("name"))
        return {"name": item.get("name")}

    monkeypatch.setattr(cl.Card, "from_dict", fake_from_dict)

    res = cl.CardLoader.load_from_json(str(path))
    assert len(res) == 2
    assert all(r["name"] == "C1" for r in res)


def test_load_invalid_copies_logs_and_skips(tmp_path, monkeypatch):
    path = tmp_path / "cards.json"
    data = [{"name": "BadCopies", "copies": "NaN"}]
    path.write_text(json.dumps(data), encoding="utf-8")

    logs = []
    monkeypatch.setattr(cl, "log_error", lambda m: logs.append(m))

    called = {"from_called": False}

    def fake_from_dict(item):
        called["from_called"] = True
        return {}

    monkeypatch.setattr(cl.Card, "from_dict", fake_from_dict)

    res = cl.CardLoader.load_from_json(str(path))
    assert res == []
    assert any("copies' invalide" in m or "copies invalide" in m for m in logs)
    assert called["from_called"] is False


def test_load_card_instantiation_exception_logs_and_skips(tmp_path, monkeypatch):
    path = tmp_path / "cards.json"
    data = [{"name": "Explode", "copies": 1}]
    path.write_text(json.dumps(data), encoding="utf-8")

    logs = []
    monkeypatch.setattr(cl, "log_error", lambda m: logs.append(m))

    def raise_exc(item):
        raise RuntimeError("boom")

    monkeypatch.setattr(cl.Card, "from_dict", raise_exc)

    res = cl.CardLoader.load_from_json(str(path))
    assert res == []
    assert any("Erreur instanciation carte" in m for m in logs)


def test_default_copies_is_one_when_missing(tmp_path, monkeypatch):
    path = tmp_path / "cards.json"
    data = [{"name": "Solo"}]
    path.write_text(json.dumps(data), encoding="utf-8")

    created = []

    def fake_from_dict(item):
        created.append(item)
        return item

    monkeypatch.setattr(cl.Card, "from_dict", fake_from_dict)

    res = cl.CardLoader.load_from_json(str(path))
    assert len(res) == 1
