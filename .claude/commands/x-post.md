# x-post: 海外Xツイート→日本語スレッド下書き作成

海外のXツイート（URLまたはID）を受け取り、日本語翻訳してファイルに保存するスキル。
Typefullyへの投稿は `/typefully-draft <ファイルパス>` で行う。

## 使い方
```
/x-post <ツイートURLまたはID>
```

---

以下の手順で処理してください：

### Step 1: ツイートID抽出

入力からツイートIDを抽出する。
- URL形式 `https://x.com/username/status/1234567890` → ID: `1234567890`
- ID直接入力 → そのまま使用

### Step 2: メインツイート取得

```bash
xurl read <tweet_id>
```

レスポンスから以下を取得：
- `conversation_id`
- `author_id` / `username`
- ツイート本文

### Step 3: スレッド全文取得

```bash
xurl search "conversation_id:<conversation_id> from:<username>"
```

取得したツイートを時系列順（created_at昇順）に並べ替える。
**リプライ（本文が @で始まるツイート）は除外する。**

### Step 4: 画像URL取得

各ツイートIDについて、APIで画像を取得：

```bash
xurl "/2/tweets?ids=<tweet_ids_comma_separated>&media.fields=url,preview_image_url&expansions=attachments.media_keys"
```

`includes.media` からtype=`photo`のURLを収集する。
type=`video`の場合はスキップしてユーザーに通知する。
どのツイートにどの画像が紐づくかを記録しておく。

### Step 5: 画像ダウンロード

```bash
curl -o /Users/kou/sns_ai/images/<filename> "<image_url>"
```

ファイル名は `<tweet_id>_<連番>.jpg` などわかりやすい名前にする。

### Step 6: 日本語翻訳・スレッド構成

以下のルールで翻訳・構成する：

**翻訳ルール：**
- カジュアルだが知的なトーン（ですます調ではなく、だ・である調でもなく、SNS的な自然な語感）
- 1ツイート280文字以内に収める
- 1ツイート目の冒頭に元投稿者のクレジットを追加：
  ```
  元スレッド: @<username>
  ```
- 最終ツイートは「日本市場への示唆や問いかけ」で締める（例：「日本でも〜な動きが出てくるかも？あなたはどう思う？」）
- スレッドの流れ・論理構成を保ちながら翻訳する

### Step 7: ファイルへの保存

**保存先ディレクトリ:** `/Users/kou/sns_ai/02_アウトプット/X投稿/下書き/`

**ファイル名形式:** `{YYYY.MM.DD}_{HHMM}_{username}.md`
- 例: `2026.04.10_1430_elonmusk.md`
- 日時は Bash ツールで `date '+%Y.%m.%d_%H%M'` を実行して取得する

**ファイルフォーマット:**

```markdown
# X投稿下書き — @{username}
作成日時: {YYYY年MM月DD日 HH:MM}
元URL: https://x.com/{username}/status/{tweet_id}

{1ツイート目の翻訳本文}
<!-- IMAGES: /Users/kou/sns_ai/images/<filename1> -->

---

{2ツイート目の翻訳本文}

---

{3ツイート目の翻訳本文}
<!-- IMAGES: /Users/kou/sns_ai/images/<filename2> -->
```

**フォーマットルール:**
- ツイート間の区切りは `---`（前後に空行を入れる）
- 画像がある場合は、そのツイートブロック内の本文直後に `<!-- IMAGES: <絶対パス> -->` を記載する
- 画像が複数ある場合は複数行に分けて記載する（1行1ファイル）
- ヘッダー部分（`# X投稿下書き`〜`元URL:`）は `---` で区切られたツイートブロックとは別扱いにする
- 動画はスキップし、`<!-- VIDEO: スキップ（動画は非対応） -->` と記載する

### Step 8: 完了報告

以下を報告する：
- 保存先ファイルパス
- スレッド構成（何ツイート）
- ダウンロードした画像数
- スキップした動画があれば通知
- 次のステップとして以下を案内する：
  ```
  内容を確認後、Typefullyに下書き保存するには:
  /typefully-draft <保存したファイルパス>
  ```
