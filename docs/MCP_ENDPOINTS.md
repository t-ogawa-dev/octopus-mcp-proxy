[English](en/MCP_ENDPOINTS.en.md) | 日本語

# MCP エンドポイント詳細ガイド

このドキュメントでは、MCP サーバーの各エンドポイントの詳細な使用方法を説明します。

## 概要

この MCP サーバーは 2 つの主要なエンドポイントを提供します:

1. **GET /mcp** - Capabilities 一覧取得
2. **POST /mcp** - MCP プロトコルリクエスト処理

Tool の実行は `POST /mcp` の `tools/call` で行います。旧エンドポイント `POST /tools/<tool_id>` と `POST /mcp/<subdomain>` は削除されました。

すべてのエンドポイントはサブドメインベースのルーティングをサポートしています。
以下は **Docker Compose 起動時 (Caddy 経由、`https://`・ポート番号なし)** のURLです。
Docker を使わず `python run.py` で直接起動した場合は `http://` + `:5000` を使ってください。
自己署名証明書のため `curl` には `-k` (証明書検証スキップ) が必要です。

管理画面は `https://localhost/`（または `https://lvh.me/`）でアクセス可能です。

## サブドメインの指定方法

### 方法 1: lvh.me ドメイン (推奨)

`lvh.me` は常に 127.0.0.1 を指すため、ローカル開発で便利です。

```
https://<subdomain>.lvh.me/mcp
```

**例:**

- `https://weather.lvh.me/mcp` - weather サービスの MCP エンドポイント
- `https://myapi.lvh.me/mcp` - myapi サービスの MCP エンドポイント
- `https://localhost/` - 管理画面（パスで振り分けられるため、ホスト名は問わない)

### 方法 2: クエリパラメータ

```
https://localhost/mcp?subdomain=<subdomain>
```

### 方法 3: カスタムヘッダー

```bash
curl -k -H "X-Subdomain: myservice" https://localhost/mcp
```

## 認証

すべてのリクエストには `Authorization` ヘッダーが必要です:

```
Authorization: Bearer <USER_BEARER_TOKEN>
```

ユーザーの Bearer トークンは、Web 管理画面のユーザー詳細ページで確認できます。

---

## 1. GET /mcp - Capabilities 取得

ユーザーが使用可能な Tool の一覧を取得します。

### リクエスト

```bash
curl -k -H "Authorization: Bearer abc123..." \
  https://myservice.lvh.me/mcp
```

### レスポンス

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
              "description": "Parameter: city",
              "default": "Tokyo"
            },
            "units": {
              "type": "string",
              "description": "Parameter: units",
              "default": "metric"
            }
          },
          "required": []
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

### 挙動

1. サブドメインからサービスを特定
2. Bearer トークンからユーザーを特定
3. ユーザーが権限を持つ、有効な Tool のみを返却 (`tools/list` と同じ結果)
4. 各 Tool の InputSchema は、登録された Body パラメータから自動生成
5. URL・ヘッダーなどの内部設定は返却しない

---

## 2. POST /mcp - MCP プロトコルリクエスト

標準的な MCP プロトコルに従ってリクエストを処理します。

`2026-07-28` のステートレスリクエストでは、`initialize` や `Mcp-Session-Id` なしで
リクエストを送信できます。`server/discover` で対応プロトコルを確認できます。
`2024-11-05` の旧仕様クライアントによる `initialize` と `Mcp-Session-Id` を使った
セッション方式も後方互換として利用できます。

### 対応メソッド

- `server/discover` - 対応プロトコルバージョンの取得
- `initialize` - 旧仕様クライアント用のセッション初期化
- `tools/list` - Tool 一覧取得 (GET /mcp と同等)
- `tools/call` - Tool 実行

### 2.1 server/discover

#### リクエスト

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"server/discover"}' \
  https://myservice.lvh.me/mcp
```

#### レスポンス

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersions": ["2026-07-28", "2024-11-05"]
  }
}
```

### 2.2 tools/list

#### リクエスト

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' \
  https://myservice.lvh.me/mcp
```

#### レスポンス

```json
{
  "jsonrpc": "2.0",
  "result": {
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
  }
}
```

### 2.3 tools/call

#### リクエスト

```bash
curl -k -X POST \
  -H "Authorization: Bearer abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {
        "city": "Tokyo"
      }
    }
  }' \
  https://myservice.lvh.me/mcp
