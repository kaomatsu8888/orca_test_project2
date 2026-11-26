# todo CLI 設計書

Python 3.8+ 標準ライブラリのみで動く最小の TODO 管理 CLI。外部依存なし。

## ファイル構成
```
todo.py         # エントリポイント。argparse でサブコマンドを振り分ける
storage.py      # JSON の読み込み・保存（load_todos / save_todos）
tests/test_todo.py  # unittest によるテスト
```
保存先は既定で `./todos.json`。環境変数 `TODO_FILE` で変更可能。

## データ形式（todos.json）
```json
{"next_id": 3, "items": [
  {"id": 1, "title": "牛乳を買う", "done": false, "created_at": "2026-11-26T10:00:00"},
  {"id": 2, "title": "本を返す", "done": true, "created_at": "2026-11-26T11:00:00"}]}
```
- `id` は 1 から始まる連番。削除がないため `next_id` で採番し再利用しない。
- ファイルが無ければ空データ `{"next_id": 1, "items": []}` として扱う。
- 保存は一時ファイルに書いてから `os.replace` で置き換える（破損防止）。UTF-8, `ensure_ascii=False`。

## コマンド
- `todo add <title>`: タイトルを追加し `Added #<id>: <title>` を表示。空文字ならエラー。
- `todo list [--all]`: 未完了のみを `#id [ ] title` 形式で id 昇順に表示。
  `--all` で完了済みも `[x]` 付きで表示。0 件なら `No todos.` を表示。
- `todo done <id>`: 該当項目を `done: true` にし `Done #<id>: <title>` を表示。
  既に完了済みなら `Already done #<id>` を表示（終了コード 0）。

## エラー処理・終了コード
- 0: 成功 / 1: 存在しない id・空タイトル・JSON 破損 / 2: 引数誤り（argparse 既定）
- エラーメッセージは stderr に出力。JSON 破損時はファイルを上書きせず終了する。

## 実行方法
`python todo.py add "牛乳を買う"` / `python todo.py list` / `python todo.py done 1`

## rm コマンド追加
- `todo rm <id>`: 該当項目を `items` から取り除いて保存し `Removed #<id>: <title>` を表示。完了・未完了を問わず削除できる。
- `id` は `done` と同じく argparse の `type=int` で受け取る。整数として解釈できない値は argparse エラー（終了コード 2）。
- 削除後も `next_id` は減らさず、削除済みの id は再利用しない（過去の id と別項目の取り違えを防ぐ）。
- 存在しない id（0・負数を含む）は stderr に `Error: todo #<id> not found` を出して終了コード 1。ファイルは書き換えない。
- JSON 破損時は他コマンドと同様にファイルを上書きせず終了コード 1。保存失敗（OSError）も終了コード 1。
- 確認プロンプトは出さない（スクリプトから使えるよう非対話）。複数 id の同時指定は対象外。
- 保存は既存の `save_todos`（一時ファイル + `os.replace`）を使う。
- 終了コード: 0 成功 / 1 存在しない id・JSON 破損・保存失敗 / 2 引数誤り。
