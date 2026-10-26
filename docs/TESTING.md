[English](en/TESTING.en.md) | 日本語

# MCP Server - Testing Guide

## テスト概要

このプロジェクトでは `pytest` を使用してテストを実行します。Rails の RSpec に似た構造で、モデル、API、ビューの各レイヤーをテストします。

## テスト構造

```
tests/
├── __init__.py                     # テストパッケージ初期化
├── conftest.py                     # pytest設定とフィクスチャ
├── conftest_playwright.py          # Playwright設定
├── README.md                       # テストドキュメント（日本語）
├── README.en.md                    # テストドキュメント（英語）
├── unit/                           # ユニット・統合テスト
│   ├── admin/
│   │   └── test_admin_settings.py  # 管理設定テスト
│   ├── infrastructure/
│   │   ├── test_database_schema.py # DBスキーマテスト
│   │   ├── test_error_responses.py # エラーレスポンステスト
│   │   ├── test_i18n.py            # 国際化テスト
│   │   └── test_timeout_feature.py # タイムアウト機能テスト
│   ├── logging/
│   │   ├── test_connection_logs.py # 接続ログテスト
│   │   └── test_log_search.py      # ログ検索テスト
│   ├── mcp/
│   │   ├── test_capability_integration.py  # Capability統合テスト
│   │   ├── test_capability_testing.py      # Capabilityテスト機能
│   │   ├── test_mcp_protocol.py            # MCPプロトコルテスト
│   │   ├── test_mcp_services.py            # MCPサービステスト
│   │   ├── test_prompt_and_resource_capability.py # プロンプト・リソーステスト
│   │   └── test_stdio_mcp.py               # stdio MCPテスト
│   ├── security/
│   │   ├── test_permissions.py     # 権限テスト
│   │   └── test_security.py        # セキュリティテスト
│   ├── templates/
│   │   ├── test_prompt_templates.py        # プロンプトテンプレートテスト
│   │   ├── test_template_import_export.py  # テンプレートインポート/エクスポート
│   │   └── test_variables.py               # 変数テスト
│   └── ui/
│       ├── test_javascript_static.py  # JavaScript静的ファイルテスト
│       └── test_modal_and_sync.py     # モーダル・同期テスト
├── e2e/                            # E2Eテスト（Playwright）
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_login.py               # ログインページ
│   ├── test_dashboard.py           # ダッシュボード
│   ├── test_javascript_errors.py   # JavaScriptエラーチェック
│   ├── accounts/
│   │   └── test_accounts.py        # アカウント管理
│   ├── capabilities/
│   │   ├── test_capabilities.py
│   │   └── test_capabilities_page.py
│   ├── mcp_services/
│   │   └── test_mcp_services.py    # MCPサービス管理
│   ├── mcp_templates/
│   │   └── test_templates.py       # テンプレート管理
│   ├── security/
│   │   └── test_security.py        # セキュリティE2Eテスト
│   ├── services/
│   │   └── test_services.py        # サービス管理
│   └── variables/
│       └── test_variables.py       # 変数管理
└── reports/                        # テストレポート（自動生成）
```

## セットアップ

### 1. テスト用パッケージのインストール

```bash
pip install -r requirements.txt
```

または個別にインストール:

```bash
pip install pytest pytest-flask pytest-cov pytest-mock pytest-playwright
```

### 2. Playwright ブラウザのインストール（E2E テスト用）

```bash
./setup_playwright.sh
```

または

```bash
python -m playwright install
```

### 3. Docker 環境でのテスト

```bash
docker compose exec web bash
pytest
```

## テストの実行方法

### unit / integration テストを実行

```bash
pytest
```

または（カバレッジ付き、`htmlcov/` にレポートを出力）

```bash
./run_tests.sh
```

引数なしの `pytest` と `run_tests.sh` は `tests/unit` と `tests/integration` だけを実行します。
E2E テストはサーバーとブラウザが必要なため、後述の手順で別に実行してください。

### 特定のファイルのテストを実行

```bash
pytest tests/unit/mcp/test_mcp_protocol.py
```

### 特定のクラスのテストを実行

```bash
pytest tests/unit/mcp/test_mcp_protocol.py::TestMcpProtocol
```

### 特定のテストケースを実行

```bash
pytest tests/unit/mcp/test_mcp_protocol.py::TestMcpProtocol::test_tools_list_public_access
```

### 詳細表示で実行

```bash
pytest -v
```

### カバレッジ付きで実行

```bash
pytest --cov=app --cov-report=term-missing
```

### HTML カバレッジレポート生成

```bash
pytest --cov=app --cov-report=html
```

レポートは `htmlcov/index.html` に生成されます。

## テストの種類

### 1. MCPプロトコルテスト (`unit/mcp/`)

MCPプロトコルの各エンドポイント、Capabilityの登録・実行、stdio接続などをテストします。

```python
def test_tools_list_public_access(self, client, db):
    """公開サービスのtools/listを認証なしで取得できる"""
    response = client.post(
        '/mcp',
        json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'},
        headers={'X-Subdomain': 'myservice'}
    )
    assert response.status_code == 200
```

### 2. セキュリティテスト (`unit/security/`)

権限管理、認証、ブルートフォース対策などをテストします。

### 3. テンプレートテスト (`unit/templates/`)

ビルトインテンプレートのインポート/エクスポート、変数機能、プロンプトテンプレートをテストします。

### 4. ログテスト (`unit/logging/`)

MCP接続ログの記録、検索、CSVエクスポート機能をテストします。

### 5. インフラストラクチャテスト (`unit/infrastructure/`)

DBスキーマ、エラーレスポンス、i18n、タイムアウト機能などをテストします。

