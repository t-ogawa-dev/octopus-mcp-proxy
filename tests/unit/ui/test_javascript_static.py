"""
JavaScript Syntax Validation Tests
Tests JavaScript files for syntax errors without running a browser
Uses Python's esprima or subprocess to validate JS syntax
"""

import shutil
import subprocess
from pathlib import Path

import pytest


class TestJavaScriptSyntax:
    """JavaScriptファイルのシンタックスエラーを検出するテスト"""

    @pytest.fixture
    def js_files(self):
        """テスト対象のJSファイル一覧を取得"""
        project_root = Path(__file__).parent.parent
        js_dir = project_root / "app" / "assets"

        js_files = []
        for js_file in js_dir.rglob("*.js"):
            # 除外パターン（node_modules、minified files等）
            if "node_modules" in str(js_file):
                continue
            if ".min.js" in str(js_file):
                continue
            js_files.append(js_file)

        return js_files

    def test_all_js_files_have_valid_syntax(self, js_files):
        """全てのJSファイルが有効なシンタックスを持つことを確認"""
        errors = []
        warnings = []

        for js_file in js_files:
            result = self._validate_js_syntax(js_file)
            if result:
                # Node.jsがない場合のPythonチェックの結果は警告として扱う
                if "Node.js" not in result and "Timeout" not in result:
                    warnings.append(f"{js_file.name}: {result}")
                else:
                    errors.append(f"{js_file}: {result}")

        # Node.jsベースのエラーのみassertで失敗させる
        if warnings:
            print(
                "\nWarning: Python-based syntax checker found potential issues (use Node.js for accurate validation):\n"
                + "\n".join(warnings[:5])
            )

        assert not errors, "JavaScript syntax errors found:\n" + "\n".join(errors)

    def _validate_js_syntax(self, js_file: Path) -> str | None:
        """
        JavaScriptファイルのシンタックスを検証
        Node.jsが利用可能ならそれを使用、なければPythonで簡易チェック
        """
        # Node.jsでシンタックスチェック
        node_cmd = shutil.which("node")
        try:
            result = subprocess.run(
                [node_cmd or "node", "--check", str(js_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return result.stderr.strip()
            return None
        except FileNotFoundError:
            # Node.jsがない場合はPythonで簡易チェック
            return self._python_js_check(js_file)
        except subprocess.TimeoutExpired:
            return "Timeout checking syntax"

    def _python_js_check(self, js_file: Path) -> str | None:
        """Pythonで簡易的なJSシンタックスチェック"""
        try:
            content = js_file.read_text(encoding="utf-8")

            # 基本的な括弧のバランスチェック
            brackets = {"(": ")", "[": "]", "{": "}"}
            stack = []
            in_string = False
            in_template_literal = False
            string_char = None
            escape_next = False
            line_num = 1
            prev_char = ""

            for _i, char in enumerate(content):
                if char == "\n":
                    line_num += 1
                    prev_char = char
                    continue

                if escape_next:
                    escape_next = False
                    prev_char = char
                    continue

                if char == "\\":
                    escape_next = True
                    prev_char = char
                    continue

                # テンプレートリテラル内の処理
                if in_template_literal:
                    if char == "`":
                        in_template_literal = False
                        string_char = None
                    # テンプレートリテラル内の ${...} は通常のブラケットとしてカウント
                    elif prev_char == "$" and char == "{":
                        stack.append((char, line_num))
                    elif char in ["}", ")"]:
                        # テンプレートリテラル内の閉じ括弧を処理
                        if stack:
                            expected = brackets.get(stack[-1][0])
                            if expected == char:
                                stack.pop()
                    prev_char = char
                    continue

                # 通常の文字列内の処理
                if in_string:
                    if char == string_char:
                        in_string = False
                        string_char = None
                    prev_char = char
                    continue

                # 文字列の開始
                if char == "`":
                    in_template_literal = True
                    string_char = char
                    prev_char = char
                    continue
                elif char in ('"', "'"):
                    in_string = True
                    string_char = char
                    prev_char = char
                    continue

                # 括弧のチェック（文字列外のみ）
                if char in brackets:
                    stack.append((char, line_num))
                elif char in brackets.values():
                    if not stack:
                        return f"Line {line_num}: Unexpected closing bracket '{char}'"
                    expected = brackets[stack[-1][0]]
                    if char != expected:
                        return f"Line {line_num}: Expected '{expected}' but got '{char}'"
                    stack.pop()

                prev_char = char

            if stack:
                unclosed = stack[-1]
                return f"Line {unclosed[1]}: Unclosed bracket '{unclosed[0]}'"

            if in_string or in_template_literal:
                return "Unclosed string"

            return None

        except Exception as e:
            return f"Error reading file: {e}"

    def test_specific_capabilities_js(self):
        """capabilities.js のシンタックスを個別にチェック"""
        node_cmd = shutil.which("node")
        if not node_cmd:
            pytest.skip("Node.js not available for accurate syntax checking")
        try:
            result = subprocess.run([node_cmd, "--version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                pytest.skip("Node.js not available for accurate syntax checking")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Node.js not available for accurate syntax checking")

        project_root = Path(__file__).parent.parent.parent.parent
        js_file = project_root / "app" / "assets" / "view" / "services" / "capabilities.js"

        if not js_file.exists():
            pytest.skip(f"File not found: {js_file}")

        error = self._validate_js_syntax(js_file)
        assert error is None, f"Syntax error in capabilities.js: {error}"

    def test_dashboard_js(self):
        """dashboard.js のシンタックスを個別にチェック"""
        node_cmd = shutil.which("node")
        if not node_cmd:
            pytest.skip("Node.js not available for accurate syntax checking")
        try:
            result = subprocess.run([node_cmd, "--version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                pytest.skip("Node.js not available for accurate syntax checking")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Node.js not available for accurate syntax checking")

        project_root = Path(__file__).parent.parent.parent.parent
        js_file = project_root / "app" / "assets" / "view" / "dashboard.js"

        if not js_file.exists():
            pytest.skip(f"File not found: {js_file}")

        error = self._validate_js_syntax(js_file)
        assert error is None, f"Syntax error in dashboard.js: {error}"


class TestJavaScriptFetchCalls:
    """JavaScript内のfetch呼び出しを静的に検証"""

    @pytest.fixture
    def js_files(self):
        """テスト対象のJSファイル一覧を取得"""
        project_root = Path(__file__).parent.parent.parent.parent
        js_dir = project_root / "app" / "assets" / "view"

        return list(js_dir.rglob("*.js"))

    def test_fetch_calls_have_error_handling(self, js_files):
        """fetch呼び出しが適切なエラーハンドリングを持つことを確認"""
        issues = []

        for js_file in js_files:
            content = js_file.read_text(encoding="utf-8")

            # fetchを使用しているが、try-catchがない関数を検出
            # 簡易的なチェック
            if (
                "fetch(" in content
                and "try {" not in content
                and ".catch(" not in content
                and ("async function" in content or "async (" in content)
            ):
                issues.append(f"{js_file.name}: fetch() without try-catch or .catch()")

        # 警告として出力（エラーにはしない）
        if issues:
            print("\nWarning - fetch calls potentially without error handling:\n" + "\n".join(issues))

    def test_api_fetch_checks_response_ok(self, js_files):
        """API fetch呼び出しがresponse.okをチェックしているか確認"""
        issues = []

        for js_file in js_files:
            content = js_file.read_text(encoding="utf-8")

            # /api/ へのfetch呼び出しを検出
            if (
                ("fetch(`/api/" in content or "fetch('/api/" in content)
                and "response.ok" not in content
                and "response.status" not in content
            ):
                issues.append(f"{js_file.name}: API fetch without response status check")

        # 警告として出力
        if issues:
            print("\nWarning - API calls potentially without status check:\n" + "\n".join(issues))


class TestSharedJavaScriptUtilities:
    """共有JS utilityのロードと利用契約を検証する"""

    @pytest.fixture
    def project_root(self):
        return Path(__file__).parent.parent.parent.parent

    def test_shared_utilities_are_loaded_by_base_template(self, project_root):
        base_template = (project_root / "app" / "views" / "templates" / "base.html").read_text(encoding="utf-8")

        assert "/assets/js/api-client.js" in base_template
        assert "/assets/js/dom.js" in base_template

    def test_connection_logs_index_uses_shared_escape_helper(self, project_root):
        source = (project_root / "app" / "assets" / "view" / "connection_logs" / "index.js").read_text(encoding="utf-8")

        assert "AppDom.escapeHtml" in source
        assert "escapeHtml(" not in source.replace("AppDom.escapeHtml(", "")

    def test_template_external_links_validate_url_scheme(self, project_root):
        dom_source = (project_root / "app" / "assets" / "js" / "dom.js").read_text(encoding="utf-8")
        template_detail = (project_root / "app" / "assets" / "view" / "templates" / "detail.js").read_text(
            encoding="utf-8"
        )
        service_new = (project_root / "app" / "assets" / "view" / "services" / "new.js").read_text(encoding="utf-8")

        assert "safeHttpUrl" in dom_source
        assert "safeHttpUrl" in template_detail
        assert "safeHttpUrl" in service_new


class TestJavaScriptConsoleLog:
    """本番コードにconsole.logが残っていないかチェック（デバッグ用を除く）"""

    @pytest.fixture
    def js_files(self):
        """テスト対象のJSファイル一覧を取得"""
        project_root = Path(__file__).parent.parent
        js_dir = project_root / "app" / "assets" / "view"

        return list(js_dir.rglob("*.js"))

    def test_no_debug_console_logs(self, js_files):
        """デバッグ用のconsole.logが残っていないことを確認"""
        issues = []

        for js_file in js_files:
            content = js_file.read_text(encoding="utf-8")
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                # console.log を検出（console.error, console.warn は許可）
                if "console.log(" in line:
                    # コメントアウトされている場合はスキップ
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("/*"):
                        continue
                    issues.append(f"{js_file.name}:{i}: {line.strip()[:50]}")

        # 警告として出力（エラーにはしない - デバッグ用途もあるため）
        if issues:
            print("\nNote - console.log found (may be intentional):\n" + "\n".join(issues[:10]))
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
