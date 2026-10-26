[English](en/QUICKSTART.en.md) | 日本語

# クイックスタート - 5 分で MCP サーバーを試す

このガイドでは、MCP サーバーを起動してテストするまでの最短手順を説明します。

## 1. サーバー起動 (1 分)

```bash
docker compose up -d
```

起動を待つ:

```bash
docker compose logs -f web
```

`Default admin user created` が表示されたら起動完了です。

## 2. 管理画面でログイン (1 分)

1. ブラウザで **https://localhost/** を開く（ポート番号なし。自己署名証明書の警告が出るので
   「詳細」→「アクセスする」で進む。Caddy がリバースプロキシをするため、ポート 5000 は
   ホストには公開されていない）
2. ログイン:

- ID: `admin`
- パスワード: `admin`

## 3. テストサービスを作成 (2 分)

### 3.1 サービス登録

1. ダッシュボード → 「サービス管理」
2. 「新規サービス登録」をクリック
3. 入力:
   - **サービス名**: Weather Service
   - **サブドメイン**: weather
   - **説明**: Test weather service
4. 「登録」をクリック

### 3.2 Capability 登録

1. 作成したサービスをクリック
2. 「Capabilities 管理」をクリック
3. 「新規 Capability 登録」をクリック
4. 入力:
   - **Capability 名**: echo_test
   - **接続タイプ**: API
   - **接続先 URL**: https://httpbin.org/post
   - **説明**: Simple echo test
   - **Body パラメータ**:
     ```
     message: Hello
     ```
5. 「登録」をクリック

### 3.3 管理者に権限付与

1. ダッシュボード → 「ユーザー管理」
2. 「管理者」をクリック
3. 「権限を追加」をクリック
4. サービス: Weather Service
5. Capability: echo_test
6. 「追加」をクリック

### 3.4 Bearer トークン取得

同じユーザー詳細画面で、**Bearer トークン**をコピーします。

## 4. MCP エンドポイントをテスト (1 分)

### 4.1 Capabilities 取得

```bash
# TOKENを置き換えてください
TOKEN="YOUR_BEARER_TOKEN_HERE"

curl -k -H "Authorization: Bearer $TOKEN" \
  https://weather.lvh.me/mcp
```

**期待される出力:**

```json
{
  "capabilities": {
    "tools": [
      {
        "name": "echo_test",
        "description": "Simple echo test",
        "inputSchema": {
          "type": "object",
          "properties": {
            "message": {
              "type": "string",
              "description": "Parameter: message",
              "default": "Hello"
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

### 4.2 Tool 実行

```bash
curl -k -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "echo_test", "arguments": {"message": "Test from MCP"}}}' \
  https://weather.lvh.me/mcp
```

**期待される出力:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"status_code\": 200, \"data\": {...}}"
      }
    ],
    "isError": false
  }
}
```

## 完了! 🎉

これで以下ができるようになりました:

✅ MCP サーバーの起動  
✅ Web 管理画面からサービス・Capability・権限の管理  
✅ サブドメインベースの MCP エンドポイントへのアクセス  
✅ Tool の実行とレスポンスの確認

## 次のステップ

### 実際の API を統合する

1. Web 管理画面で新しい Capability を作成
2. 実際の API URL (OpenWeather, GitHub, など) を設定
3. API Key をヘッダーパラメータに設定
4. ユーザーに権限を付与
5. MCP クライアント (Dify, Claude Desktop) から利用

### 複数のサービスを管理

1. 各 API ごとにサービスを作成
2. サブドメインで分離 (weather, github, database, etc.)
3. ユーザーごとに異なる権限を設定

### MCP サーバーの中継

1. 他の MCP サーバーを Capability として登録
2. タイプを「MCP」に設定
3. 複数の MCP サーバーを 1 つに統合

## トラブルシューティング

### lvh.me が動作しない

代わりに以下を使用:

```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  https://localhost/mcp?subdomain=weather
```

### `https://localhost/` で証明書の警告が出る

Caddy が自動生成する自己署名証明書のため、ローカル開発では想定どおりの動作です。
ブラウザの警告画面で「詳細」→「アクセスする」と進めば問題なく使えます。
警告を消したい場合は [スケーリング・コンテナ構成](SCALING.md#https) を参照してください。

### Docker を使わず直接 `python run.py` で起動した場合

ポート 5000・`http`（TLSなし）でアクセスしてください:
`http://localhost:5000/` 、`http://weather.lvh.me:5000/mcp` のように読み替えます。

### 権限エラーが出る

1. ユーザー詳細画面で権限が正しく設定されているか確認
2. Capability 名が正しいか確認
3. サブドメインが正しいか確認

### データベースエラー

```bash
# コンテナを再起動
docker compose restart

# または完全に再ビルド
docker compose down
docker compose up -d --build
```

## その他のドキュメント

- **詳細な使い方**: `SETUP.md`
- **MCP エンドポイント詳細**: `MCP_ENDPOINTS.md`
- **プロジェクト概要**: `README.md`
