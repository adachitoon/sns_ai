from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest

from research.research import run_research


MOCK_X_POSTS = [{"author": "test", "content": "AI", "likes": 100, "retweets": 50, "bookmarks": 30, "url": "https://x.com/1", "is_english": False, "translation": "", "jp_relevance": ""}]
MOCK_HN = [{"title": "OpenAI news", "url": "https://openai.com", "points": 200, "comments": 50}]
MOCK_REDDIT = [{"title": "Claude beats all", "url": "https://reddit.com/1", "upvotes": 300, "comments": 80, "subreddit": "ClaudeAI"}]
MOCK_PH = [{"name": "ToolX", "description": "AI tool", "upvotes": 200, "url": "https://ph.com/toolx"}]
MOCK_GT = {"rising_keywords": ["Claude"], "related_rising": ["AIエージェント"]}
MOCK_REPORT = "■ 今日の一言サマリー\nAIが熱い。"


def test_run_research_calls_all_fetchers_and_saves_file(monkeypatch, tmp_path):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")

    with patch("research.research.GrokClient") as mock_gc_class, \
         patch("research.research.fetch_x_posts", return_value=MOCK_X_POSTS) as mock_x, \
         patch("research.research.fetch_hn_stories", return_value=MOCK_HN) as mock_hn, \
         patch("research.research.fetch_reddit_posts", return_value=MOCK_REDDIT) as mock_reddit, \
         patch("research.research.fetch_product_hunt", return_value=MOCK_PH) as mock_ph, \
         patch("research.research.fetch_google_trends", return_value=MOCK_GT) as mock_gt, \
         patch("research.research.generate_report", return_value=MOCK_REPORT) as mock_gen, \
         patch("research.research.check_urls", return_value=MOCK_REPORT) as mock_check, \
         patch("research.research.PROJECT_ROOT", tmp_path):

        result = run_research()

    mock_x.assert_called_once()
    mock_hn.assert_called_once()
    mock_reddit.assert_called_once()
    mock_ph.assert_called_once()
    mock_gt.assert_called_once()
    mock_gen.assert_called_once()
    mock_check.assert_called_once_with(MOCK_REPORT)

    from datetime import datetime
    date = datetime.now().strftime("%Y.%m.%d")
    output = tmp_path / "01_リサーチ" / f"{date}.md"
    assert output.exists()
    assert output.read_text(encoding="utf-8") == MOCK_REPORT


def test_run_research_handles_fetcher_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")

    with patch("research.research.GrokClient"), \
         patch("research.research.fetch_x_posts", side_effect=Exception("API down")), \
         patch("research.research.fetch_hn_stories", return_value=MOCK_HN), \
         patch("research.research.fetch_reddit_posts", return_value=MOCK_REDDIT), \
         patch("research.research.fetch_product_hunt", return_value=MOCK_PH), \
         patch("research.research.fetch_google_trends", return_value=MOCK_GT), \
         patch("research.research.generate_report", return_value=MOCK_REPORT), \
         patch("research.research.check_urls", return_value=MOCK_REPORT), \
         patch("research.research.PROJECT_ROOT", tmp_path):

        result = run_research()

    from datetime import datetime
    date = datetime.now().strftime("%Y.%m.%d")
    output = tmp_path / "01_リサーチ" / f"{date}.md"
    assert output.exists()


def test_run_research_uses_correct_fallback_for_google_trends(monkeypatch, tmp_path):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    captured_data = {}

    def capture_generate_report(data, grok_client=None):
        captured_data.update(data)
        return MOCK_REPORT

    with patch("research.research.GrokClient"), \
         patch("research.research.fetch_x_posts", return_value=MOCK_X_POSTS), \
         patch("research.research.fetch_hn_stories", return_value=MOCK_HN), \
         patch("research.research.fetch_reddit_posts", return_value=MOCK_REDDIT), \
         patch("research.research.fetch_product_hunt", return_value=MOCK_PH), \
         patch("research.research.fetch_google_trends", side_effect=Exception("timeout")), \
         patch("research.research.generate_report", side_effect=capture_generate_report), \
         patch("research.research.check_urls", return_value=MOCK_REPORT), \
         patch("research.research.PROJECT_ROOT", tmp_path):

        run_research()

    assert isinstance(captured_data.get("google_trends"), dict)
    assert "rising_keywords" in captured_data["google_trends"]
