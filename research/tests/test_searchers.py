from unittest.mock import patch, MagicMock
import pytest
from research.searchers import fetch_hn_stories, fetch_reddit_posts, fetch_x_posts
from research.grok_client import GrokClient


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


def _make_reddit_response(posts: list[dict]) -> dict:
    return {
        "data": {
            "children": [{"data": p} for p in posts]
        }
    }


def test_fetch_reddit_posts_returns_filtered_posts():
    posts = [
        {"title": "Claude 3.7 vs GPT-4o benchmark", "ups": 350, "num_comments": 80,
         "permalink": "/r/LocalLLaMA/comments/abc/"},
        {"title": "Daily discussion thread", "ups": 50, "num_comments": 20,
         "permalink": "/r/ChatGPT/comments/def/"},
        {"title": "New tool for local LLM", "ups": 100, "num_comments": 60,
         "permalink": "/r/ClaudeAI/comments/ghi/"},
    ]

    def mock_get(url, headers=None, timeout=10):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _make_reddit_response(posts)
        return resp

    with patch("research.searchers.requests.get", side_effect=mock_get):
        result = fetch_reddit_posts()

    titles = [p["title"] for p in result]
    assert "Claude 3.7 vs GPT-4o benchmark" in titles
    assert "New tool for local LLM" in titles
    assert "Daily discussion thread" not in titles


def test_fetch_reddit_posts_handles_http_error():
    with patch("research.searchers.requests.get", side_effect=Exception("503")):
        result = fetch_reddit_posts()
    assert result == []


def test_fetch_reddit_posts_returns_at_most_5():
    posts = [
        {"title": f"Post {i}", "ups": 300, "num_comments": 100,
         "permalink": f"/r/LocalLLaMA/comments/{i}/"}
        for i in range(20)
    ]

    def mock_get(url, headers=None, timeout=10):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _make_reddit_response(posts)
        return resp

    with patch("research.searchers.requests.get", side_effect=mock_get):
        result = fetch_reddit_posts()

    assert len(result) <= 5


def test_fetch_x_posts_calls_grok_with_live_x_search(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = '[{"author": "test", "content": "AI news", "likes": 200, "retweets": 60, "bookmarks": 40, "url": "https://x.com/test/1", "is_english": false, "translation": "", "jp_relevance": ""}]'

    result = fetch_x_posts(grok_client=mock_client)

    call_kwargs = mock_client.chat.call_args[1]
    assert call_kwargs["search_mode"] == "on"
    assert call_kwargs["search_sources"] == [{"type": "x"}]
    assert len(result) == 1
    assert result[0]["author"] == "test"


def test_fetch_x_posts_handles_grok_error(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.side_effect = Exception("API error")

    result = fetch_x_posts(grok_client=mock_client)
    assert result == []


def test_fetch_x_posts_handles_invalid_json(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = "申し訳ありませんが、取得できませんでした。"

    result = fetch_x_posts(grok_client=mock_client)
    assert result == []


def test_fetch_x_posts_handles_markdown_wrapped_json(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = '```json\n[{"author": "test", "content": "news", "likes": 150, "retweets": 55, "bookmarks": 35, "url": "https://x.com/test/2", "is_english": false, "translation": "", "jp_relevance": ""}]\n```'

    result = fetch_x_posts(grok_client=mock_client)
    assert len(result) == 1
    assert result[0]["author"] == "test"
