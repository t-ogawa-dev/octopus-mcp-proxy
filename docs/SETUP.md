[English](en/SETUP.en.md) | 日本語

# MCP Server セットアップガイド

## 起動手順

### 1. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、必要に応じて編集してください。

```bash
cp .env.example .env
```

### 2. Docker コンテナの起動

```bash
docker compose up -d
```

初回起動時は、イメージのビルドとデータベースの初期化が行われます。

### 3. ログの確認

```bash
docker compose logs -f web
```

起動が完了すると、デフォルト管理者の Bearer トークンがログに表示されます。

### 4. Web 管理画面へアクセス

ブラウザで **https://localhost/** を開きます(ポート番号なし)。Caddy がリバースプロキシ
として 80/443 番を受け、アプリ本体のポート 5000 はホストに公開されないため、`:5000` では
アクセスできません。自己署名証明書のため「保護されていない通信」の警告が出ますが、
「詳細」→「アクセスする」で進めます(警告を消したい場合は
[スケーリング・コンテナ構成](SCALING.md#https) 参照)。

Docker を使わず `python run.py` で直接起動した場合は `http://localhost:5000/` を使います。

**デフォルト管理者アカウント:**

- ログイン ID: `admin`
- パスワード: `admin`

**注意**: 管理画面はパスで振り分けられるため、`https://localhost/` ・`https://lvh.me/` ・
`https://admin.lvh.me/` のどれでアクセスしても同じ画面が表示されます。MCP サービスのみ
サブドメインで区別されます。

## 基本的な使い方

### 1. サービスの登録

1. ダッシュボードから「サービス管理」をクリック
2. 「新規サービス登録」をクリック
3. 以下を入力:
   - サービス名: 任意の名前
   - サブドメイン: MCP クライアントからの接続パス (例: `myservice`)
   - 共通ヘッダー: 全ての Capability で使用するヘッダー (JSON 形式)

**サブドメインの例:**

```
サブドメイン: myservice
→ MCPエンドポイント: https://myservice.lvh.me/mcp   (Docker Compose, Caddy経由)
→ MCPエンドポイント: http://myservice.lvh.me:5000/mcp  (python run.py で直接起動した場合)
```

### 2. Capability の登録

1. サービス詳細画面から「Capabilities 管理」をクリック
2. 「新規 Capability 登録」をクリック
3. 以下を入力:
   - Capability 名: MCP Tool として表示される名前
   - 接続タイプ: API または MCP
   - 接続先 URL: 中継先の API/MCP サーバーの URL
   - ヘッダーパラメータ: 個別のヘッダー設定
   - Body パラメータ: デフォルトのパラメータ

**API Capability の例:**

```
Capability名: get_weather
接続タイプ: API
接続先URL: https://api.weather.com/v1/current
ヘッダーパラメータ:
  X-API-Key: your-api-key
Bodyパラメータ:
  units: metric
```

**MCP Capability の例:**

```
Capability名: search_database
接続タイプ: MCP
接続先URL: http://other-mcp-server:5000/mcp/db
```

### 3. ユーザーの登録

1. ダッシュボードから「ユーザー管理」をクリック
2. 「新規ユーザー登録」をクリック
3. ログイン ID、パスワードを入力して登録
4. 登録後、ユーザー詳細画面で Bearer トークンを確認

### 4. 権限の設定

1. ユーザー詳細画面で「権限を追加」をクリック
2. サービスと Capability を選択
3. 追加をクリック

これで、そのユーザーは指定した Capability を使用できるようになります。

## MCP クライアントからの接続

以下は **Docker Compose 起動時 (Caddy 経由、`https://`・ポート番号なし)** のURLです。
Docker を使わず `python run.py` で直接起動した場合は `http://` + `:5000` を使ってください。

### サブドメインベースのアクセス (推奨)

#### lvh.me ドメインを使用

`lvh.me` は常に 127.0.0.1 を指す、ローカル開発用の公開ドメインです。

```bash
# Capabilities取得 (自己署名証明書のため -k が必要)
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://myservice.lvh.me/mcp

# Tool実行
curl -k -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_weather", "arguments": {"param": "value"}}}' \
  https://myservice.lvh.me/mcp
```

#### クエリパラメータを使用

```bash
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://localhost/mcp?subdomain=myservice
```

### MCP クライアント設定例

#### Dify

```json
{
  "mcp_servers": {
    "my_service": {
      "url": "https://myservice.lvh.me/mcp",
      "auth": {
        "type": "bearer",
        "token": "YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

#### Claude Desktop

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://myservice.lvh.me/mcp",
      "transport": {
        "type": "http"
      },
      "headers": {
        "Authorization": "Bearer YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

### Legacy エンドポイント (後方互換性)

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://localhost/mcp/myservice",
      "headers": {
        "Authorization": "Bearer YOUR_BEARER_TOKEN"
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
        "<ユーザーのBearerトークン>"
      ]
    }
  }
}
```

## 使用例

### 1. 外部 API の中継

天気 API を MCP 経由で利用する例:

1. サービス登録:
   - 名前: Weather Service
   - サブドメイン: weather

2. Capability 登録:
   - 名前: get_current_weather
   - タイプ: API
   - URL: https://api.openweathermap.org/data/2.5/weather
   - ヘッダー: `appid: YOUR_API_KEY`
   - Body パラメータ: `units: metric`

3. ユーザーに権限付与

4. MCP クライアントから:

```
User: 東京の天気を教えて
AI: (get_current_weather ツールを使用して天気情報を取得)
```

### 2. 複数 MCP サーバーの統合

データベース MCP サーバーとファイルシステム MCP サーバーを統合する例:

1. サービス登録: Integration Hub
2. Capability 登録:
   - database_query (MCP, http://db-mcp:5000/mcp/db)
   - file_read (MCP, http://fs-mcp:5002/mcp/files)
3. ユーザーごとに必要な Capability のみ権限付与

## トラブルシューティング

### データベース接続エラー

```bash
# MySQLコンテナのログを確認
docker compose logs db

# データベースが起動するまで待機
docker compose restart web
```

### ポート競合

ホストに公開されているのは `caddy` サービスの 80/443 番のみです(`web`/`mcp` の 5000 番は
内部専用)。80/443 が他のプロセスと競合する場合は `compose.yaml` の `caddy` サービスの
`ports` を変更してください:

```yaml
ports:
  - "8080:80"
  - "8443:443"
```

### `https://localhost/` で証明書の警告が出る

Caddy が自動生成する自己署名証明書のため、ローカル開発では想定どおりの動作です。
[スケーリング・コンテナ構成](SCALING.md#https) を参照してください。

### トークンが無効

ユーザー詳細画面で「トークン再発行」をクリックして新しいトークンを発行してください。

## セキュリティ

### 本番環境での設定

1. **SECRET_KEY の変更**

   ```bash
   # .envファイル
   SECRET_KEY=ランダムな長い文字列
   ```

2. **管理者パスワードの変更**
   - ログイン後、ユーザー詳細画面でパスワードを変更

3. **HTTPS の使用**
   - リバースプロキシ (Nginx, Traefik) で SSL/TLS 終端

4. **データベースパスワードの変更**
   - `compose.yaml`の MYSQL_PASSWORD 等を変更

## データのバックアップ

```bash
# データベースのバックアップ
docker compose exec db mysqldump -u mcpuser -pmcppassword mcpdb > backup.sql

# データベースのリストア
docker compose exec -T db mysql -u mcpuser -pmcppassword mcpdb < backup.sql
```

## 開発モード

ローカルで開発する場合:

```bash
# 仮想環境の作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発サーバーの起動
export DATABASE_URL=mysql+pymysql://mcpuser:mcppassword@localhost:3306/mcpdb
python run.py
```

## API リファレンス

### サービス API

- `GET /api/services` - サービス一覧
- `POST /api/services` - サービス作成
- `GET /api/services/{id}` - サービス詳細
- `PUT /api/services/{id}` - サービス更新
- `DELETE /api/services/{id}` - サービス削除

### Capability API

- `GET /api/services/{id}/capabilities` - Capability 一覧
- `POST /api/services/{id}/capabilities` - Capability 作成
- `GET /api/capabilities/{id}` - Capability 詳細
- `PUT /api/capabilities/{id}` - Capability 更新
- `DELETE /api/capabilities/{id}` - Capability 削除

### ユーザー API

- `GET /api/users` - ユーザー一覧
- `POST /api/users` - ユーザー作成
- `GET /api/users/{id}` - ユーザー詳細
- `PUT /api/users/{id}` - ユーザー更新
- `DELETE /api/users/{id}` - ユーザー削除
- `POST /api/users/{id}/regenerate_token` - トークン再発行

### 権限 API

- `GET /api/users/{id}/permissions` - ユーザー権限一覧
- `POST /api/users/{id}/permissions` - 権限追加
- `DELETE /api/permissions/{id}` - 権限削除

### MCP API

- `POST /mcp` (サブドメイン指定) / `POST /{identifier}/mcp` - MCP リクエスト処理
  - Authorization: Bearer {token}
  - Content-Type: application/json
