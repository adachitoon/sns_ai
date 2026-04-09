import re
import requests

URL_PATTERN = re.compile(r'https?://[^\s\)\]（）「」、。\n⚠️]+')


def check_urls(report: str) -> str:
    urls = list(set(URL_PATTERN.findall(report)))
    bad_urls: set[str] = set()
    for url in urls:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code >= 400:
                bad_urls.add(url)
        except Exception:
            bad_urls.add(url)

    if not bad_urls:
        return report

    def replacer(match: re.Match) -> str:
        u = match.group(0)
        return f"{u} ⚠️ URL要確認" if u in bad_urls else u

    return URL_PATTERN.sub(replacer, report)


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


def generate_report(data: dict, grok_client: "GrokClient | None" = None) -> str:
    from research.grok_client import GrokClient as _GrokClient
    if grok_client is None:
        grok_client = _GrokClient()

    import json as _json
    data_str = _json.dumps(data, ensure_ascii=False, indent=2)
    prompt = REPORT_PROMPT_TEMPLATE.format(data=data_str)

    return grok_client.chat(
        [{"role": "user", "content": prompt}],
        search_mode="off",
    )
