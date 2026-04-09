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


REDDIT_SUBREDDITS = ["LocalLLaMA", "ChatGPT", "ClaudeAI"]


def fetch_reddit_posts() -> list[dict]:
    results = []
    for subreddit in REDDIT_SUBREDDITS:
        for _ in range(3):
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
                break  # success - exit retry loop
            except Exception:
                continue  # retry on failure (after 3 failures, move to next subreddit)
    return results[:5]


X_QUERIES = ["AI 新機能", "LLM リリース", "OpenAI", "Claude"]


def _parse_json_response(text: str) -> list | dict:
    import re
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


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
        parsed = _parse_json_response(response)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


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
        parsed = _parse_json_response(response)
        return parsed if isinstance(parsed, list) else []
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
        parsed = _parse_json_response(response)
        return parsed if isinstance(parsed, dict) else {"rising_keywords": [], "related_rising": []}
    except Exception:
        return {"rising_keywords": [], "related_rising": []}
