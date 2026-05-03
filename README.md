# bug-chaser

Discordのフォーラム投稿を監視し、報告の取得、タグ状態判定、管理補助、Google Sheetsと連携を行うDiscord-Botです。

## 主な機能

- フォーラムチャンネル内のスレッドを収集し、タイトル・本文・投稿者・タグ・リアクション・返信数などをまとめます。
- フォーラムごとの YAML で監視対象、状態ルール、自動アクション、任意の Sheets 連携を設定します。
- タグの排他制御を提供します。
- 同期結果をSQLiteに保存します。
- `/bugchaser` スラッシュコマンドで同期の手動実行や Sheets・自動処理のオンオフができます。
- Google Sheets 連携は任意です。有効にするとフォーラムごとにスプレッドシートを用意でき、Bot が 1枚目にマスターデータを転記し、2枚目は進捗管理用として利用できます。

## セットアップ


Linux/macOS:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```


Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

`.env` に Discord Bot token などを設定してください。

## 環境変数

`.env.example` をコピーして `.env` を作成し、ローカル環境に合わせて値を設定します。


- `BUG_CHASER_DISCORD_TOKEN`: Discord Developer Portal で発行した Bot token です。
- `BUG_CHASER_CONFIG_DIR`: フォーラム別 YAML を置くディレクトリです。通常は `config/forums` のままで使います。
- `BUG_CHASER_DB_PATH`: 同期結果を保存する SQLite データベースのパスです。親ディレクトリは起動時に自動作成されます。
- `BUG_CHASER_GOOGLE_SERVICE_ACCOUNT_FILE`: Google Sheets 連携を使う場合に、Service Account 認証 JSON のパスを指定します。Sheets 連携を使わない場合は空で構いません。
- `BUG_CHASER_COMMAND_GUILD_ID`: スラッシュコマンドを即時反映したいDiscordサーバーの Guild IDです。未設定の場合はグローバルコマンドとして同期され、反映に時間がかかる場合があります。

## Google Sheets 連携

Sheets 連携は Service Account 方式です。

1. Google Cloud で Google Sheets API と Google Drive API を有効化します。
2. Service Account を作成します。
3. 認証 JSON を保存します。
4. `BUG_CHASER_GOOGLE_SERVICE_ACCOUNT_FILE` に JSON のパスを設定します。
5. フォーラム別 YAML の `forum.sheets.configured` を `true` にし、`editor_emails` を最低 1 件指定します。

所有者移譲は Google アカウント種別や Workspace ドメイン制約で失敗する場合があります。その場合でも編集者共有までは行い、ログに警告を出します。

## フォーラム設定

`config/forums/example.yaml` を参考に、`config/forums/<forum_key>.yaml` を作成して編集します。

> 注意:`example.yaml` は読み込みません。リポジトリ内のサンプル用です。

### states と state_order

states(forum上のタグ名)とstate_order(優先度)はユーザーが指定することができます。

- `states` のキーが状態 ID（小文字の識別子）になります。
- `state_order` に状態 ID を並べ、**先頭から順に**タグ照合されます（最初にマッチした状態が採用されます）
- 状態の個数は **最大 20**（Discord API のフォーラムチャンネル `available_tags` の上限と同じ）
- YAMLで参照するタグ名は Discord のフォーラムタグ `name` と一致させてください（長さ 1〜20 文字）。Bot起動時にフォーラムチャンネルの利用可能タグと突き合わせ、存在しない名前があれば起動に失敗します。
- どの状態にもマッチしないスレッドは `open` として扱われ、コンソールに警告ログが出ます。

### actions

`actions` の各エントリは、キー名に対応する 1 つのアクション定義です。

- **キー名**: **`when_<状態ID>`**（`states` のキーと一致する識別子。例: 状態 `closed` なら `when_closed`）自動化の発火元（タグの追加・状態遷移）に合わせて、ここに定義した内容が使われます。

各 `when_*` の下で指定できる **アクション用フィールド**（`ActionRule`）は以下の通りです。(いずれも任意)

| フィールド | 型 | 意味 |
| --- | --- | --- |
| `add_comment` | str | スレッドに送る 1 件のメッセージ。 |
| `add_tags` | list[str] | 付け足すフォーラムタグの名前（Discord のタグ `name` と一致）。 |
| `remove_tags` | list[str] | 外すフォーラムタグの名前。 |
| `archive` | bool | `true` のときスレッドをアーカイブする。 |
| `lock` | bool | `true` のときスレッドをロックする。 |
| `reopen` | bool | `true` のときアーカイブ解除・ロック解除（再開）する。 |

タグの排他をしたい場合は、遷移先以外の状態タグを `remove_tags` に書きます。

**自動化フラグ**: 上記のうち、実際に Bot が実行するのは `forum.automation` でオンになっている項目だけです。例: `add_comment` は `auto_comment: true`、`add_tags` / `remove_tags` は `auto_tag: true`、`archive` は `auto_archive: true`、`lock` は `auto_lock: true` が必要です。オフの項目は YAML に書いても無視されます。


## 起動

```powershell
bug-chaser
```

または:

```powershell
python -m bug_chaser
```

## スラッシュコマンド

Botを招待したチャンネルで以下のコマンドが使用可能です。

- `/bugchaser run`: 全フォーラムを同期
- `/bugchaser channel`: 指定フォーラムを同期
- `/bugchaser thread`: 指定スレッドを同期
- `/bugchaser dry-run`: 書き込みなしで同期結果を確認
- `/bugchaser status`: 設定状況を表示
- `/bugchaser export`: Sheets 有効フォーラムを再同期
- `/bugchaser sheets on/off`: Sheets 連携を開始/停止
- `/bugchaser automation on/off`: 自動コメント、タグ付け、アーカイブ、ロックの有効/無効を切替
- `/bugchaser close`: スレッドをロックしてアーカイブ
- `/bugchaser reopen`: スレッドを再開


## パッケージ構成

- `bug_chaser.core`: ドメインモデルと実行設定
- `bug_chaser.config`: フォーラム別 YAML の読み込みと検索
- `bug_chaser.discord`: Discord Gateway、コマンド、スレッド取得、管理操作
- `bug_chaser.rules`: タグ優先の状態判定
- `bug_chaser.sheets`: 任意の Google Sheets 連携
- `bug_chaser.storage`: SQLite 永続化
- `bug_chaser.sync`: 同期サービスとスケジューラ


## Discordモジュール構成

- `bug_chaser.discord.lady`: エントリーポイント
- `bug_chaser.discord.bird`: フォーラムスレッド収集
- `bug_chaser.discord.gloop`: 投稿情報の正規化
- `bug_chaser.discord.mothman`: `/bugchaser` コマンド定義
- `bug_chaser.discord.guard`: Discord 側の管理操作


## ライセンス

[MIT License](LICENSE)
