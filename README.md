# Octopus MCP Proxy

[English](README.en.md) | 日本語

HTTP/stdio 対応の MCP サーバー。API/MCP 中継機能とユーザー別権限管理を備えた Web 管理画面付き。

![Octopus MCP Proxy 概念図](docs/assets/diagrams/architecture-overview.svg)

## 機能

- **MCP プロトコル対応**: HTTP と stdio の両方をサポート
- **中継機能**: API および MCP サーバーへの中継
- **権限管理**: ユーザーごとの Tool 使用権限制御
- **Web 管理画面**: サービス、Capability、ユーザーの管理
- **Bearer トークン認証**: ユーザー別のトークン発行

## MCP プロトコル仕様対応

| 仕様バージョン      | 対応状況                                                    |
| ------------------- | ----------------------------------------------------------- |
| `2026-07-28` (最新) | ✅ **対応済み** — ステートレスリクエスト、`server/discover` |
| `2024-11-05` (旧)   | ✅ 後方互換として継続サポート                               |

### 2026-07-28 対応内容

- **ステートレスリクエスト**: `initialize` ハンドシェイクや `Mcp-Session-Id` なしで `tools/list` / `tools/call` などを直接呼び出せます。
- **`server/discover`**: セッション不要のケーパビリティ検出エンドポイント。`protocolVersions: ["2026-07-28", "2024-11-05"]` を返します。
- **後方互換**: `Mcp-Session-Id` を送る旧仕様クライアントの `initialize` → セッションフローは引き続き動作します。不正なセッション ID を送った場合のみ 400 を返します。

## コンテナ構成

Octopus MCP Proxy は次のコンテナで構成されます（`web` と `mcp` は同一イメージ）。

- `caddy`: リバースプロキシ / TLS（パスで `web` と `mcp` に振り分け）
- `web`: 管理画面 + REST API（起動時に DB マイグレーションを実行）
- `mcp`: MCP エンドポイント（複数レプリカ / 別ホストにスケール可能）
- `redis`: 旧仕様の Streamable HTTP セッションの共有ストア
- `db`: PostgreSQL

1台運用（全部入り）も複数台運用（WEB/MCP/Redis を別サーバに分散）も**同じ compose 定義**で動きます。
旧仕様の MCP セッションは `REDIS_URL` があれば Redis で共有され、未設定ならプロセス内メモリにフォールバックします。
詳細は [スケーリング・コンテナ構成](docs/SCALING.md) を参照してください。

## 起動方法

### 開発環境（デフォルト）

```bash
# Docker Composeで起動
docker compose up -d

# ログ確認
docker compose logs -f

# 停止
docker compose down
```

開発環境では Flask 開発サーバーが起動し、コード変更時に自動リロードされます。

### 本番環境

```bash
# Gunicornで起動
FLASK_ENV=production docker compose up -d
```

または `.env` ファイルで設定：

```
FLASK_ENV=production
```

本番環境では Gunicorn が起動し、マルチプロセスで安定した動作を提供します。

### ログレベルの設定

環境変数 `LOG_LEVEL` でログレベルを制御できます：

```bash
# DEBUGレベルで起動（詳細なログを出力）
LOG_LEVEL=DEBUG docker compose up -d

# INFOレベル（デフォルト）
LOG_LEVEL=INFO docker compose up -d
```

利用可能なログレベル：

- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 一般的な情報メッセージ（デフォルト）
- `WARNING`: 警告メッセージ
- `ERROR`: エラーメッセージ
- `CRITICAL`: 重大なエラー

`.env` ファイルで設定することも可能：

```
LOG_LEVEL=DEBUG
```

## アクセス

### Docker Compose で起動した場合（推奨）

Caddy がリバースプロキシとして 443/80 番ポートを受け、`web`/`mcp` コンテナの 5000 番は
ホストに公開されません。**ポート番号なしの `https://`** でアクセスしてください。

- Web 管理画面: **https://localhost/**
- MCP サービス（サブドメイン方式）: **https://`<identifier>`.lvh.me/mcp**
  （`lvh.me` は常に 127.0.0.1 を指す公開DNSなので、追加設定なしでサブドメインが使えます）

