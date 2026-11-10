import pytest

import ask
import llm


def test_chat_shapes_the_request_and_parses_usage(fake_server, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    r = llm.chat("some/model", [{"role": "user", "content": "ping"}], base_url=fake_server.url + "/v1")
    assert r["text"] == "pong" and r["usage"]["cost"] == 0.0001
    seen = fake_server.seen[0]
    assert seen["path"] == "/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key-not-real"
    assert seen["body"]["model"] == "some/model" and seen["body"]["temperature"] == 0


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(llm.LLMError, match="OPENROUTER_API_KEY"):
        llm.chat("m", [], base_url="http://127.0.0.1:1")


def test_ask_two_models_prints_both(fake_server, monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    rc = ask.main(["hi", "--model", "a/one", "--model", "b/two", "--base-url", fake_server.url + "/v1"])
    out = capsys.readouterr().out
    assert rc == 0 and "[a/one]" in out and "[b/two]" in out and "cost=0.0001" in out


def test_unreachable_gateway_is_reported(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    with pytest.raises(llm.LLMError, match="cannot reach"):
        llm.chat("m", [], base_url="http://127.0.0.1:9", timeout=2)
