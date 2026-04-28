# bug-chaser

Discord のフォーラム投稿をスレッドとして監視し、バグ報告の取得、状態判定、管理補助、任意の Google Sheets 連携を行う Bot です。

## 主な方針

- 設定はフォーラムごとの YAML に集約します。
- Google Sheets 連携はオプションです。未設定でも Discord 側の取得、状態判定、DB 保存、コマンドは動作します。
- Sheets 連携を有効にする場合、1フォーラムチャンネルにつき 1つのスプレッドシートを Bot が作成します。
- 1枚目のシートは Bot 管理、2枚目のシートは人間の進捗管理用です。
- 状態判定はタグ優先です。リアクションによる状態管理は初期状態では使いません。

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Linux/macOS の場合:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

`.env` に Discord Bot token などを設定してください。

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

```yaml
forum:
  key: "example-forum"
  guild_id: 123456789012345678
  channel_id: 234567890123456789
  sync:
    interval_minutes: 10
    dry_run_default: true
  sheets:
    configured: false
    enabled: false
    auto_create: true
    spreadsheet_id:
    owner_email: "owner@example.com"
    editor_emails:
      - "owner@example.com"
    master_sheet_name: "Master"
    progress_sheet_name: "Progress"
  automation:
    enabled: false
    auto_comment: false
    auto_tag: false
    auto_archive: false
    auto_lock: false
```

## 起動

```powershell
bug-chaser
```

または:

```powershell
python -m bug_chaser
```

## スラッシュコマンド

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

## Discordモジュール構成

- `bug_chaser.discord.lady`: Discord Bot の入口
- `bug_chaser.discord.bird`: フォーラムスレッド収集
- `bug_chaser.discord.gloop`: 投稿情報の正規化
- `bug_chaser.discord.mothman`: `/bugchaser` コマンド定義
- `bug_chaser.discord.guard`: Discord 側の管理操作

## パッケージ構成

- `bug_chaser.core`: ドメインモデルと実行設定
- `bug_chaser.config`: フォーラム別 YAML の読み込みと検索
- `bug_chaser.discord`: Discord Gateway、コマンド、スレッド取得、管理操作
- `bug_chaser.rules`: タグ優先の状態判定
- `bug_chaser.sheets`: 任意の Google Sheets 連携
- `bug_chaser.storage`: SQLite 永続化
- `bug_chaser.sync`: 同期サービスとスケジューラ
