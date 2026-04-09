from unittest.mock import patch, MagicMock
import pytest
from research.searchers import fetch_hn_stories


def _make_hn_story(story_id, title, score, descendants, url="https://example.com"):
    return {
        "id": story_id,
        "title": title,
        "score": score,
        "descendants": descendants,
        "url": url,
    }


def test_fetch_hn_stories_returns_ai_articles():
    top_ids = list(range(1, 6))
    stories = [
        _make_hn_story(1, "OpenAI releases new LLM model", 150, 45),
        _make_hn_story(2, "Show HN: My weekend project", 50, 10),
        _make_hn_story(3, "Claude AI beats benchmarks", 200, 80),
        _make_hn_story(4, "Ask HN: Best coffee shops", 20, 60),
        _make_hn_story(5, "LLM fine-tuning guide", 110, 35),
    ]

    def mock_get(url, timeout=10):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "topstories" in url:
            resp.json.return_value = top_ids
        else:
            story_id = int(url.split("/")[-1].replace(".json", ""))
            resp.json.return_value = stories[story_id - 1]
        return resp

    with patch("research.searchers.requests.get", side_effect=mock_get):
        result = fetch_hn_stories()

    titles = [s["title"] for s in result]
    assert "OpenAI releases new LLM model" in titles
    assert "Claude AI beats benchmarks" in titles
    assert "LLM fine-tuning guide" in titles
    assert "Show HN: My weekend project" not in titles
    assert "Ask HN: Best coffee shops" not in titles


def test_fetch_hn_stories_handles_http_error():
    with patch("research.searchers.requests.get", side_effect=Exception("timeout")):
        result = fetch_hn_stories()
    assert result == []


def test_fetch_hn_stories_returns_at_most_5():
    top_ids = list(range(1, 51))
    ai_story = _make_hn_story(1, "AI and LLM news", 500, 200)

    def mock_get(url, timeout=10):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "topstories" in url:
            resp.json.return_value = top_ids
        else:
            resp.json.return_value = ai_story
        return resp

    with patch("research.searchers.requests.get", side_effect=mock_get):
        result = fetch_hn_stories()

    assert len(result) <= 5
