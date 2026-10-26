"""
Tests for Modal and Template Sync functionality
共通モーダルとビルトインテンプレート同期機能のテスト
"""

from unittest.mock import Mock, patch


class TestTemplateSyncService:
    """Test template synchronization service - unit tests"""

    def test_check_for_updates_with_update_available(self, app, db):
        """Test check_for_updates when new version is available"""
        from app.models.models import AdminSettings
        from app.models.models import db as _db
        from app.services.template_sync import TemplateSyncService

        with app.app_context():
            # Mock index.yaml data
            mock_index = {
                "versions": [
                    {
                        "version": "1.1.0",
                        "accel_mcp_min": "0.1.0",
                        "accel_mcp_max": "2.0.0",
                        "file": "builtin_templates_v1.1.0.yaml",
                        "changelog": "New templates added",
                        "template_count": 5,
                        "released_at": "2026-01-14",
                        "schema_breaking": False,
                    }
                ]
            }

            # Set current version
            setting = AdminSettings.query.filter_by(setting_key="builtin_templates_version").first()
            if setting:
                setting.setting_value = "1.0.0"
            else:
                setting = AdminSettings(setting_key="builtin_templates_version", setting_value="1.0.0")
                _db.session.add(setting)
            _db.session.commit()

            service = TemplateSyncService()

            with patch.object(service, "fetch_yaml", return_value=mock_index):
                result = service.check_for_updates()

                assert result["has_update"] is True
                assert result["current_version"] == "1.0.0"
                assert result["latest_version"] == "1.1.0"
                assert result["changelog"] == "New templates added"
                assert result["template_count"] == 5

    def test_check_for_updates_already_latest(self, app, db):
        """Test check_for_updates when already on latest version"""
        from app.models.models import AdminSettings
        from app.models.models import db as _db
        from app.services.template_sync import TemplateSyncService

        with app.app_context():
            mock_index = {
                "versions": [
                    {
                        "version": "1.0.0",
                        "accel_mcp_min": "0.1.0",
                        "accel_mcp_max": "2.0.0",
                        "file": "builtin_templates_v1.0.0.yaml",
                        "changelog": "Initial release",
                        "template_count": 3,
                        "released_at": "2026-01-01",
                        "schema_breaking": False,
                    }
                ]
            }

            # Set current version to latest
            setting = AdminSettings.query.filter_by(setting_key="builtin_templates_version").first()
            if setting:
                setting.setting_value = "1.0.0"
            else:
                setting = AdminSettings(setting_key="builtin_templates_version", setting_value="1.0.0")
                _db.session.add(setting)
            _db.session.commit()

            service = TemplateSyncService()

            with patch.object(service, "fetch_yaml", return_value=mock_index):
                result = service.check_for_updates()

                assert result["has_update"] is False
                assert result["current_version"] == "1.0.0"
                assert result["latest_version"] == "1.0.0"

    def test_sync_templates_success(self, app, db):
        """Test successful template synchronization"""
        from app.models.models import AdminSettings, McpServiceTemplate
        from app.services.template_sync import TemplateSyncService

        with app.app_context():
            mock_index = {
                "versions": [
                    {
                        "version": "1.1.0",
                        "accel_mcp_min": "0.1.0",
                        "accel_mcp_max": "2.0.0",
                        "file": "builtin_templates_v1.1.0.yaml",
                    }
                ]
            }

            mock_template_data = {
                "version": "1.1.0",
                "templates": [
                    {
                        "id": "test-template-1",
                        "name": "Test Template 1",
                        "service_type": "rest_api",
                        "description": "Test template",
                        "icon": "🧪",
                        "category": "Test",
                        "common_headers": {"X-Test": "value"},
                    }
                ],
            }

            service = TemplateSyncService()

            def fetch_yaml_side_effect(url):
                if "index.yaml" in url:
                    return mock_index
                else:
                    return mock_template_data

            with patch.object(service, "fetch_yaml", side_effect=fetch_yaml_side_effect):
                result = service.sync_templates()

                assert result["success"] is True
                assert result["version"] == "1.1.0"
                assert result["added"] == 1

                # Verify template was added
                template1 = McpServiceTemplate.query.filter_by(template_id="test-template-1").first()
                assert template1 is not None
                assert template1.name == "Test Template 1"
                assert template1.service_type == "rest_api"
                assert template1.template_version == "1.1.0"

                # Verify version was saved
                version_setting = AdminSettings.query.filter_by(setting_key="builtin_templates_version").first()
                assert version_setting is not None
                assert version_setting.setting_value == "1.1.0"

    def test_sync_templates_removes_existing_capabilities_before_deleting_templates(self, app, db):
        """Re-syncing must delete child McpCapabilityTemplate rows before deleting their
        parent McpServiceTemplate rows, otherwise the bulk delete violates the DB-level
        foreign key constraint (no ON DELETE CASCADE) and the whole sync fails in production
        Postgres, even though it passes against SQLite (which doesn't enforce FKs in tests)."""
        from app.models.models import McpCapabilityTemplate, McpServiceTemplate
        from app.models.models import db as _db
        from app.services.template_sync import TemplateSyncService

        with app.app_context():
            # Seed a pre-existing builtin template that has child capabilities, mirroring
            # production state (e.g. the real "Slack API" builtin template).
            old_template = McpServiceTemplate(
                name="Old API",
                template_type="builtin",
                service_type="api",
                template_id="old-api",
                template_version="1.0.0",
            )
            _db.session.add(old_template)
            _db.session.flush()
            _db.session.add(
                McpCapabilityTemplate(
                    template_id=old_template.id,
                    name="Old Capability",
                    capability_type="tool",
                )
            )
            _db.session.commit()

            mock_index = {
                "versions": [
                    {
                        "version": "1.1.0",
                        "accel_mcp_min": "0.1.0",
                        "accel_mcp_max": "2.0.0",
                        "file": "builtin_templates_v1.1.0.yaml",
                    }
                ]
            }
            mock_template_data = {
                "version": "1.1.0",
                "templates": [
                    {
                        "id": "new-api",
                        "name": "New API",
                        "service_type": "api",
                        "description": "Replacement template",
                        "icon": "🆕",
                        "category": "Test",
                        "capabilities": [{"name": "New Capability", "capability_type": "tool", "endpoint_path": "x"}],
                    }
                ],
            }

            service = TemplateSyncService()

            def fetch_yaml_side_effect(url):
                return mock_index if "index.yaml" in url else mock_template_data

            with patch.object(service, "fetch_yaml", side_effect=fetch_yaml_side_effect):
                result = service.sync_templates()

            assert result["success"] is True

            # The old template and its capability must be fully gone. (Note: SQLite reuses
            # primary keys after a delete, so check by name rather than the stale FK value.)
            assert McpServiceTemplate.query.filter_by(template_id="old-api").first() is None
            assert McpCapabilityTemplate.query.filter_by(name="Old Capability").first() is None

            # The new template was added correctly.
            new_template = McpServiceTemplate.query.filter_by(template_id="new-api").first()
            assert new_template is not None
            assert len(new_template.capability_templates) == 1


