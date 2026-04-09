import os
from unittest.mock import MagicMock, patch
import pytest
from research.grok_client import GrokClient


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
    with patch("research.grok_client.OpenAI") as mock_openai:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "[]"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = GrokClient()
        client.chat(
            [{"role": "user", "content": "search"}],
            search_mode="on",
            search_sources=[{"type": "x"}],
        )

        call_kwargs = mock_openai.return_value.chat.completions.create.call_args[1]
        assert call_kwargs["extra_body"]["search_parameters"]["mode"] == "on"
        assert call_kwargs["extra_body"]["search_parameters"]["sources"] == [{"type": "x"}]


def test_grok_client_chat_without_search_has_no_extra_body(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    with patch("research.grok_client.OpenAI") as mock_openai:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "hello"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = GrokClient()
        client.chat([{"role": "user", "content": "hello"}], search_mode="off")

        call_kwargs = mock_openai.return_value.chat.completions.create.call_args[1]
        assert "extra_body" not in call_kwargs
