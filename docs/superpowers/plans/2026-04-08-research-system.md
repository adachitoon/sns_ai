# AIトレンドリサーチ自動化システム 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/research` コマンドで5ステップのAIトレンドリサーチを自動実行し、`01_リサーチ/YYYY.MM.DD.md` に保存する

**Architecture:** GrokClientがxAI APIのラッパー。searchers.pyが5ステップのデータ取得を担当（X→Grok live search、HN/Reddit→直接API、PH/GTrends→Grok web search）。formatter.pyがレポート生成とURL疎通確認を担当。research.pyがThreadPoolExecutorで並列実行して結果をファイル保存。

**Tech Stack:** Python 3.13、openai SDK（xAI API互換）、requests、python-dotenv、pytest

---

## ファイル構成

```
sns_ai/
├── research/
│   ├── __init__.py          # パッケージ化
│   ├── grok_client.py       # xAI API ラッパー
│   ├── searchers.py         # 全5ステップのデータ取得
│   ├── formatter.py         # レポート生成 + URL疎通確認
│   ├── research.py          # エントリーポイント・並列オーケストレーション
│   └── tests/
│       ├── __init__.py
│       ├── test_grok_client.py
│       ├── test_searchers.py
│       └── test_formatter.py
└── .claude/commands/
    └── research.md          # /research コマンド定義
```

---

## Task 1: プロジェクト構造のセットアップ

**Files:**
- Create: `research/__init__.py`
- Create: `research/tests/__init__.py`

- [ ] **Step 1: ディレクトリとファイルを作成**

```bash
mkdir -p /Users/kou/sns_ai/research/tests
touch /Users/kou/sns_ai/research/__init__.py
touch /Users/kou/sns_ai/research/tests/__init__.py
```

- [ ] **Step 2: 動作確認**

```bash
cd /Users/kou/sns_ai && python -c "import research; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd /Users/kou/sns_ai && git add research/__init__.py research/tests/__init__.py
git commit -m "chore: initialize research package structure"
```

---

## Task 2: GrokClient（xAI APIラッパー）

**Files:**
- Create: `research/grok_client.py`
- Create: `research/tests/test_grok_client.py`

- [ ] **Step 1: テストを書く**

`research/tests/test_grok_client.py` を以下の内容で作成:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_grok_client.py -v
```

Expected: `ImportError` または `ModuleNotFoundError: No module named 'research.grok_client'`

- [ ] **Step 3: GrokClient を実装**

`research/grok_client.py` を以下の内容で作成:

```python
import os
from openai import OpenAI


class GrokClient:
    def __init__(self):
        api_key = os.environ.get("GROK_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY が環境変数に設定されていません")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )

    def chat(
        self,
        messages: list[dict],
        search_mode: str = "off",
        search_sources: list[dict] | None = None,
    ) -> str:
        kwargs: dict = {
            "model": "grok-3",
            "messages": messages,
        }
        if search_mode != "off":
            sources = search_sources or [{"type": "web"}]
            kwargs["extra_body"] = {
                "search_parameters": {
                    "mode": search_mode,
                    "sources": sources,
                }
            }
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_grok_client.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/grok_client.py research/tests/test_grok_client.py
git commit -m "feat: add GrokClient wrapper for xAI API"
```

---

## Task 3: HackerNewsSearcher

**Files:**
- Create: `research/searchers.py`
- Create: `research/tests/test_searchers.py`

- [ ] **Step 1: テストを書く**

`research/tests/test_searchers.py` を以下の内容で作成:

```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py -v
```

Expected: `ImportError: cannot import name 'fetch_hn_stories'`

- [ ] **Step 3: HackerNews searcher を実装**

`research/searchers.py` を以下の内容で作成:

```python
import json
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from research.grok_client import GrokClient

HN_BASE = "https://hacker-news.firebaseio.com/v0"
AI_KEYWORDS = {
    "ai", "llm", "gpt", "claude", "gemini", "mistral", "llama",
    "openai", "anthropic", "machine learning", "neural", "transformer",
    "chatgpt", "copilot", "diffusion", "multimodal",
}
REDDIT_HEADERS = {"User-Agent": "sns-ai-research-bot/1.0"}


