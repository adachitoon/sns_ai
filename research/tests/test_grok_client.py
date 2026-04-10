import io
import json
from unittest.mock import MagicMock, patch
import pytest
from research.grok_client import GrokClient


def _make_urlopen_mock(tools_in_payload=None):
    """urllib.request.urlopen をモックし、payload を記録するコンテキストマネージャを返す。"""
    captured = {}

    class FakeResponse:
        def read(self):
            return json.dumps({
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "mocked result"}],
                    }
                ]
            }).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    def fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode())
        return FakeResponse()

    captured["fake_urlopen"] = fake_urlopen
    return captured


def test_grok_client_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GROK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROK_API_KEY"):
        GrokClient()


def test_grok_client_chat_returns_content(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    with patch("research.grok_client.OpenAI") as mock_openai:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "test response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = GrokClient()
        result = client.chat([{"role": "user", "content": "hello"}])
        assert result == "test response"


def test_grok_client_chat_with_x_search_passes_correct_params(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    captured = _make_urlopen_mock()
    with patch("research.grok_client.OpenAI"), \
         patch("urllib.request.urlopen", captured["fake_urlopen"]):
        client = GrokClient()
        client.chat(
            [{"role": "user", "content": "search"}],
            search_mode="on",
            search_sources=[{"type": "x"}],
        )

        assert captured["payload"]["tools"] == [{"type": "x_search"}]


def test_grok_client_chat_without_search_has_no_tools(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    with patch("research.grok_client.OpenAI") as mock_openai:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "hello"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = GrokClient()
        client.chat([{"role": "user", "content": "hello"}], search_mode="off")

        call_kwargs = mock_openai.return_value.chat.completions.create.call_args[1]
        assert "tools" not in call_kwargs


def test_grok_client_chat_with_search_defaults_to_web_source(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    captured = _make_urlopen_mock()
    with patch("research.grok_client.OpenAI"), \
         patch("urllib.request.urlopen", captured["fake_urlopen"]):
        client = GrokClient()
        client.chat([{"role": "user", "content": "search"}], search_mode="on")

        assert captured["payload"]["tools"] == [{"type": "web_search"}]
