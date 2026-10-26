[English](en/E2E_TESTING.en.md) | 日本語

# E2E Testing with Playwright

このプロジェクトでは、E2E テスト用に専用のコンテナを使用しています。

## アーキテクチャ

- **web**: 本番アプリケーションコンテナ（Playwright 不要）
- **e2e**: E2E テスト専用コンテナ（Playwright + Chromium 含む）
- **db**: MySQL データベース

## E2E テストの実行方法

E2E テストの接続先は `DOCKER_ENV=1` の場合 `http://web:5000`、ローカル実行時は
`FLASK_PORT` または `PORT` を使用します。ログイン情報は `ADMIN_USERNAME` と
`ADMIN_PASSWORD` で上書きでき、既定値は `admin` / `admin` です。

### 方法 1: 専用コンテナで実行（推奨）

```bash
# E2Eコンテナを起動してテスト実行
docker compose --profile e2e run --rm e2e

# 特定のテストファイルのみ実行
docker compose --profile e2e run --rm e2e python -m pytest tests/e2e/test_login.py -v

# 全テスト（ユニット+統合+E2E）を実行
docker compose --profile e2e run --rm e2e python -m pytest tests/ -v
```

### 方法 2: web コンテナで実行（開発時）

web コンテナでも E2E 以外のテストは実行可能です:

```bash
# ユニット・統合・APIテストのみ
docker compose exec web python -m pytest tests/test_models.py tests/test_integration.py tests/test_api.py tests/test_views.py -v
```

## なぜ分離するのか？

1. **本番環境の軽量化**: web コンテナには Playwright や Chromium が含まれないため、イメージサイズが小さくなります
2. **セキュリティ**: 本番環境に不要なブラウザバイナリを含めません
3. **保守性**: テスト環境と本番環境を明確に分離できます
4. **Rails のベストプラクティス**: Rails でも同様に chromium コンテナを分離しています

## 技術選択について

### なぜ Selenium Grid ではなく Playwright 内蔵ブラウザを使うのか？

Rails では`seleniarm/standalone-chromium`のような Selenium Grid 用のコンテナを使いますが、
このプロジェクトでは Playwright 内蔵の Chromium を使用しています。

**理由:**

- **Playwright の設計思想**: Playwright は独自のブラウザバイナリを管理し、Selenium Grid とは互換性がありません
- **シンプルさ**: 外部ブラウザコンテナとの通信設定が不要
- **軽量**: E2E コンテナのみで完結し、追加のブラウザコンテナが不要
- **速度**: ローカルブラウザの方が通信オーバーヘッドがない

**Selenium Grid を使いたい場合:**

- Playwright の代わりに Selenium WebDriver を使用してください
- または、複数ブラウザでの並列テストが必要な場合のみ Playwright の実験的な Grid サポートを検討

**現在のアーキテクチャの利点:**

```
e2e コンテナ = Python + pytest + Playwright + Chromium (all-in-one)
```

- Dockerfile.e2e のみで完結
- 設定がシンプル
- 本番用 web コンテナは完全にクリーン

## Docker Compose Profiles

`profiles: [e2e]`を使用することで、通常の`docker compose up`では起動せず、
明示的に`--profile e2e`を指定した時のみ E2E コンテナが起動します。

```bash
# 通常起動（webとdbのみ）
docker compose up -d

# E2Eテスト時のみ起動
docker compose --profile e2e up -d
```
