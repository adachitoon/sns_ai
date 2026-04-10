import json
import os
import urllib.request
from openai import OpenAI

# sources形式 → Agent Tools API のツール型名マッピング
_SOURCE_TO_TOOL_TYPE = {
    "x": "x_search",
    "web": "web_search",
}

RESPONSES_ENDPOINT = "https://api.x.ai/v1/responses"
SEARCH_MODEL = "grok-4-fast-non-reasoning"


class GrokClient:
    def __init__(self):
        api_key = os.environ.get("GROK_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY が環境変数に設定されていません")
        self._api_key = api_key
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
        if search_mode != "off":
            sources = search_sources or [{"type": "web"}]
            return self._search(messages, sources)

        kwargs: dict = {
            "model": "grok-3",
            "messages": messages,
        }
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("API returned empty content")
        return content

    def _search(self, messages: list[dict], sources: list[dict]) -> str:
        tools = [
            {"type": _SOURCE_TO_TOOL_TYPE.get(s["type"], s["type"])}
            for s in sources
        ]
        payload = {
            "model": SEARCH_MODEL,
            "input": messages,
            "tools": tools,
        }
        req = urllib.request.Request(
            RESPONSES_ENDPOINT,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())

        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        text = c.get("text")
                        if text is None:
                            raise ValueError("API returned empty content")
                        return text

        raise ValueError("API returned no text content")
