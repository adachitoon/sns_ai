# AIトレンドリサーチ自動化システム 設計書

**日付:** 2026-04-08  
**対象:** `/research` カスタムコマンドによるAIトレンド自動収集・レポート生成

---

## 概要

`リサーチの仕組み.md` に定義された5ステップのAIトレンドリサーチを自動化するシステム。
Claude Codeのカスタムコマンド `/research` を実行すると、各ソースからデータを収集し、既存フォーマット通りのレポートを `01_リサーチ/YYYY.MM.DD.md` に保存する。

---

## アーキテクチャ

```
/research コマンド実行
      ↓
.claude/commands/research.md（Claude Codeが読む指示ファイル）
      ↓
research/research.py を実行
      ↓
┌─────────────────────────────────────┐
│  ResearchRunner（並列実行）         │
│  ├── XSearcher（Grok API）          │
│  ├── HackerNewsSearcher（HN API）   │
│  ├── RedditSearcher（Reddit JSON）  │
│  └── GrokWebSearcher               │
│       ├── ProductHuntSearcher       │
│       └── GoogleTrendsSearcher     │
└─────────────────────────────────────┘
      ↓
ReportGenerator（Grok APIでまとめ生成）
      ↓
URLChecker（全URLをHEADリクエストで疎通確認）
      ↓
01_リサーチ/YYYY.MM.DD.md に保存
```

---

## ファイル構成

```
sns_ai/
├── research/
│   ├── research.py        # メインスクリプト（エントリーポイント）
│   ├── searchers.py       # 各ステップのデータ取得ロジック
│   └── formatter.py       # レポート整形・URL疎通確認
├── .claude/commands/
│   └── research.md        # /researchコマンド定義
└── .env                   # GROK_API_KEY を追加
```

---

## 各ステップ詳細

### ステップ1: X速報（Grok API）

- **モデル:** `grok-3`（xAI API: `https://api.x.ai/v1`）
- **検索クエリ:** `AI 新機能`, `LLM リリース`, `OpenAI`, `Claude`
- **フィルタ:** 直近24時間、いいね100以上 or RT50以上 or ブックマーク30以上
- **収集内容:** 投稿者名、内容要約、反応数、URL、英語投稿の場合は日本語訳

Grokのlive search機能（`search_parameters` with `mode: "on"`）を使用してX公式データにアクセス。

### ステップ2: HackerNews（HN Firebase API）

- **エンドポイント:** `https://hacker-news.firebaseio.com/v0/topstories.json`
- **フィルタ:** ポイント100以上 or コメント30以上、タイトルにAI/LLM関連キーワードを含む
- **処理:** トップ50件のIDを取得し、詳細を並列取得
- **収集内容:** タイトル、ポイント数、コメント数、URL

認証不要。構造化データのためGrokを使わず直接取得。

### ステップ3: Reddit（Reddit JSON API）

- **対象サブレディット:** `r/LocalLLaMA`, `r/ChatGPT`, `r/ClaudeAI`
- **エンドポイント:** `https://www.reddit.com/r/{subreddit}/hot.json?limit=25`
- **フィルタ:** アップボート200以上 or コメント50以上
- **ヘッダー:** `User-Agent: sns-ai-research-bot/1.0`
- **収集内容:** タイトル、アップボート数、コメント数、URL

認証不要（パブリックデータ）。構造化データのためGrokを使わず直接取得。

### ステップ4: Product Hunt（Grok webサーチ）

- **プロンプト:** 「今日（{date}）のProduct Huntで上位にランクインしているAI関連ツール・サービスTOP3を教えてください。ツール名、一言説明、アップボート数、URLを含めてください。」
- **理由:** Product HuntのGraphQL APIはOAuth認証が必要なため、Grokのwebサーチを使用。

### ステップ5: Google Trends（Grok webサーチ）

- **プロンプト:** 「Google Trendsで{date}現在、日本で急上昇中のAI関連キーワードと、Claude・ChatGPTの関連急上昇キーワードを教えてください。」
- **理由:** 公式APIが不安定（pytrends）なため、Grokのwebサーチを使用。

---

## レポート生成（Grok API）

5ステップで収集した生データをすべてGrokに渡し、`リサーチの仕組み.md` の最終アウトプットフォーマット通りのレポートを生成する。

**プロンプト制約（ハルシネーション防止）:**
- 「提供したデータのみを使用し、存在しない情報・URLを追加しないこと」
- 「数値（いいね数、RT数など）は提供されたデータをそのまま使用すること」
- 「URLが不明な場合は記載しないこと」

---

## ファクトチェック（URL疎通確認）

レポート生成後、含まれる全URLに対してHEADリクエストを送信。

- **200-399:** そのまま
- **400以上 or タイムアウト:** 該当URLの末尾に `⚠️ URL要確認` を付記
- **タイムアウト設定:** 5秒

これにより `リサーチの仕組み.md` の「最終納品時にURLが記載されているか確認」ルールを自動化する。

---

## エラーハンドリング

| 状況 | 対処 |
|------|------|
| APIキーなし | 起動時にチェックし即座にエラー終了 |
| 各ステップのHTTPエラー | 3回リトライ後スキップ |
| スキップされたステップ | レポートに「※取得エラー、代替調査が必要」と明記 |
| Grokのレート制限 | 指数バックオフで最大3回リトライ |

---

## 環境変数

`.env` に以下を追加：

```
GROK_API_KEY=xai-xxxxxxxxxx
```

既存の `TYPEFULLY_API_KEY` はそのまま維持。

---

## `/research` コマンド定義

`.claude/commands/research.md` の動作：

1. `research/research.py` を実行
2. 生成されたレポートを `01_リサーチ/YYYY.MM.DD.md` に保存
3. 保存完了とURL疎通確認結果を報告

**実行時間の目安:** 並列処理で約30〜60秒

---

## 出力フォーマット

既存の `01_リサーチ/` ディレクトリ内のファイルと同一フォーマットを維持。
`リサーチの仕組み.md` の【最終アウトプット】セクション通り：

- 今日の一言サマリー
- 速報ニュース TOP5（Xより）
- エンジニア界隈の注目トピック TOP3（HackerNewsより）
- 海外ユーザーのリアルな声 TOP3（Redditより）
- 今日の注目AIツール（Product Huntより）
- 急上昇キーワード（Google Trendsより）
- 今日のイチオシネタ
