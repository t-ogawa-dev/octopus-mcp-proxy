# Claude 開発ガイド

このファイルは、Octopus MCP Proxy を変更する AI エージェントと開発者向けの作業ルールです。プロジェクトの構成やテストの詳細は [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) を参照してください。

## プロジェクト概要

- Python 3.10 以上で動作する Flask アプリケーション
- FastMCP/MCP プロトコルの HTTP・stdio 中継
- Flask-SQLAlchemy + Alembic によるデータ管理
- Web 管理画面、REST API、MCP エンドポイントを同じアプリファクトリから提供
- Docker Compose では `caddy`、`web`、`mcp`、`redis`、`db` を構成

## 変更前の確認

1. 変更対象のファイル、シンボル、失敗しているテストまたは再現手順を最初の起点にする。
2. 近傍の実装、呼び出し元、関連テストだけを読み、動作を決めている層を特定する。
3. 変更前に、原因について検証可能な仮説と、最も安価な確認方法を1つ決める。
4. 既存の未コミット変更を確認し、ユーザーの変更を上書き・破棄しない。

## レイヤーと変更先

- ルート登録・アプリ初期化: `app/__init__.py`
- 設定: `app/config/config.py`
- 認証・管理画面: `app/controllers/auth_controller.py`, `admin_controller.py`
- REST API: `app/controllers/api_controller.py`
- MCP プロトコル: `app/controllers/mcp_controller.py`, `admin_mcp_controller.py`
- DB モデル: `app/models/models.py`
- 中核ロジック: `app/services/`
- Jinja2 テンプレート: `app/views/templates/`
- CSS/JavaScript/画像: `app/assets/`
- DB マイグレーション: `db/migrations/versions/`
- テスト: `tests/unit/`, `tests/integration/`, `tests/e2e/`

コントローラーに複雑な業務ロジックを追加せず、再利用される処理は `app/services/` に置く。DB スキーマ変更を伴う場合はモデルだけでなく Alembic マイグレーションとテストを更新する。

## コーディング規約

- 既存の Flask Blueprint、SQLAlchemy ORM、アプリファクトリのパターンを維持する。
- Python のファイル・関数・変数は `snake_case`、クラスは `PascalCase` を使う。
- Ruff の設定は `pyproject.toml` を唯一の基準とする。行長の警告を手作業で回避しない。
- 公開 API、ルート、モデルの既存契約を変更する場合は、関連するテストとドキュメントも更新する。
- 秘密情報、トークン、実データをソースコード・ログ・スクリーンショットに含めない。
- 画像や生成物を手作業で編集せず、既存スクリプトで再生成する。
- 無関係なリファクタリング、依存関係更新、フォーマット変更を混ぜない。
- コメントはコードから意図を読み取れない複雑な処理にだけ追加する。

## 検証コマンド

```bash
# 静的チェック・フォーマット確認
./run_check.sh

# 自動修正・フォーマット
./run_format.sh

# 全テスト（カバレッジも生成）
./run_tests.sh

# 対象を絞ったテスト
pytest tests/unit/path/to/test_file.py -q

# スクリーンショット再生成（Playwright Chromium が必要）
python scripts/capture_screenshots.py
```

変更後は、まず変更範囲に最も近いテストまたはチェックを実行し、その後必要に応じて全体チェックを行う。テンプレート/CSS/画像を変更した場合は、関連する E2E テストまたはスクリーンショットも確認する。

## 起動方法

```bash
# 推奨: Docker Compose
cp .env.example .env
docker compose up -d

# ローカルの Flask 開発サーバー
source .venv/bin/activate
python run.py
```

本番相当では `FLASK_ENV=production` を使う。`SECRET_KEY`、管理者認証情報、DB 接続先、`ACCELMCP_ADMIN_API_KEY` は必ず環境変数で設定する。デフォルト認証情報はデモ・検証用であり、本番利用しない。

## 変更完了時の確認

- 変更対象とテスト結果を簡潔に報告する。
- 実行できなかった検証、既存の警告、未解決のリスクを明記する。
- コミットやブランチ作成は依頼がない限り行わない。
