import json
from mindbug_engine.core.config import ConfigurationService
from mindbug_engine.core.consts import Difficulty


def test_load_nonexistent_file_uses_defaults(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(ConfigurationService, "FILE_PATH", str(path))

    cfg = ConfigurationService()

    assert cfg.ai_difficulty == Difficulty.MEDIUM
    assert cfg.debug_mode is False
    assert cfg.game_mode == "HOTSEAT"
    assert cfg.active_sets == ["FIRST_CONTACT"]
    assert cfg.resolution == (1280, 720)
    assert cfg.fullscreen is False


def test_load_valid_file_overrides(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(ConfigurationService, "FILE_PATH", str(path))

    data = {
        "debug_mode": True,
        "game_mode": "MULTI",
        "fullscreen": True,
        "resolution": [1920, 1080],
        "ai_difficulty": "HARD",
        "active_sets": ["S1", "S2"],
    }
    path.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigurationService()

    assert cfg.debug_mode is True
    assert cfg.game_mode == "MULTI"
    assert cfg.fullscreen is True
    assert cfg.resolution == (1920, 1080)
    assert cfg.ai_difficulty == Difficulty.HARD
    assert cfg.active_sets == ["S1", "S2"]


def test_load_invalid_ai_defaults_to_medium(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(ConfigurationService, "FILE_PATH", str(path))

    data = {"ai_difficulty": "IMPOSSIBLE"}
    path.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigurationService()
    assert cfg.ai_difficulty == Difficulty.MEDIUM


def test_empty_active_sets_does_not_overwrite_default(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(ConfigurationService, "FILE_PATH", str(path))

    data = {"active_sets": []}
    path.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigurationService()
    assert cfg.active_sets == ["FIRST_CONTACT"]


def test_save_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(ConfigurationService, "FILE_PATH", str(path))

    cfg = ConfigurationService()
    cfg.debug_mode = True
    cfg.game_mode = "FOO"
    cfg.ai_difficulty = Difficulty.HARD
    cfg.active_sets = ["A"]
    cfg.resolution = (800, 600)
    cfg.fullscreen = True

    cfg.save()

    content = json.loads(path.read_text(encoding="utf-8"))
    assert content["debug_mode"] is True
    assert content["game_mode"] == "FOO"
    assert content["ai_difficulty"] == "HARD"
    assert content["active_sets"] == ["A"]
    assert content["resolution"] == [800, 600]
    assert content["fullscreen"] is True