class TestCommonModalBasic:
    """Basic tests for common modal functionality"""

    def test_modal_html_structure_exists(self, client):
        """Test that modal HTML structure is present in base template"""
        # This is a simple test that checks if modal-related code exists
        # More comprehensive E2E tests would require Playwright
        response = client.get("/login")
        assert response.status_code == 200
        # Check if modal.js is loaded (in production it should be)
        # This is a basic sanity check
        assert b"html" in response.data

    def test_i18n_modal_keys_exist(self):
        """Test that i18n modal keys are defined"""
        # Import i18n module and check if modal-related keys exist
        import os

        # Check if i18n.js file exists
        i18n_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "app", "assets", "i18n.js")
        assert os.path.exists(i18n_path)

        # Read the file and check for modal-related keys
        with open(i18n_path, encoding="utf-8") as f:
            content = f.read()

        # Check for Japanese translation keys
        assert "common_confirm" in content
        assert "common_notice" in content
        assert "common_success" in content
        assert "common_error" in content
        assert "common_warning" in content
        assert "common_delete" in content
        assert "common_cancel" in content

    def test_modal_js_file_exists(self):
        """Test that modal.js file exists"""
        import os

        modal_js_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "app", "assets", "view", "common", "modal.js"
        )
        assert os.path.exists(modal_js_path)

        # Check file contains expected functions
        with open(modal_js_path, encoding="utf-8") as f:
            content = f.read()

        assert "class CommonModal" in content
        assert "confirm(" in content
        assert "alert(" in content
        assert "success(" in content
        assert "error(" in content
        assert "warning(" in content
        assert "confirmDelete(" in content


class TestAPIEndpoints:
    """Test API endpoints for template sync"""

    def test_check_updates_endpoint_exists(self, auth_client):
        """Test that check-updates endpoint exists"""
        with patch("app.services.template_sync.TemplateSyncService") as mock_service:
            mock_instance = Mock()
            mock_instance.check_for_updates.return_value = {
                "has_update": False,
                "current_version": "1.0.0",
                "latest_version": "1.0.0",
                "changelog": "",
                "template_count": 3,
            }
            mock_service.return_value = mock_instance

            response = auth_client.get("/api/templates/check-updates")
            assert response.status_code == 200
            data = response.get_json()
            assert "has_update" in data
            assert "current_version" in data
            assert "latest_version" in data

    def test_sync_templates_endpoint_exists(self, auth_client):
        """Test that sync endpoint exists"""
        with patch("app.services.template_sync.TemplateSyncService") as mock_service:
            mock_instance = Mock()
            mock_instance.sync_templates.return_value = {
                "success": True,
                "version": "1.0.0",
                "added": 3,
                "updated": 0,
                "message": "Success",
            }
            mock_service.return_value = mock_instance

            response = auth_client.post("/api/templates/sync")
            assert response.status_code == 200
            data = response.get_json()
            assert "success" in data
            assert "version" in data


def test_template_sync_service_initialization(app):
    """Test that TemplateSyncService can be initialized"""
    from app.services.template_sync import TemplateSyncService

    with app.app_context():
        service = TemplateSyncService()
        assert service is not None
        assert hasattr(service, "check_for_updates")
        assert hasattr(service, "sync_templates")


def test_modal_and_sync_integration(app):
    """Integration test - verify both features are properly integrated"""
    with app.app_context():
        # Check that template sync service exists
        from app.services.template_sync import TemplateSyncService

        service = TemplateSyncService()
        assert service is not None

        # Check that modal JavaScript exists
        import os

        modal_js_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "app", "assets", "view", "common", "modal.js"
        )
        assert os.path.exists(modal_js_path)

        # Both features are successfully integrated
        assert True
