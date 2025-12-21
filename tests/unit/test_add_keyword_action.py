from types import SimpleNamespace
from mindbug_engine.managers.effects.actions.add_keyword import AddKeywordAction
from mindbug_engine.core.consts import Keyword


def test_execute_ignores_targets_without_keywords():
    action = AddKeywordAction()
    target = object()
    # Should not raise
    action.execute(target, {}, None, None, None)


def test_execute_adds_single_keyword_string():
    action = AddKeywordAction()
    target = SimpleNamespace(name="C", keywords=[])
    action.execute(target, {"keywords": "TOUGH"}, None, None, None)
    assert Keyword.TOUGH in target.keywords


def test_execute_adds_list_and_does_not_duplicate():
    action = AddKeywordAction()
    target = SimpleNamespace(name="C", keywords=[Keyword.TOUGH])
    action.execute(target, {"keywords": ["TOUGH", "FRENZY"]}, None, None, None)
    # TOUGH should not be duplicated
    tough_count = sum(1 for k in target.keywords if k == Keyword.TOUGH)
    assert tough_count == 1
    assert Keyword.FRENZY in target.keywords


def test_execute_invalid_keyword_logs_error(monkeypatch):
    action = AddKeywordAction()
    target = SimpleNamespace(name="C", keywords=[])
    logs = []

    def fake_log(msg):
        logs.append(msg)

    # patch the logger used in the exception block
    monkeypatch.setattr("mindbug_engine.utils.logger.log_error", fake_log)

    action.execute(target, {"keywords": ["NOT_A_KEY"]}, None, None, None)
    assert any("Mot-clé inconnu" in str(m) or "unknown" in str(m).lower()
               for m in logs)