証明書は Caddy が自動生成する自己署名証明書（`tls internal`）です。ブラウザに
「この接続は保護されていません」という警告が出ますが、ローカル開発では想定どおりの動作です。
警告を消したい場合は [スケーリング・コンテナ構成](docs/SCALING.md#https) の手順で
Caddy のローカル CA をOSに信頼させてください。

- デフォルト管理者
  - ID: `admin`
  - パスワード: `admin`

### Docker を使わず `python run.py` で直接起動した場合

Flask 開発サーバーがそのままポート 5000 で起動するので、TLS なしでアクセスします。

- Web 管理画面: http://localhost:5000/
- MCP サービス（サブドメイン方式）: http://`<identifier>`.lvh.me:5000/mcp

**⚠️ セキュリティ警告**

- **本番環境では必ず認証情報を変更してください**
- 環境変数 `ADMIN_USERNAME` と `ADMIN_PASSWORD` で上書き可能です
- デフォルト認証情報はデモ・検証用です（Oracle の scott/tiger のような位置づけ）

**環境変数での認証情報変更：**

```bash
# docker-compose.yml または .env
environment:
  ADMIN_USERNAME: your_secure_username
  ADMIN_PASSWORD: your_secure_password
```

**注意**: 管理画面はパス（`/dashboard` 等）で振り分けられるため、`https://localhost/` ・
`https://lvh.me/` ・`https://admin.lvh.me/` のどのホスト名でアクセスしても同じ管理画面が
表示されます。MCP サービス側だけが、サブドメイン（`<identifier>.lvh.me`）で対象サービスを
区別します。

## セキュリティ機能

### ブルートフォース攻撃対策

管理画面ログインは IP アドレスベースのレート制限機能を備えています：

- **デフォルト設定**: 5 回の失敗で 30 分間ロック
- **ログ記録**: 全ログイン試行（成功/失敗）を記録
- **手動ロック解除**: 管理画面から IP アドレスのロックを解除可能

### 監査ログ機能

すべての管理者操作が自動的に記録されます：

- **ログイン履歴**: ユーザー名、IP アドレス、成功/失敗、タイムスタンプ
- **CRUD 操作履歴**: MCP サービス、アプリ、Capability、アカウント、権限の作成・更新・削除
- **変更差分**: 操作前後の値を JSON 形式で記録
- **CSV エクスポート**: 監査レポート用に CSV 出力可能

**監査ログ API:**

- `GET /api/admin/login-logs` - ログイン履歴取得
- `GET /api/admin/login-logs/export` - ログイン履歴 CSV 出力
- `GET /api/admin/action-logs` - 操作履歴取得
- `GET /api/admin/action-logs/export` - 操作履歴 CSV 出力
- `POST /api/admin/unlock-account` - IP ロック解除
- `GET /api/admin/locked-ips` - ロック中 IP 一覧

### セキュリティ設定

AdminSettings で以下の設定をカスタマイズ可能：

- `login_max_attempts`: ログイン試行上限（デフォルト: 5）
- `login_lock_duration_minutes`: ロック時間（デフォルト: 30 分）
- `audit_log_retention_days`: 監査ログ保持期間（デフォルト: 365 日）

## 管理画面構成

### ログイン画面

- 管理者認証

### サービス管理

- サービス一覧表示
- サービス新規登録 (サブドメイン、共通ヘッダー設定)
- サービス詳細/編集
- Capability 管理

### Capability 管理

- Capability 一覧
- Capability 登録 (API/MCP 選択、URL、ヘッダー、ボディ設定)
- Capability 編集/削除

### ユーザー管理

- ユーザー一覧
- ユーザー登録 (ログイン ID、パスワード)
- ユーザー詳細 (Bearer トークン表示)
- ユーザー情報編集/削除

## MCP クライアント接続

以下は **Docker Compose 起動時 (Caddy 経由、`https://`・ポート番号なし)** のURLです。
Docker を使わず `python run.py` で直接起動した場合は `http://` + `:5000` を使ってください
(例: `http://myservice.lvh.me:5000/mcp`)。自己署名証明書のため、`curl` には `-k`
(証明書検証スキップ) が必要です。

### サブドメインベースのアクセス (推奨)

#### 1. Capabilities 取得 (GET リクエスト)

```bash
# lvh.me ドメインを使用 (ローカル開発用、常に127.0.0.1を指す)
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://myservice.lvh.me/mcp

# または subdomain パラメータを使用
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://localhost/mcp?subdomain=myservice
```

**レスポンス例:**

```json
{
  "capabilities": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather information",
        "inputSchema": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "Parameter: city"
            }
          }
        }
      }
    ]
  },
  "serverInfo": {
    "name": "Weather Service",
    "version": "1.0.0"
  }
}
```

#### 2. Tool 実行 (POST リクエスト)

```bash
# Tool を直接実行
curl -k -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"city": "Tokyo"}}' \
  https://myservice.lvh.me/tools/get_weather

# または MCP プロトコルで実行
curl -k -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {"city": "Tokyo"}
    }
  }' \
  https://myservice.lvh.me/mcp
```

### MCP クライアント設定

#### HTTP 接続 (Dify, Claude Desktop など)

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://myservice.lvh.me/mcp",
      "transport": {
        "type": "http"
      },
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

#### Legacy エンドポイント (後方互換性)

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://localhost/mcp/myservice",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

### stdio 接続

```json
{
  "mcpServers": {
    "my-service": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "mcp_server",
        "python",
        "stdio_server.py",
        "myservice",
        "YOUR_TOKEN"
      ]
    }
  }
}
```

## エンドポイント一覧

### MCP エンドポイント

| エンドポイント                       | メソッド | 説明                                          |
| ------------------------------------ | -------- | --------------------------------------------- |
| `<subdomain>.lvh.me/mcp`             | GET      | ユーザーが使用可能な Capabilities を取得      |
| `<subdomain>.lvh.me/mcp`             | POST     | MCP リクエストを処理 (tools/list, tools/call) |
| `<subdomain>.lvh.me/tools/<tool_id>` | POST     | 特定の Tool を直接実行                        |
| `/mcp/<subdomain>`                   | POST     | Legacy エンドポイント (後方互換性)            |

**注意:** 上記は Docker Compose (Caddy経由) でのURLです（`https://`、ポート番号なし）。
`python run.py` で直接起動した場合は `http://<subdomain>.lvh.me:5000/mcp` のように
ポート5000・`http`を使ってください。`lvh.me` はローカル開発用のドメインで、常に 127.0.0.1
を指します。本番環境では独自ドメインを使用してください。

## データベース構造

- **users**: ユーザー情報、認証情報
- **services**: 登録サービス (サブドメイン、共通ヘッダー)
- **capabilities**: Tool 定義 (API/MCP、URL、ヘッダー、ボディ)
- **user_permissions**: ユーザー ×Capability の権限マッピング
- **mcp_connection_logs**: MCP 接続ログ（監査用）

## 接続ログ

### 標準出力への JSON 構造化ログ

Octopus MCP Proxy は、すべての MCP 接続ログを標準出力（stdout）に JSON 形式で出力します。これにより、任意のコンテナログ収集システムで自動的にログを集約できます。

**対応プラットフォーム：**

- **AWS ECS/Fargate** → CloudWatch Logs
- **Google Cloud Run** → Cloud Logging
- **Azure Container Apps** → Azure Monitor
- **Kubernetes** → kubelet → Fluentd/Fluent Bit → 任意のバックエンド
- **Heroku** → Logplex
- その他、Docker コンテナをサポートするすべてのプラットフォーム

**ログ形式例：**

```json
{
  "timestamp": "2026-01-08T12:34:56.789Z",
  "log_type": "mcp_connection",
  "level": "INFO",
  "mcp_method": "tools/call",
  "mcp_service_id": 7,
  "mcp_service_name": "OpenAI Service",
  "app_id": 43,
  "app_name": "ChatGPT API",
  "capability_id": 215,
  "capability_name": "generate_text",
  "tool_name": "generate_text",
  "account_id": null,
  "account_name": null,
  "status_code": 200,
  "is_success": true,
  "duration_ms": 1234,
  "ip_address": "192.168.1.1",
  "user_agent": "Claude/1.0",
  "access_control": "public",
  "request_id": "abc123",
  "error_code": null,
  "error_message": null,
  "request_body": "{\"prompt\":\"Hello\"}",
  "response_body": "{\"text\":\"Hi there!\"}"
}
```

### 環境変数設定

```bash
# 標準出力ログの有効/無効（デフォルト: true）
MCP_LOG_STDOUT=true
```

### ログ無効化

開発環境でログ出力を無効にする場合：

```bash
MCP_LOG_STDOUT=false docker compose up
```

### クラウドプラットフォームでの活用

**AWS ECS/Fargate:**

```json
{
  "logConfiguration": {
    "logDriver": "awslogs",
    "options": {
      "awslogs-group": "/ecs/accel-mcp",
      "awslogs-region": "ap-northeast-1",
      "awslogs-stream-prefix": "mcp"
    }
  }
}
```

CloudWatch Insights で検索：

```
fields @timestamp, mcp_method, tool_name, duration_ms, is_success
| filter log_type = "mcp_connection"
| filter is_success = false
| sort @timestamp desc
```

**Google Cloud Run:**

自動的に Cloud Logging に送信され、`jsonPayload`フィールドでフィルタリング可能：

```
jsonPayload.log_type="mcp_connection"
jsonPayload.is_success=false
```

**Kubernetes (Fluent Bit):**

```yaml
[FILTER]
    Name parser
    Match *
    Key_Name log
    Parser json

[FILTER]
    Name modify
    Match *
    Condition Key_value_matches log_type mcp_connection
    Add k8s_label_app accel-mcp
```

## 開発

```bash
# ローカルで開発
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### コード品質チェック

プロジェクトでは **Ruff** (リンター・フォーマッター) と **mypy** (型チェッカー) を使用しています。

**すべてのチェックを実行:**

```bash
./run_check.sh
```

このスクリプトは以下を実行します：

- Ruff によるコードスタイルチェック
- Ruff によるフォーマットチェック
- mypy による型チェック

**自動修正とフォーマット:**

```bash
./run_format.sh
```

このスクリプトは以下を実行します：

- Ruff による自動修正
- Ruff によるコードフォーマット（自動整形）

**個別実行:**

```bash
# Ruff リンター
ruff check app/ tests/

# Ruff フォーマッター（チェックのみ）
ruff format app/ tests/ --check

# Ruff フォーマッター（実行）
ruff format app/ tests/

# mypy 型チェック
mypy app/

# 自動修正
ruff check app/ tests/ --fix
```

**設定ファイル:**

- `pyproject.toml` - Ruff と mypy の設定

> **注意:** `check.sh` と `format.sh` は `run_check.sh` と `run_format.sh` にリネームされています。

## ドキュメント

詳細なドキュメントは `docs/` ディレクトリにあります。

| ドキュメント                                                                             | 説明                                                                             |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [クイックスタート](docs/QUICKSTART.md) / [English](docs/en/QUICKSTART.en.md)             | 5 分で MCP サーバーを起動・テストする最短手順                                    |
| [セットアップガイド](docs/SETUP.md) / [English](docs/en/SETUP.en.md)                     | 詳細なセットアップ・起動手順                                                     |
| [MCP エンドポイント詳細](docs/MCP_ENDPOINTS.md) / [English](docs/en/MCP_ENDPOINTS.en.md) | 各 MCP エンドポイントの詳細な使用方法                                            |
| [ディレクトリ構造](docs/STRUCTURE.md) / [English](docs/en/STRUCTURE.en.md)               | MVC パターンに基づくプロジェクト構成の説明                                       |
| [テストガイド](docs/TESTING.md) / [English](docs/en/TESTING.en.md)                       | ユニットテスト・統合テストの実行方法と構成                                       |
| [E2E テスト](docs/E2E_TESTING.md) / [English](docs/en/E2E_TESTING.en.md)                 | Playwright を使った E2E テストの実行方法                                         |
| [データベースマイグレーション](docs/MIGRATION.md) / [English](docs/en/MIGRATION.en.md)   | Flask-Migrate (Alembic) を使ったマイグレーション管理                             |
| [スケーリング・コンテナ構成](docs/SCALING.md) / [English](docs/en/SCALING.en.md)         | コンテナ構成、1台/複数台運用、Redis セッション共有、MCP エンドポイントのスケール |

## このプロジェクトについて

このプロジェクトは **100% バイブコーディング（vibe coding）** で作成されています。
コードはすべて AI とのペアプログラミングによって実装されました。

**使用モデル:**

- Claude Sonnet 4.5 / 4.6
- Claude Opus 4.8
