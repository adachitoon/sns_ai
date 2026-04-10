# typefully-draft: TypeFully下書き作成コマンド

ツイート本文（単体またはスレッド）、またはx-postが出力した下書きファイルを受け取り、TypeFullyに下書きとして保存する。

## 使い方

**パターンA: ファイルから（x-postの出力ファイルを使う場合）**
```
/typefully-draft /Users/kou/sns_ai/02_アウトプット/X投稿/下書き/2026.04.10_1430_username.md
```

**パターンB: テキスト直接入力**
```
/typefully-draft <ツイート本文>
```

スレッドの場合は、ツイートを `---` で区切って渡す。

**例（単体）:**
```
/typefully-draft AIを業務に使うなら、まず「どこに一番時間を取られているか」を特定するのが先。ツール選びはその後でいい。
```

**例（スレッド）:**
```
/typefully-draft
1本目のツイート本文
---
2本目のツイート本文
---
3本目のツイート本文
```

---

## 処理手順

### Step 1: 入力の判定とパース

引数が `.md` ファイルパスの場合 → **パターンA（ファイル読み込み）**
それ以外 → **パターンB（テキスト直接入力）**

**パターンA: ファイル読み込み**

Readツールでファイルを読み込み、以下のルールでパースする：

1. ヘッダー（`# X投稿下書き`〜`元URL:`行まで）は無視する
2. 残りのコンテンツを `---` で分割してツイートブロックのリストにする
3. 各ブロックから以下を抽出する：
   - **ツイート本文**: `<!-- IMAGES: ... -->` および `<!-- VIDEO: ... -->` コメント行を除いたテキスト（前後の空白・改行はトリム）
   - **画像パス**: `<!-- IMAGES: <パス> -->` 行から絶対パスを抽出（複数行ある場合は全て収集）
4. `<!-- VIDEO: ... -->` コメントが含まれるブロックは画像なしとして扱い、ユーザーに通知する

**パターンB: テキスト直接入力**

- `---` で分割してツイートリストにする（区切りがない場合は1ツイート）
- 画像パスなし

### Step 2: 文字数チェック

各ツイートが **280文字以内** であることを確認する。

- 超過している場合は処理を止め、どのツイートが何文字かを報告してユーザーに修正を求める
- OKであれば次のステップへ

### Step 3: APIキー読み込み

```bash
grep TYPEFULLY_API_KEY /Users/kou/sns_ai/.env | cut -d '=' -f2
```

取得した値を `TYPEFULLY_API_KEY` として以降のステップで使用する。

### Step 4: Social Set ID 取得

```bash
curl -s -H "Authorization: Bearer $TYPEFULLY_API_KEY" \
  https://api.typefully.com/v2/social-sets
```

レスポンスの `results[0].id` を `SOCIAL_SET_ID` として使用する。

### Step 5: 画像アップロード（画像がある場合のみ）

画像パスが1件以上ある場合のみ実行する。

**5-1. プリサインドURL取得**

各画像ファイルについて：

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TYPEFULLY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_name": "<filename>", "content_type": "image/jpeg"}' \
  "https://api.typefully.com/v2/social-sets/<SOCIAL_SET_ID>/media/upload"
```

> ⚠️ フィールド名は `file_name`（アンダースコアあり）。`filename` では VALIDATION_ERROR になる。
> `content_type` は実際のファイル形式に合わせて `image/png` または `image/jpeg` を指定する。

レスポンスから `upload_url`（S3プリサインドURL）と `media_id` を取得し、元の画像パスと対応付けて記録する。

**5-2. S3へアップロード（必ず `-T` フラグを使う）**

```bash
curl -T <画像の絶対パス> "<upload_url>"
```

> ⚠️ `--data-binary` や `-d` は403エラーになるため使用禁止。必ず `-T` を使うこと。

### Step 6: 下書き作成

翻訳済みツイートと画像の `media_id` を組み合わせてTypefullyに下書きを作成する。

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TYPEFULLY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "platforms": {
      "x": {
        "enabled": true,
        "posts": [
          {"text": "<tweet1>", "media_ids": ["<media_id_1>"]},
          {"text": "<tweet2>", "media_ids": []},
          {"text": "<tweet3>", "media_ids": []}
        ]
      },
      "linkedin": {"enabled": false},
      "mastodon": {"enabled": false},
      "threads": {"enabled": false},
      "bluesky": {"enabled": false}
    }
  }' \
  "https://api.typefully.com/v2/social-sets/<SOCIAL_SET_ID>/drafts"
```

**注意事項:**
- `posts` 配列にツイートを1件ずつ入れる（スレッドは複数要素）
- 画像がないツイートの `media_ids` は空配列 `[]`
- 画像があるツイートの `media_ids` にはStep 5で取得した `media_id` を入れる
- `scheduled_date` は設定しない（下書きのまま保存）

### Step 7: 完了報告

以下を報告する:

- 下書きURL（`private_url` フィールド）
- ツイート数（単体 or Nツイートスレッド）
- 各ツイートの文字数
- アップロードした画像数

**報告フォーマット:**
```
下書きを作成しました。

TypeFully: https://typefully.com/?d=XXXXXXX&a=XXXXXX
構成: Nツイートスレッド
1/N: XX文字（画像: 1枚）
2/N: XX文字
...
```