```

#### レスポンス (成功時)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": {\"temperature\": 25, \"condition\": \"sunny\"}}"
      }
    ]
  }
}
```

#### レスポンス (権限エラー)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32000,
    "message": "Permission denied for tool: get_weather"
  }
}
```

---

## エラーコード一覧

| コード | 説明                                  |
| ------ | ------------------------------------- |
| -32700 | Parse error - 無効な JSON             |
| -32600 | Invalid Request - サブドメイン未指定  |
| -32601 | Method not found - 未対応のメソッド   |
| -32602 | Invalid params - Tool が見つからない  |
| -32603 | Internal error - 実行エラー           |
| -32000 | Server error - 認証エラー、権限エラー |
| -32001 | Server error - サービス未発見         |

---

## 使用例

### 例 1: Dify での設定

```json
{
  "mcp_servers": {
    "weather_service": {
      "url": "https://weather.lvh.me/mcp",
      "auth": {
        "type": "bearer",
        "token": "YOUR_BEARER_TOKEN"
      }
    }
  }
}
```

### 例 2: Claude Desktop での設定

```json
{
  "mcpServers": {
    "weather": {
      "url": "https://weather.lvh.me/mcp",
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

### 例 3: Python スクリプトでの利用

```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_BEARER_TOKEN',
    'Content-Type': 'application/json'
}

# Capabilities取得
response = requests.get(
    'https://myservice.lvh.me/mcp',
    headers=headers
)
capabilities = response.json()
print(capabilities)

# Tool実行 (MCP プロトコルの tools/call)
response = requests.post(
    'https://myservice.lvh.me/mcp',
    headers=headers,
    json={
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {'name': 'get_weather', 'arguments': {'city': 'Tokyo'}},
    }
)
result = response.json()
print(result)
```

### 例 4: cURL での完全なワークフロー

```bash
# 1. Capabilitiesを取得
curl -k -H "Authorization: Bearer YOUR_TOKEN" \
  https://myservice.lvh.me/mcp

# 2. MCPプロトコルでToolを実行
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

---

## 実装の流れ

### GET /mcp または POST /mcp (tools/list)

```
1. リクエスト受信
   ↓
2. サブドメインを抽出 (lvh.me, クエリパラメータ, ヘッダー)
   ↓
3. Bearerトークンを検証
   ↓
4. サブドメインからServiceを検索
   ↓
5. ユーザーIDとService IDから権限のあるCapabilityを取得
   ↓
6. Capabilityリストを整形して返却
```

### POST /mcp (tools/call)

```
1. リクエスト受信
   ↓
2. サブドメインを抽出
   ↓
3. Bearerトークンを検証
   ↓
4. サブドメインからServiceを検索
   ↓
5. params.nameからCapabilityを検索
   ↓
6. ユーザーの権限を確認
   ↓
7. 権限あり → Capability実行
   権限なし → JSON-RPCエラーレスポンス
   ↓
8. JSON-RPC形式で結果を返却
```

---

## トラブルシューティング

### サブドメインが認識されない

**問題:** lvh.me でアクセスしてもサブドメインが認識されない

**解決策:**

1. DNS 設定を確認 (`ping myservice.lvh.me` が 127.0.0.1 を返すか)
2. 代わりにクエリパラメータを使用: `?subdomain=myservice`
3. Docker Compose 経由なら `https://`・ポート番号なし、`python run.py` で直接起動した場合は
   `http://` + ポート5000 を使っているか確認 (`https://myservice.lvh.me/mcp` /
   `http://myservice.lvh.me:5000/mcp`)
4. `curl` で証明書エラーが出る場合は `-k` を付ける(自己署名証明書のため)

### 認証エラー

**問題:** `Invalid bearer token` エラー

**解決策:**

1. Bearer トークンを確認 (Web 管理画面 > ユーザー詳細)
2. `Authorization: Bearer ` の形式を確認 (スペース含む)
3. トークンを再発行

### 権限エラー

**問題:** `Permission denied for tool: xxx`

**解決策:**

1. Web 管理画面でユーザーの権限を確認
2. ユーザー詳細 > 権限管理 で該当 Capability を追加

### Tool 未発見エラー

**問題:** `Tool not found: xxx`

**解決策:**

1. Capability が正しく登録されているか確認
2. Tool 名のスペルミスがないか確認
3. 正しいサービス(サブドメイン)にアクセスしているか確認
