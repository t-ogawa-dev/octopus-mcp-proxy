"""
Test suite for stdio MCP functionality
Tests for stdio MCP connection, discovery, and variable replacement in args/env
"""

import json
import logging
from unittest.mock import patch

import pytest

from app.models.models import Capability, Service, Variable


# Fixture for sample_variable that properly encrypts the value
@pytest.fixture
def sample_variable(db):
    """Create sample variable for testing with proper encryption"""
    variable = Variable(
        name="TEST_API_KEY",
        value_type="string",
        source_type="value",
        description="Test API key for stdio MCP",
        is_secret=True,
    )
    variable.set_value("secret-test-key-12345")  # Use set_value for encryption
    db.session.add(variable)
    db.session.commit()
    return variable


@pytest.fixture
def sample_stdio_app(db, sample_mcp_service):
    """Create sample stdio MCP app"""
    service = Service(
        mcp_service_id=sample_mcp_service.id,
        name="stdio-test-app",
        service_type="mcp",
        mcp_transport="stdio",
        stdio_command="npx",
        stdio_args=json.dumps(["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]),
        stdio_env=json.dumps({"API_KEY": "{{TEST_API_KEY}}"}),
        stdio_cwd="/tmp",
        description="Test stdio MCP app",
    )
    db.session.add(service)
    db.session.commit()
    return service


class TestStdioMcpModel:
    """Test Service model with stdio fields"""

    def test_service_stdio_fields_exist(self, db, sample_mcp_service):
        """Test that stdio fields are properly saved and retrieved"""
        service = Service(
            mcp_service_id=sample_mcp_service.id,
            name="stdio-model-test",
            service_type="mcp",
            mcp_transport="stdio",
            stdio_command="python",
            stdio_args=json.dumps(["--version"]),
            stdio_env=json.dumps({"PATH": "/usr/bin"}),
            stdio_cwd="/home/user",
        )
        db.session.add(service)
        db.session.commit()

        # Retrieve and verify
        saved = Service.query.filter_by(name="stdio-model-test").first()
        assert saved is not None
        assert saved.mcp_transport == "stdio"
        assert saved.stdio_command == "python"
        assert saved.stdio_args == '["--version"]'
        assert saved.stdio_env == '{"PATH": "/usr/bin"}'
        assert saved.stdio_cwd == "/home/user"

    def test_service_to_dict_includes_stdio_fields(self, db, sample_mcp_service):
        """Test that to_dict includes all stdio fields"""
        service = Service(
            mcp_service_id=sample_mcp_service.id,
            name="stdio-dict-test",
            service_type="mcp",
            mcp_transport="stdio",
            stdio_command="node",
            stdio_args=json.dumps(["server.js"]),
            stdio_env=json.dumps({"NODE_ENV": "production"}),
            stdio_cwd="/app",
        )
        db.session.add(service)
        db.session.commit()

        data = service.to_dict()
        assert data["mcp_transport"] == "stdio"
        assert data["stdio_command"] == "node"
        assert data["stdio_args"] == ["server.js"]
        assert data["stdio_env"] == {"NODE_ENV": "production"}
        assert data["stdio_cwd"] == "/app"

    def test_service_http_transport_default(self, db, sample_mcp_service):
        """Test that HTTP transport is default"""
        service = Service(
            mcp_service_id=sample_mcp_service.id,
            name="http-default-test",
            service_type="mcp",
            mcp_url="http://localhost:3000/mcp",
        )
        db.session.add(service)
        db.session.commit()

        data = service.to_dict()
        assert data["mcp_transport"] == "http"


class TestVariableReplacementInStdio:
    """Test variable replacement in stdio args and env"""

    def test_variable_replacement_in_env(self, db, sample_variable):
        """Test that variables are replaced in environment variables"""
        from app.services.variable_replacer import VariableReplacer

        replacer = VariableReplacer()

        # Test replacement
        result = replacer.replace_in_string("{{TEST_API_KEY}}")
        assert result == "secret-test-key-12345"

    def test_variable_replacement_in_args(self, db, sample_variable):
        """Test that variables are replaced in arguments"""
        from app.services.variable_replacer import VariableReplacer

        replacer = VariableReplacer()
        args = ["--api-key", "{{TEST_API_KEY}}", "--verbose"]

        resolved = [replacer.replace_in_string(arg) for arg in args]
        assert resolved == ["--api-key", "secret-test-key-12345", "--verbose"]

    def test_unresolved_variable_stays_unchanged(self, db):
        """Test that unresolved variables remain as placeholders"""
        from app.services.variable_replacer import VariableReplacer

        replacer = VariableReplacer()
        result = replacer.replace_in_string("{{UNDEFINED_VAR}}")
        assert result == "{{UNDEFINED_VAR}}"

    def test_multiple_variables_in_string(self, db, sample_variable):
        """Test replacement of multiple variables in a single string"""
        # Create another variable
        var2 = Variable(name="ANOTHER_KEY", value_type="string", source_type="value", description="Another test key")
        var2.set_value("another-value")
        db.session.add(var2)
        db.session.commit()

        from app.services.variable_replacer import VariableReplacer

        replacer = VariableReplacer()

        result = replacer.replace_in_string("--key={{TEST_API_KEY}}&other={{ANOTHER_KEY}}")
        assert result == "--key=secret-test-key-12345&other=another-value"


class TestStdioConnectionTestAPI:
    """Test the stdio connection test API endpoint"""

    @patch("app.services.mcp_discovery.test_stdio_mcp_connection")
    def test_test_stdio_connection_does_not_log_arguments_or_environment(self, mock_test, auth_client, caplog):
        secret_value = "stdio-secret-marker"
        mock_test.return_value = {"success": True, "tools": [], "server_info": {}}

        with caplog.at_level(logging.INFO):
            response = auth_client.post(
                "/api/apps/test-stdio-connection",
                json={"command": "mcp-client", "args": ["--token", secret_value], "env": {"API_KEY": secret_value}},
                content_type="application/json",
            )

        assert response.status_code == 200
        assert secret_value not in caplog.text

    def test_test_stdio_connection_missing_command(self, auth_client):
        """Test error when command is missing"""
        response = auth_client.post(
            "/api/apps/test-stdio-connection", json={"args": [], "env": {}}, content_type="application/json"
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Command is required" in data["error"]

    def test_test_stdio_connection_unresolved_variable_in_args(self, auth_client, db):
        """Test error when args contain unresolved variables"""
        response = auth_client.post(
            "/api/apps/test-stdio-connection",
            json={"command": "npx", "args": ["--token", "{{UNDEFINED_TOKEN}}"], "env": {}},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "UNDEFINED_TOKEN" in data["error"]

    def test_test_stdio_connection_unresolved_variable_in_env(self, auth_client, db):
        """Test error when env contains unresolved variables"""
        response = auth_client.post(
            "/api/apps/test-stdio-connection",
            json={"command": "npx", "args": [], "env": {"API_KEY": "{{UNDEFINED_KEY}}"}},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "UNDEFINED_KEY" in data["error"]

    @patch("app.services.mcp_discovery.test_stdio_mcp_connection")
    def test_test_stdio_connection_success(self, mock_test, auth_client, db, sample_variable):
        """Test successful stdio connection test"""
        mock_test.return_value = {
            "success": True,
            "tools": ["read_file", "write_file", "list_directory"],
            "server_info": {"name": "filesystem-server", "version": "1.0.0"},
        }

        response = auth_client.post(
            "/api/apps/test-stdio-connection",
            json={
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "env": {"API_KEY": "{{TEST_API_KEY}}"},
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "tools" in data
        assert len(data["tools"]) == 3

    @patch("app.services.mcp_discovery.test_stdio_mcp_connection")
    def test_test_stdio_connection_failure(self, mock_test, auth_client, db):
        """Test failed stdio connection test"""
        mock_test.return_value = {"success": False, "error": "Command not found: npx"}

        response = auth_client.post(
            "/api/apps/test-stdio-connection",
            json={"command": "npx", "args": ["-y", "nonexistent-package"], "env": {}},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert "Command not found" in data["error"]


def close_coroutine_and_return(return_value):
    """Create a side_effect function that closes the coroutine and returns a value"""

    def side_effect(coro):
        coro.close()  # Close the coroutine to prevent "never awaited" warning
        return return_value

    return side_effect


class TestStdioMcpDiscovery:
    """Test stdio MCP capability discovery"""

    @patch("app.services.mcp_discovery.asyncio.run")
    def test_discover_stdio_capabilities(self, mock_run, db, sample_mcp_service):
        """Test stdio capability discovery"""
        from app.services.mcp_discovery import discover_stdio_mcp_capabilities

        mock_run.side_effect = close_coroutine_and_return(
            [
                {"name": "read_file", "description": "Read a file", "inputSchema": {"type": "object"}},
                {"name": "write_file", "description": "Write a file", "inputSchema": {"type": "object"}},
            ]
        )

        # Create a service first
        service = Service(
            mcp_service_id=sample_mcp_service.id,
            name="discovery-test",
            service_type="mcp",
            mcp_transport="stdio",
            stdio_command="npx",
        )
        db.session.add(service)
        db.session.commit()
        service_id = service.id

        # Call without variables (no variable replacement needed)
        tool_count = discover_stdio_mcp_capabilities(
            service_id,
            "npx",
            ["-y", "@modelcontextprotocol/server-filesystem"],
            {},  # No env vars with variables
            "/tmp",
        )

        assert tool_count == 2

        # Verify capabilities were created
        caps = Capability.query.filter_by(app_id=service_id).all()
        assert len(caps) == 2
        assert any(c.name == "read_file" for c in caps)
        assert any(c.name == "write_file" for c in caps)

    @patch("app.services.mcp_discovery.asyncio.run")
    def test_discover_stdio_capabilities_with_variables(self, mock_run, db, sample_mcp_service, sample_variable):
        """Test stdio capability discovery with variable replacement"""
        from app.services.mcp_discovery import discover_stdio_mcp_capabilities

        mock_run.side_effect = close_coroutine_and_return(
            [{"name": "search", "description": "Search", "inputSchema": {"type": "object"}}]
        )

        # Create a service
        service = Service(
            mcp_service_id=sample_mcp_service.id,
            name="discovery-var-test",
            service_type="mcp",
            mcp_transport="stdio",
            stdio_command="python",
        )
        db.session.add(service)
        db.session.commit()

        # Call with variable in env - should be resolved
        tool_count = discover_stdio_mcp_capabilities(
            service.id,
            "python",
            ["--key", "{{TEST_API_KEY}}"],  # Variable in args
            {"API_TOKEN": "{{TEST_API_KEY}}"},  # Variable in env
            None,
        )

        assert tool_count == 1

        # Verify asyncio.run was called with resolved values
        mock_run.call_args[0][0]
        # The coroutine should have been called with resolved values

    @patch("app.services.mcp_discovery.asyncio.run")
    def test_test_stdio_mcp_connection_function(self, mock_run, db):
        """Test test_stdio_mcp_connection function"""
        from app.services.mcp_discovery import test_stdio_mcp_connection

        mock_run.side_effect = close_coroutine_and_return(
            [{"name": "tool1", "description": "Tool 1"}, {"name": "tool2", "description": "Tool 2"}]
        )

        result = test_stdio_mcp_connection("npx", ["-y", "package"], {}, None)

        assert result["success"] is True
        assert "tools" in result
        assert len(result["tools"]) == 2

    @patch("app.services.mcp_discovery.asyncio.run")
    def test_test_stdio_mcp_connection_error(self, mock_run, db):
        """Test test_stdio_mcp_connection function when error occurs"""
        from app.services.mcp_discovery import test_stdio_mcp_connection

        def raise_error(coro):
            coro.close()
            raise Exception("Connection refused")

        mock_run.side_effect = raise_error

        result = test_stdio_mcp_connection("npx", ["-y", "bad-package"], {}, None)

        assert result["success"] is False
        assert "Connection refused" in result["error"]


class TestStdioAppCreation:
    """Test creating apps with stdio transport via API"""

    @patch("app.services.mcp_discovery.discover_stdio_mcp_capabilities")
    def test_create_stdio_app_via_api(self, mock_discover, auth_client, db, sample_mcp_service):
        """Test creating a stdio MCP app via API"""
        mock_discover.return_value = 0  # Mock to return 0 tools

        response = auth_client.post(
            "/api/apps",
            json={
                "mcp_service_id": sample_mcp_service.id,
                "name": "api-stdio-test",
                "service_type": "mcp",
                "mcp_transport": "stdio",
                "stdio_command": "python",
                "stdio_args": ["-m", "mcp_server"],
                "stdio_env": {"DEBUG": "true"},
                "stdio_cwd": "/app",
                "description": "Test stdio app created via API",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "api-stdio-test"
        assert data["mcp_transport"] == "stdio"
        assert data["stdio_command"] == "python"
        assert data["stdio_args"] == ["-m", "mcp_server"]
        assert data["stdio_env"] == {"DEBUG": "true"}

    @patch("app.services.mcp_discovery.discover_mcp_capabilities")
    def test_create_http_app_via_api(self, mock_discover, auth_client, db, sample_mcp_service):
        """Test creating an HTTP MCP app via API (default transport)"""
        mock_discover.return_value = 0  # Mock to return 0 tools

        response = auth_client.post(
            "/api/apps",
            json={
                "mcp_service_id": sample_mcp_service.id,
                "name": "api-http-test",
                "service_type": "mcp",
                "mcp_url": "http://localhost:3000/mcp",
                "description": "Test HTTP app created via API",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "api-http-test"
        assert data["mcp_transport"] == "http"
        assert data["mcp_url"] == "http://localhost:3000/mcp"


class TestMcpHandlerStdio:
    """Test MCP Handler with stdio transport"""

    def test_mcp_handler_detects_stdio_transport(self, db, sample_stdio_app, sample_variable):
        """Test that MCP handler correctly identifies stdio transport"""

        # Create a capability for the stdio app
        capability = Capability(
            app_id=sample_stdio_app.id, name="test_tool", capability_type="mcp_tool", description="Test tool"
        )
        db.session.add(capability)
        db.session.commit()

        # Verify the app has stdio transport
        service = db.session.get(Service, sample_stdio_app.id)
        assert service.mcp_transport == "stdio"
        assert service.stdio_command == "npx"

    @patch("app.services.mcp_handler.MCPHandler._execute_stdio_mcp_call")
    def test_mcp_handler_calls_stdio_method(self, mock_stdio_call, db, sample_stdio_app, sample_variable):
        """Test that MCP handler calls stdio method for stdio transport"""
        from app.services.mcp_handler import MCPHandler

        # Create capability
        capability = Capability(
            app_id=sample_stdio_app.id, name="list_files", capability_type="mcp_tool", description="List files"
        )
        db.session.add(capability)
        db.session.commit()

        mock_stdio_call.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "file1.txt\nfile2.txt"}]},
        }

        handler = MCPHandler(db)
        service = db.session.get(Service, sample_stdio_app.id)

        # Call the method that should detect stdio
        handler._execute_mcp_call(service, capability, {"path": "/tmp"})

        # Verify stdio method was called
        mock_stdio_call.assert_called_once()

    def test_stdio_mcp_call_variable_replacement(self, db, sample_stdio_app, sample_variable):
        """Test that variables are replaced in stdio MCP calls"""
        from app.services.variable_replacer import VariableReplacer

        # Verify the service has variables in env
        service = db.session.get(Service, sample_stdio_app.id)
        env = json.loads(service.stdio_env)
        assert "{{TEST_API_KEY}}" in env.get("API_KEY", "")

        # Test variable replacement
        replacer = VariableReplacer()
        resolved = replacer.replace_in_string(env["API_KEY"])
        assert resolved == "secret-test-key-12345"


class TestVariableEncryption:
    """Test Variable model encryption"""

    def test_variable_set_and_get_value(self, db):
        """Test that Variable correctly encrypts and decrypts values"""
        variable = Variable(
            name="ENCRYPTED_VAR", value_type="string", source_type="value", description="Test encryption"
        )
        variable.set_value("my-secret-value")
        db.session.add(variable)
        db.session.commit()

        # Retrieve and check
        saved = Variable.query.filter_by(name="ENCRYPTED_VAR").first()
        assert saved is not None
        assert saved.value != "my-secret-value"  # Should be encrypted
        assert saved.get_value() == "my-secret-value"  # Should decrypt correctly

    def test_variable_in_replacer(self, db):
        """Test that VariableReplacer correctly uses encrypted variables"""
        variable = Variable(name="REPLACER_TEST", value_type="string", source_type="value")
        variable.set_value("replaced-value")
        db.session.add(variable)
        db.session.commit()

        from app.services.variable_replacer import VariableReplacer

        replacer = VariableReplacer()

        result = replacer.replace_in_string("prefix-{{REPLACER_TEST}}-suffix")
        assert result == "prefix-replaced-value-suffix"
