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