def fetch_hn_stories() -> list[dict]:
    try:
        resp = requests.get(f"{HN_BASE}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:50]
    except Exception:
        return []

    def _fetch_story(story_id: int) -> dict | None:
        for _ in range(3):
            try:
                r = requests.get(f"{HN_BASE}/item/{story_id}.json", timeout=5)
                r.raise_for_status()
                return r.json()
            except Exception:
                continue
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        stories = list(executor.map(_fetch_story, story_ids))

    results = []
    for story in stories:
        if not story:
            continue
        title = story.get("title", "").lower()
        score = story.get("score", 0)
        comments = story.get("descendants", 0)
        if (score >= 100 or comments >= 30) and any(kw in title for kw in AI_KEYWORDS):
            results.append({
                "title": story.get("title", ""),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={story['id']}"),
                "points": score,
                "comments": comments,
            })
    return results[:5]
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py -v
```

Expected: 3 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/searchers.py research/tests/test_searchers.py
git commit -m "feat: add HackerNews searcher with AI keyword filtering"
```

---

## Task 4: RedditSearcher

**Files:**
- Modify: `research/searchers.py`
- Modify: `research/tests/test_searchers.py`

- [ ] **Step 1: テストを追加**

`research/tests/test_searchers.py` の末尾に以下を追記:

```python
from research.searchers import fetch_reddit_posts


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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py::test_fetch_reddit_posts_returns_filtered_posts -v
```

Expected: `ImportError: cannot import name 'fetch_reddit_posts'`

- [ ] **Step 3: Reddit searcher を実装**

`research/searchers.py` に以下を追記（`fetch_hn_stories` の後）:

```python
REDDIT_SUBREDDITS = ["LocalLLaMA", "ChatGPT", "ClaudeAI"]


def fetch_reddit_posts() -> list[dict]:
    results = []
    for subreddit in REDDIT_SUBREDDITS:
        for attempt in range(3):
            try:
                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
                resp = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
                resp.raise_for_status()
                posts = resp.json()["data"]["children"]
                for post in posts:
                    data = post["data"]
                    upvotes = data.get("ups", 0)
                    comments = data.get("num_comments", 0)
                    if upvotes >= 200 or comments >= 50:
                        results.append({
                            "title": data.get("title", ""),
                            "url": f"https://www.reddit.com{data.get('permalink', '')}",
                            "upvotes": upvotes,
                            "comments": comments,
                            "subreddit": subreddit,
                        })
                break  # 成功したらリトライループを抜ける
            except Exception:
                continue  # 失敗したら次のattemptへ（3回失敗で次のsubredditへ）
    return results[:5]
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/searchers.py research/tests/test_searchers.py
git commit -m "feat: add Reddit searcher for LocalLLaMA, ChatGPT, ClaudeAI subreddits"
```

---

## Task 5: X Searcher（Grok live search）

**Files:**
- Modify: `research/searchers.py`
- Modify: `research/tests/test_searchers.py`

- [ ] **Step 1: テストを追加**

`research/tests/test_searchers.py` の末尾に以下を追記:

```python
from research.searchers import fetch_x_posts
from research.grok_client import GrokClient


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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py::test_fetch_x_posts_calls_grok_with_live_x_search -v
```

Expected: `ImportError: cannot import name 'fetch_x_posts'`

- [ ] **Step 3: X searcher を実装**

`research/searchers.py` の `fetch_reddit_posts` の後に以下を追記（`GrokClient` インポートは Task 3 で追加済み）:

```python
from research.grok_client import GrokClient

X_QUERIES = ["AI 新機能", "LLM リリース", "OpenAI", "Claude"]


def _parse_json_response(text: str) -> list | dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def fetch_x_posts(grok_client: GrokClient | None = None) -> list[dict]:
    if grok_client is None:
        grok_client = GrokClient()

    date = datetime.now().strftime("%Y年%m月%d日")
    prompt = f"""
{date}の直近24時間以内のXの投稿を以下のクエリで検索し、いいね100以上、RT50以上、ブックマーク30以上のいずれかを満たす投稿をTOP5件抽出してください。

検索クエリ: {', '.join(X_QUERIES)}

以下のJSON形式のみで返してください（説明文・コードブロック不要）:
[
  {{
    "author": "投稿者名",
    "content": "内容の要約（1〜2文）",
    "likes": 数値,
    "retweets": 数値,
    "bookmarks": 数値,
    "url": "投稿URL",
    "is_english": true/false,
    "translation": "英語の場合の日本語訳（日本語の場合は空文字）",
    "jp_relevance": "英語の場合の日本語圏での重要性（日本語の場合は空文字）"
  }}
]
"""
    try:
        response = grok_client.chat(
            messages=[{"role": "user", "content": prompt}],
            search_mode="on",
            search_sources=[{"type": "x"}],
        )
        return _parse_json_response(response)
    except Exception:
        return []
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py -v
```

Expected: 9 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/searchers.py research/tests/test_searchers.py
git commit -m "feat: add X searcher using Grok live search"
```

---

## Task 6: Product Hunt + Google Trends（Grok web search）

**Files:**
- Modify: `research/searchers.py`
- Modify: `research/tests/test_searchers.py`

- [ ] **Step 1: テストを追加**

`research/tests/test_searchers.py` の末尾に以下を追記:

```python
from research.searchers import fetch_product_hunt, fetch_google_trends


def test_fetch_product_hunt_calls_grok_with_web_search(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = '[{"name": "TestAI", "description": "AI tool", "upvotes": 300, "url": "https://producthunt.com/posts/testai"}]'

    result = fetch_product_hunt(grok_client=mock_client)

    call_kwargs = mock_client.chat.call_args[1]
    assert call_kwargs["search_mode"] == "on"
    assert call_kwargs["search_sources"] == [{"type": "web"}]
    assert len(result) == 1
    assert result[0]["name"] == "TestAI"


def test_fetch_product_hunt_handles_error(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.side_effect = Exception("API error")

    result = fetch_product_hunt(grok_client=mock_client)
    assert result == []


def test_fetch_google_trends_calls_grok_with_web_search(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.return_value = '{"rising_keywords": ["Claude", "ChatGPT"], "related_rising": ["AIエージェント"]}'

    result = fetch_google_trends(grok_client=mock_client)

    call_kwargs = mock_client.chat.call_args[1]
    assert call_kwargs["search_mode"] == "on"
    assert call_kwargs["search_sources"] == [{"type": "web"}]
    assert result["rising_keywords"] == ["Claude", "ChatGPT"]


def test_fetch_google_trends_handles_error(monkeypatch):
    monkeypatch.setenv("GROK_API_KEY", "xai-test")
    mock_client = MagicMock(spec=GrokClient)
    mock_client.chat.side_effect = Exception("API error")

    result = fetch_google_trends(grok_client=mock_client)
    assert result == {"rising_keywords": [], "related_rising": []}
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py::test_fetch_product_hunt_calls_grok_with_web_search -v
```

Expected: `ImportError: cannot import name 'fetch_product_hunt'`

- [ ] **Step 3: Product Hunt と Google Trends searcher を実装**

`research/searchers.py` の末尾に以下を追記:

```python
def fetch_product_hunt(grok_client: GrokClient | None = None) -> list[dict]:
    if grok_client is None:
        grok_client = GrokClient()

    date = datetime.now().strftime("%Y年%m月%d日")
    prompt = f"""
{date}のProduct Huntで上位にランクインしているAI関連ツール・サービスTOP3を教えてください。

以下のJSON形式のみで返してください（説明文・コードブロック不要）:
[
  {{
    "name": "ツール名",
    "description": "一言説明",
    "upvotes": 数値,
    "url": "Product HuntのURL"
  }}
]

情報が取得できない場合は [] を返してください。
"""
    try:
        response = grok_client.chat(
            messages=[{"role": "user", "content": prompt}],
            search_mode="on",
            search_sources=[{"type": "web"}],
        )
        return _parse_json_response(response)
    except Exception:
        return []


def fetch_google_trends(grok_client: GrokClient | None = None) -> dict:
    if grok_client is None:
        grok_client = GrokClient()

    date = datetime.now().strftime("%Y年%m月%d日")
    prompt = f"""
{date}現在のGoogle Trendsで日本で急上昇中のAI関連キーワードと、ClaudeおよびChatGPTの関連急上昇キーワードを教えてください。

以下のJSON形式のみで返してください（説明文・コードブロック不要）:
{{
  "rising_keywords": ["キーワード1", "キーワード2"],
  "related_rising": ["関連キーワード1", "関連キーワード2"]
}}

情報が取得できない場合は {{"rising_keywords": [], "related_rising": []}} を返してください。
"""
    try:
        response = grok_client.chat(
            messages=[{"role": "user", "content": prompt}],
            search_mode="on",
            search_sources=[{"type": "web"}],
        )
        return _parse_json_response(response)
    except Exception:
        return {"rising_keywords": [], "related_rising": []}
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_searchers.py -v
```

Expected: 13 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/searchers.py research/tests/test_searchers.py
git commit -m "feat: add Product Hunt and Google Trends searchers via Grok web search"
```

---

## Task 7: URLChecker

**Files:**
- Create: `research/formatter.py`
- Create: `research/tests/test_formatter.py`

- [ ] **Step 1: テストを書く**

`research/tests/test_formatter.py` を以下の内容で作成:

```python
from unittest.mock import patch, MagicMock
import pytest
import requests as req
from research.formatter import check_urls


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

    assert "https://good.com/page" in result
    assert "⚠️" not in result.split("https://good.com/page")[1].split("https://bad.com/page")[0]
    assert "https://bad.com/page ⚠️ URL要確認" in result
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_formatter.py -v
```

Expected: `ImportError: cannot import name 'check_urls'`

- [ ] **Step 3: URLChecker を実装**

`research/formatter.py` を以下の内容で作成:

```python
import re
import requests
from research.grok_client import GrokClient

URL_PATTERN = re.compile(r'https?://[^\s\)\]（）「」、。\n⚠️]+')


def check_urls(report: str) -> str:
    urls = list(set(URL_PATTERN.findall(report)))
    for url in urls:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code >= 400:
                report = report.replace(url, f"{url} ⚠️ URL要確認")
        except Exception:
            report = report.replace(url, f"{url} ⚠️ URL要確認")
    return report
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_formatter.py -v
```

Expected: 4 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/formatter.py research/tests/test_formatter.py
git commit -m "feat: add URL checker with HEAD request validation"
```

---

## Task 8: ReportGenerator

**Files:**
- Modify: `research/formatter.py`
- Modify: `research/tests/test_formatter.py`

- [ ] **Step 1: テストを追加**

`research/tests/test_formatter.py` の末尾に以下を追記:

```python
from research.formatter import generate_report
from research.grok_client import GrokClient

SAMPLE_DATA = {
    "date": "2026.04.08",
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_formatter.py::test_generate_report_calls_grok_with_all_data -v
```

Expected: `ImportError: cannot import name 'generate_report'`

- [ ] **Step 3: ReportGenerator を実装**

`research/formatter.py` に以下を追記（`check_urls` の後）:

```python
REPORT_PROMPT_TEMPLATE = """
以下のデータを使って、AIトレンドリサーチレポートを生成してください。

【重要ルール】
- 提供されたデータのみを使用し、存在しない情報・URLを絶対に追加しないこと
- 数値（いいね数、RT数など）は提供されたデータをそのまま使用すること
- URLが不明な場合は記載しないこと
- 英語コンテンツには日本語訳と「日本語圏での重要性」を一言添えること

【収集データ】
{data}

【出力フォーマット】（このフォーマットに厳密に従ってください）

■ 今日の一言サマリー（全体を2〜3文で）
[ここにサマリー]

■ 速報ニュース TOP5（Xより）
1. 投稿者 / 種別（通常 / スレッド / X長文記事）
   内容：
   反応：いいね○ / RT○ / ブックマーク○
   URL: [URL]
   ※英語の場合：日本語訳 / 日本語圏での重要性：

■ エンジニア界隈の注目トピック TOP3（HackerNewsより）
1. タイトル（Points○ / Comments○）
   内容：
   URL: [URL]

■ 海外ユーザーのリアルな声 TOP3（Redditより）
1. タイトル（アップボート○ / コメント○）
   内容：
   URL: [URL]

■ 今日の注目AIツール（Product Huntより）
1. ツール名：一言説明（アップボート○）
   URL: [URL]

■ 急上昇キーワード（Google Trendsより）
・急上昇ワード：
・注目の関連キーワード：

■ 今日のイチオシネタ
・テーマ：
・なぜ今これが熱いか：
・おすすめの切り口：
・活用先タグ：【X投稿向け】【ニュースレター向け】【研修教材向け】から該当するものをすべて選択
"""


def generate_report(data: dict, grok_client: GrokClient | None = None) -> str:
    if grok_client is None:
        grok_client = GrokClient()

    import json as _json
    data_str = _json.dumps(data, ensure_ascii=False, indent=2)
    prompt = REPORT_PROMPT_TEMPLATE.format(data=data_str)

    return grok_client.chat(
        messages=[{"role": "user", "content": prompt}],
        search_mode="off",
    )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/test_formatter.py -v
```

Expected: 6 tests PASSED

- [ ] **Step 5: Commit**

```bash
cd /Users/kou/sns_ai && git add research/formatter.py research/tests/test_formatter.py
git commit -m "feat: add report generator using Grok with anti-hallucination prompt"
```

---

## Task 9: ResearchRunner（並列オーケストレーション）

**Files:**
- Create: `research/research.py`

- [ ] **Step 1: research.py を作成**

`research/research.py` を以下の内容で作成:

```python
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from research.grok_client import GrokClient
from research.searchers import (
    fetch_x_posts,
    fetch_hn_stories,
    fetch_reddit_posts,
    fetch_product_hunt,
    fetch_google_trends,
)
from research.formatter import generate_report, check_urls


def run_research() -> str:
    load_dotenv()

    grok_client = GrokClient()
    date = datetime.now().strftime("%Y.%m.%d")

    print("🔍 リサーチ開始...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            "x_posts": executor.submit(fetch_x_posts, grok_client),
            "hn_stories": executor.submit(fetch_hn_stories),
            "reddit_posts": executor.submit(fetch_reddit_posts),
            "product_hunt": executor.submit(fetch_product_hunt, grok_client),
            "google_trends": executor.submit(fetch_google_trends, grok_client),
        }
        results = {}
        for key, future in futures.items():
            try:
                results[key] = future.result()
                print(f"  ✅ {key}")
            except Exception as e:
                results[key] = []
                print(f"  ⚠️  {key} 取得失敗: {e}")

    results["date"] = date

    print("📝 レポート生成中...")
    report = generate_report(results, grok_client)

    print("🔗 URL疎通確認中...")
    report = check_urls(report)

    output_path = Path(f"01_リサーチ/{date}.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    url_warnings = report.count("⚠️ URL要確認")
    print(f"\n✅ レポート保存完了: {output_path}")
    if url_warnings > 0:
        print(f"⚠️  要確認URL: {url_warnings}件")

    return str(output_path)


if __name__ == "__main__":
    run_research()
```

- [ ] **Step 2: 動作確認（ドライラン）**

`GROK_API_KEY` が `.env` に設定済みであることを確認:

```bash
cd /Users/kou/sns_ai && grep GROK_API_KEY .env
```

Expected: `GROK_API_KEY=xai-...` が表示される

- [ ] **Step 3: 全テストが通ることを確認**

```bash
cd /Users/kou/sns_ai && python -m pytest research/tests/ -v
```

Expected: 19 tests PASSED

- [ ] **Step 4: Commit**

```bash
cd /Users/kou/sns_ai && git add research/research.py
git commit -m "feat: add research orchestrator with parallel execution"
```

---

## Task 10: `/research` スラッシュコマンド

**Files:**
- Create: `.claude/commands/research.md`

- [ ] **Step 1: コマンドファイルを作成**

`.claude/commands/research.md` を以下の内容で作成:

```markdown
# AIトレンドリサーチ実行

AIトレンドリサーチを自動実行し、今日の日付でレポートを保存します。

## 手順

### 1. スクリプトを実行

以下のコマンドを Bash ツールで実行してください:

```bash
cd /Users/kou/sns_ai && python -m research.research
```

### 2. 結果を報告

実行完了後、以下を報告してください:

- 保存先ファイルのパス（例: `01_リサーチ/2026.04.08.md`）
- ⚠️ URL要確認 の件数（0件の場合は「全URL正常」と報告）
- 各ステップの取得状況（失敗したステップがある場合は明記）

### 3. エラーが発生した場合

`GROK_API_KEY` が設定されていない場合は `.env` に追加するよう案内してください。
その他のエラーは内容をそのまま報告してください。
```

- [ ] **Step 2: コマンドが認識されることを確認**

Claude Code のプロンプトで `/research` と入力するとコマンドが補完候補に表示されることを確認。

- [ ] **Step 3: 実際にコマンドを実行してレポートが生成されることを確認**

```bash
cd /Users/kou/sns_ai && python -m research.research
```

Expected: `01_リサーチ/YYYY.MM.DD.md` が生成され、既存ファイル (`01_リサーチ/2026.04.08.md`) と同じフォーマットになっていることを目視確認。

- [ ] **Step 4: Commit**

```bash
cd /Users/kou/sns_ai && git add .claude/commands/research.md
git commit -m "feat: add /research slash command"
```

---

## 完了チェックリスト

- [ ] `python -m pytest research/tests/ -v` → 19 tests PASSED
- [ ] `.env` に `GROK_API_KEY` が設定済み
- [ ] `python -m research.research` で `01_リサーチ/YYYY.MM.DD.md` が生成される
- [ ] 生成レポートが `リサーチの仕組み.md` のフォーマットと一致する
- [ ] `/research` コマンドが Claude Code で補完表示される