### 6. E2E テスト (`e2e/`) - Playwright

実際のブラウザを使用したエンドツーエンドテスト（Capybara相当）。

**ファイル構成:**

- `e2e/test_login.py` - ログイン/ログアウト
- `e2e/test_dashboard.py` - ダッシュボード
- `e2e/test_javascript_errors.py` - JavaScriptエラー検出
- `e2e/services/test_services.py` - App 管理（作成・編集・接続テスト）
- `e2e/capabilities/test_capabilities.py` - Capabilities 管理
- `e2e/capabilities/test_capability_schema_roundtrip.py` - 新規作成と編集でスキーマが一致することの確認
- `e2e/accounts/test_accounts.py` - アカウント管理
- `e2e/mcp_services/test_mcp_services.py` - MCPサービス管理
- `e2e/mcp_templates/test_templates.py` - テンプレート管理
- `e2e/security/test_security.py` - セキュリティE2Eテスト
- `e2e/variables/test_variables.py` - 変数管理

```python
def test_login_with_valid_credentials(self, page: Page):
    """正しい認証情報でログインできる"""
    page.goto("http://localhost:5000/login")

    page.fill('input[name="username"]', "accel")
    page.fill('input[name="password"]', "universe")
    page.click('button[type="submit"]')

    page.wait_for_url("http://localhost:5000/")
    expect(page).to_have_url("http://localhost:5000/")
```

**E2E テストの実行方法:**

```bash
# 推奨: Docker で実行（ブラウザ入りのイメージを使用）
docker compose up -d
docker compose --profile e2e run --rm e2e

# ローカルで実行する場合（サーバーを起動し、Playwright のブラウザを導入済みであること）
pytest tests/e2e/

# 特定のページのテスト実行
pytest tests/e2e/test_login.py
pytest tests/e2e/services/test_services.py
pytest tests/e2e/mcp_templates/test_templates.py

# マーカーで実行（パスの指定が必要）
pytest tests/e2e/ -m e2e

# ヘッドレスモード無効（ブラウザを表示）
pytest tests/e2e/ --headed

# 特定のブラウザで実行
pytest tests/e2e/ --browser chromium
pytest tests/e2e/ --browser firefox
pytest tests/e2e/ --browser webkit
```

## フィクスチャ

テストで使用できる主なフィクスチャ:

**ユニット/API テスト用:**

- `app` - Flask アプリケーション
- `db` - テスト用データベース
- `client` - テストクライアント（未認証）
- `auth_client` - 認証済みテストクライアント
- `sample_service` - サンプルサービス
- `sample_capability` - サンプル Capability
- `sample_account` - サンプル接続アカウント
- `sample_template` - サンプルテンプレート

**E2E テスト用（Playwright）:**

- `page` - Playwright ページオブジェクト
- `browser` - ブラウザインスタンス
- `context` - ブラウザコンテキスト

使用例:

```python
def test_something(self, auth_client, sample_service):
    """フィクスチャを使用したテスト"""
    response = auth_client.get(f'/services/{sample_service.id}')
    assert response.status_code == 200
```

```python
def test_e2e_example(self, page: Page):
    """E2Eテストの例"""
    page.goto("http://localhost:5000/login")
    page.fill('input[name="username"]', "accel")
    page.click('button[type="submit"]')
```

## テストデータベース

テストは SQLite インメモリデータベースを使用します。各テスト実行後に自動的にクリーンアップされます。

```python
class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## CI/CD 統合

GitHub Actions などの CI 環境でテストを実行する例:

```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    python -m playwright install

- name: Run unit tests
  run: |
    pytest tests/unit/ --cov=app --cov-report=xml

- name: Run E2E tests
  run: |
    docker compose up -d
    pytest tests/e2e/
    docker compose down

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## トラブルシューティング

### インポートエラー

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### データベース接続エラー

テスト用のインメモリ DB を使用しているため、MySQL 接続は不要です。

### 認証エラー

`auth_client` フィクスチャを使用してください。これは自動的にログイン済みの状態です。

### E2E テストでサーバーに接続できない

サーバーが起動していることを確認してください:

```bash
docker compose up
```

### Playwright ブラウザがインストールされていない

```bash
python -m playwright install
```

## Playwright デバッグ

### ブラウザを表示して実行

```bash
pytest tests/e2e/ --headed
```

### スローモーション実行

`conftest_playwright.py` で `slow_mo` を設定:

```python
"slow_mo": 1000,  # 1秒ずつ遅らせる
```

### スクリーンショット撮影

テスト内で:

```python
page.screenshot(path="debug.png")
```

### トレース記録

```python
context.tracing.start(screenshots=True, snapshots=True)
# テスト実行
context.tracing.stop(path="trace.zip")
```

トレースファイルは Playwright Inspector で確認:

```bash
playwright show-trace trace.zip
```

## ベストプラクティス

1. **テストは独立させる**: 各テストは他のテストに依存しない
2. **AAA パターン**: Arrange（準備）, Act（実行）, Assert（検証）
3. **明確な名前**: テスト名は何をテストしているか明確に
4. **適切なフィクスチャ**: 共通のセットアップはフィクスチャに
5. **カバレッジ目標**: 80%以上を目指す
6. **E2E テストは最小限に**: 実行時間が長いため、重要なユーザーフローのみ

## 参考リンク

- [pytest 公式ドキュメント](https://docs.pytest.org/)
- [pytest-flask](https://pytest-flask.readthedocs.io/)
- [Flask Testing](https://flask.palletsprojects.com/en/3.0.x/testing/)
- [Playwright for Python](https://playwright.dev/python/)
- [pytest-playwright](https://github.com/microsoft/playwright-pytest)
