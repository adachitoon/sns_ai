from unittest.mock import patch, MagicMock
import pytest
import requests as req
from research.formatter import check_urls, generate_report
from research.grok_client import GrokClient


def test_check_urls_keeps_200_url():
    report = "詳細はこちら https://example.com/article を確認してください"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "⚠️" not in result
    assert "https://example.com/article" in result


def test_check_urls_marks_404_url():
    report = "詳細はこちら https://example.com/broken を確認してください"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 404
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "https://example.com/broken ⚠️ URL要確認" in result


def test_check_urls_marks_timeout_url():
    report = "詳細はこちら https://example.com/slow を確認してください"

    with patch("research.formatter.requests.head", side_effect=req.exceptions.Timeout):
        result = check_urls(report)

    assert "https://example.com/slow ⚠️ URL要確認" in result


def test_check_urls_handles_multiple_urls():
    report = "OK: https://good.com/page NG: https://bad.com/page"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 200 if "good" in url else 404
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "https://good.com/page ⚠️ URL要確認" not in result
    assert "https://good.com/page" in result
    assert "https://bad.com/page ⚠️ URL要確認" in result


SAMPLE_DATA = {
    "date": "2026.04.09",
    "x_posts": [{"author": "テストユーザー", "content": "AI news", "likes": 200,
                  "retweets": 60, "bookmarks": 40, "url": "https://x.com/test/1",
                  "is_english": False, "translation": "", "jp_relevance": ""}],
    "hn_stories": [{"title": "OpenAI releases GPT-5", "url": "https://openai.com",
                     "points": 500, "comments": 200}],
    "reddit_posts": [{"title": "Claude is amazing", "url": "https://reddit.com/r/ClaudeAI/1",
                       "upvotes": 400, "comments": 100, "subreddit": "ClaudeAI"}],
    "product_hunt": [{"name": "AI Tool X", "description": "Best AI tool",
                       "upvotes": 300, "url": "https://producthunt.com/posts/aitoolx"}],
    "google_trends": {"rising_keywords": ["Claude"], "related_rising": ["AIエージェント"]},
}


def test_generate_report_calls_grok_with_all_data(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = "■ 今日の一言サマリー\nテストレポート"

    result = generate_report(SAMPLE_DATA, grok_client=mock_client)

    assert mock_client.chat.called
    call_args = mock_client.chat.call_args
    prompt = call_args[0][0][0]["content"]
    assert "x_posts" in prompt
    assert "hn_stories" in prompt
    assert "reddit_posts" in prompt
    assert "product_hunt" in prompt
    assert "google_trends" in prompt
    assert "提供されたデータのみを使用" in prompt


def test_generate_report_returns_grok_response(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    expected = "■ 今日の一言サマリー\n今日はAIが盛り上がっています。"
    mock_client.chat.return_value = expected

    result = generate_report(SAMPLE_DATA, grok_client=mock_client)
    assert result == expected
