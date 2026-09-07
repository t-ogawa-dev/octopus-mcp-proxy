[English](en/DEVELOPMENT.en.md) | 日本語

# 開発ガイド

## システムの責務

Octopus MCP Proxy は、管理画面・REST API・MCP エンドポイントを1つの Flask アプリファクトリから提供します。MCP リクエストはサービス定義、Capability、接続アカウント、権限設定を参照して中継され、接続ログと監査ログに記録されます。

## ディレクトリと責務

| パス                      | 責務                                                        |
| ------------------------- | ----------------------------------------------------------- |
| `app/__init__.py`         | アプリファクトリ、拡張機能初期化、Blueprint 登録、`/health` |
| `app/config/`             | 環境変数を含む設定クラス                                    |
| `app/controllers/`        | HTTP ルート、認証、API、MCP リクエストの入口                |
| `app/models/`             | SQLAlchemy モデルと DB 拡張                                 |
| `app/services/`           | MCP 中継、権限、ログ、テンプレート同期、変数展開            |
| `app/views/templates/`    | Jinja2 の HTML テンプレート                                 |
| `app/assets/`             | CSS、JavaScript、画像などの静的ファイル                     |
| `db/migrations/`          | Alembic マイグレーション                                    |
| `db/seeds/`               | 初期管理者・設定・組み込みテンプレートの投入                |
| `data/builtin_templates/` | 組み込み MCP テンプレートの YAML 定義                       |
| `tests/unit/`             | 機能単位のテスト                                            |
| `tests/integration/`      | 複数コンポーネントをまたぐテスト                            |
| `tests/e2e/`              | Playwright によるブラウザテスト                             |
| `scripts/`                | 開発補助スクリプト。スクリーンショット生成など              |

詳細なファイル一覧は [ディレクトリ構造](STRUCTURE.md) を参照してください。

## 代表的な変更手順

### 管理画面や API を追加する場合

1. 適切な Blueprint のコントローラーにルートを追加する。
2. 業務ロジックや外部接続は `app/services/` に置く。
3. DB が必要なら `app/models/models.py` と `db/migrations/versions/` を更新する。
4. テンプレート、JavaScript、i18n 辞書を更新する。
5. 認証、権限、エラー応答、監査ログが必要か確認する。
6. unit/integration テストを追加し、画面変更なら E2E テストも更新する。

### MCP Capability や中継処理を変更する場合

- `app/controllers/mcp_controller.py` はプロトコル入口とルーティングに留める。
- 中継・Capability 解決・変数置換・権限判定は既存のサービス層を優先して変更する。
- `tools/list`、`tools/call`、Prompt、Resource、stdio、Streamable HTTP、旧仕様クライアントの互換性を意識する。
- エラー時の JSON-RPC エラー、HTTP ステータス、接続ログの内容を既存テストで確認する。

### DB スキーマを変更する場合

```bash
# 開発用 DB に対するマイグレーション生成例
flask db migrate -m "describe schema change"
flask db upgrade
```

生成されたマイグレーションを必ず読み、既存データへの影響、NULL/デフォルト値、ロールバック可能性を確認します。`db/migrate.py` と既存のマイグレーション運用も確認してください。

## 設定と実行環境

主な設定は `app/config/config.py` にあります。

- `DATABASE_URL`: DB 接続先。未設定時は SQLite
- `SECRET_KEY`: Flask セッション署名鍵
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`: 初期管理者情報
- `ACCELMCP_ADMIN_API_KEY`: Admin MCP 用 Bearer キー
- `REDIS_URL`: Streamable HTTP セッション共有。未設定時はプロセス内ストア
- `LOG_LEVEL`: `DEBUG`、`INFO`、`WARNING`、`ERROR` など
- `FLASK_DEBUG` / `FLASK_ENV`: 開発・本番モード

Docker Compose では `web` がマイグレーションを実行し、`mcp` は MCP エンドポイントを提供します。Redis は複数レプリカ間の Streamable HTTP セッション共有に使用します。構成の詳細は [スケーリング・コンテナ構成](SCALING.md) を参照してください。

## 品質チェック

```bash
./run_check.sh
```

このスクリプトは Ruff lint、Ruff format check、mypy を実行します。設定は `pyproject.toml` にあります。

```bash
pytest tests/unit/path/to/test_file.py -q
pytest tests/integration/ -q
pytest tests/e2e/ -v
./run_tests.sh
```

E2E テストやスクリーンショット生成には Playwright のブラウザが必要です。

```bash
./setup_playwright.sh
python -m playwright install chromium
```

画面変更後は次のコマンドでドキュメント用画像を更新します。

```bash
python scripts/capture_screenshots.py
```

出力先は `docs/assets/screenshots/` です。画像の差分は意図した画面だけか確認してください。

## 変更時の原則

- 既存の責務分担と命名を維持し、最小の変更で目的を達成する。
- 認証・権限・入力検証・ログ出力を機能追加時に確認する。
- 秘密情報をテストデータ、ログ、画像、ドキュメントへ書き込まない。
- 既存の未コミット変更を破棄しない。
- 実装変更と同じ変更で不要なリファクタリングを行わない。
- 動作を変更したら、テストと関連ドキュメントを同時に更新する。
