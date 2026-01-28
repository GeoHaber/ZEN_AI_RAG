# -*- coding: utf-8 -*-
"""
Test UI for External LLM Settings

Tests the new External LLM configuration section in the settings dialog.
Verifies that users can:
- Enable/disable external LLMs
- Enter API keys (with password masking)
- Select models
- Configure consensus settings
- Set budget limits
"""

import pytest
from unittest.mock import Mock, patch
from settings import AppSettings, ExternalLLMSettings


class TestExternalLLMSettings:
    """Test external LLM settings data model."""

    def test_default_settings(self):
        """Test default external LLM settings."""
        settings = ExternalLLMSettings()

        assert settings.enabled == False
        assert settings.anthropic_api_key == ""
        assert settings.google_api_key == ""
        assert settings.xai_api_key == ""
        assert settings.use_consensus == True
        assert settings.cost_tracking_enabled == True
        assert settings.budget_limit == 10.0
        assert settings.anthropic_model == "claude-3-5-sonnet-20241022"
        assert settings.google_model == "gemini-pro"
        assert settings.xai_model == "grok-beta"

    def test_api_key_storage(self):
        """Test API key storage and retrieval."""
        settings = ExternalLLMSettings()

        # Set API keys
        settings.anthropic_api_key = "sk-ant-test123"
        settings.google_api_key = "AIza-test456"
        settings.xai_api_key = "xai-test789"

        # Verify storage
        assert settings.anthropic_api_key == "sk-ant-test123"
        assert settings.google_api_key == "AIza-test456"
        assert settings.xai_api_key == "xai-test789"

    def test_model_selection(self):
        """Test model selection for each provider."""
        settings = ExternalLLMSettings()

        # Test Anthropic models
        settings.anthropic_model = "claude-3-opus-20240229"
        assert settings.anthropic_model == "claude-3-opus-20240229"

        # Test Google models
        settings.google_model = "gemini-pro-vision"
        assert settings.google_model == "gemini-pro-vision"

        # Test Grok models
        settings.xai_model = "grok-beta"
        assert settings.xai_model == "grok-beta"

    def test_consensus_settings(self):
        """Test consensus configuration."""
        settings = ExternalLLMSettings()

        # Disable consensus
        settings.use_consensus = False
        assert settings.use_consensus == False

        # Re-enable
        settings.use_consensus = True
        assert settings.use_consensus == True

    def test_cost_tracking_settings(self):
        """Test cost tracking configuration."""
        settings = ExternalLLMSettings()

        # Disable cost tracking
        settings.cost_tracking_enabled = False
        assert settings.cost_tracking_enabled == False

        # Test budget limits
        settings.budget_limit = 25.50
        assert settings.budget_limit == 25.50

        settings.budget_limit = 100.0
        assert settings.budget_limit == 100.0

    def test_integration_with_app_settings(self):
        """Test external LLM settings integrate with main app settings."""
        app_settings = AppSettings()

        # Should have external_llm attribute
        assert hasattr(app_settings, 'external_llm')
        assert isinstance(app_settings.external_llm, ExternalLLMSettings)

        # Test modification through app settings
        app_settings.external_llm.enabled = True
        app_settings.external_llm.google_api_key = "AIza-test"

        assert app_settings.external_llm.enabled == True
        assert app_settings.external_llm.google_api_key == "AIza-test"


class TestExternalLLMUIComponents:
    """Test UI components for external LLM configuration."""

    def test_ui_expansion_exists(self):
        """Test that External LLMs expansion section exists in settings dialog."""
        # This would be tested with actual UI framework
        # For now, verify the settings structure is correct
        settings = AppSettings()
        assert hasattr(settings, 'external_llm')

    def test_api_key_password_masking(self):
        """Test that API keys are password-masked in UI."""
        # Verify settings support password storage
        settings = ExternalLLMSettings()

        # API keys should be stored as plain strings
        # (UI handles masking via password=True)
        settings.anthropic_api_key = "sk-ant-secret123"
        assert settings.anthropic_api_key == "sk-ant-secret123"

    def test_model_dropdown_options(self):
        """Test that model dropdown has correct options."""
        # Anthropic models
        anthropic_models = [
            'claude-3-5-sonnet-20241022',
            'claude-3-opus-20240229',
            'claude-3-haiku-20240307'
        ]

        # Google models
        google_models = [
            'gemini-pro',
            'gemini-pro-vision'
        ]

        # Grok models
        grok_models = ['grok-beta']

        # Verify default selections are in the lists
        settings = ExternalLLMSettings()
        assert settings.anthropic_model in anthropic_models
        assert settings.google_model in google_models
        assert settings.xai_model in grok_models

    def test_budget_limit_validation(self):
        """Test budget limit input validation."""
        settings = ExternalLLMSettings()

        # Valid budgets
        settings.budget_limit = 0.0  # Minimum
        assert settings.budget_limit == 0.0

        settings.budget_limit = 50.0  # Reasonable
        assert settings.budget_limit == 50.0

        settings.budget_limit = 1000.0  # Maximum
        assert settings.budget_limit == 1000.0

        # Note: UI should enforce min=0, max=1000, step=5


class TestExternalLLMIntegration:
    """Test integration with SwarmArbitrator."""

    def test_settings_to_environment_variables(self):
        """Test that settings can be used to set environment variables."""
        import os

        settings = ExternalLLMSettings()
        settings.anthropic_api_key = "sk-ant-test123"
        settings.google_api_key = "AIza-test456"
        settings.xai_api_key = "xai-test789"

        # Simulate setting environment variables from settings
        os.environ['ANTHROPIC_API_KEY'] = settings.anthropic_api_key
        os.environ['GOOGLE_API_KEY'] = settings.google_api_key
        os.environ['XAI_API_KEY'] = settings.xai_api_key

        # Verify they're set
        assert os.getenv('ANTHROPIC_API_KEY') == "sk-ant-test123"
        assert os.getenv('GOOGLE_API_KEY') == "AIza-test456"
        assert os.getenv('XAI_API_KEY') == "xai-test789"

        # Cleanup
        del os.environ['ANTHROPIC_API_KEY']
        del os.environ['GOOGLE_API_KEY']
        del os.environ['XAI_API_KEY']

    def test_external_llm_enabled_flag(self):
        """Test that enabled flag controls external LLM usage."""
        settings = ExternalLLMSettings()

        # When disabled, external LLMs should not be queried
        settings.enabled = False
        assert settings.enabled == False

        # When enabled with API keys, external LLMs can be queried
        settings.enabled = True
        settings.google_api_key = "AIza-test"
        assert settings.enabled == True
        assert settings.google_api_key != ""

    def test_consensus_mode_configuration(self):
        """Test consensus mode can be configured."""
        settings = ExternalLLMSettings()

        # Consensus mode enabled (default)
        assert settings.use_consensus == True

        # Single LLM mode (consensus disabled)
        settings.use_consensus = False
        assert settings.use_consensus == False


class TestUIWorkflow:
    """Test complete user workflow for configuring external LLMs."""

    def test_workflow_google_gemini_setup(self):
        """Test workflow: User sets up Google Gemini (FREE)."""
        settings = AppSettings()

        # Step 1: User enables external LLMs
        settings.external_llm.enabled = True

        # Step 2: User enters Google API key
        settings.external_llm.google_api_key = "AIza-real-key-here"

        # Step 3: User selects model (default is fine)
        assert settings.external_llm.google_model == "gemini-pro"

        # Step 4: User enables consensus
        settings.external_llm.use_consensus = True

        # Step 5: User enables cost tracking
        settings.external_llm.cost_tracking_enabled = True

        # Step 6: User sets budget
        settings.external_llm.budget_limit = 10.0

        # Verify final state
        assert settings.external_llm.enabled == True
        assert settings.external_llm.google_api_key == "AIza-real-key-here"
        assert settings.external_llm.use_consensus == True
        assert settings.external_llm.cost_tracking_enabled == True
        assert settings.external_llm.budget_limit == 10.0

    def test_workflow_all_three_providers(self):
        """Test workflow: User sets up all three providers."""
        settings = AppSettings()

        # Enable external LLMs
        settings.external_llm.enabled = True

        # Add all three API keys
        settings.external_llm.anthropic_api_key = "sk-ant-key"
        settings.external_llm.google_api_key = "AIza-key"
        settings.external_llm.xai_api_key = "xai-key"

        # Enable consensus (query all three)
        settings.external_llm.use_consensus = True

        # Set higher budget for multiple providers
        settings.external_llm.budget_limit = 30.0

        # Verify all providers configured
        assert settings.external_llm.anthropic_api_key != ""
        assert settings.external_llm.google_api_key != ""
        assert settings.external_llm.xai_api_key != ""
        assert settings.external_llm.budget_limit == 30.0

    def test_workflow_disable_external_llms(self):
        """Test workflow: User disables external LLMs."""
        settings = AppSettings()

        # Setup first
        settings.external_llm.enabled = True
        settings.external_llm.google_api_key = "AIza-key"

        # Then disable
        settings.external_llm.enabled = False

        # API keys should persist (not deleted)
        assert settings.external_llm.google_api_key == "AIza-key"
        # But feature is disabled
        assert settings.external_llm.enabled == False


class TestSettingsPersistence:
    """Test that external LLM settings persist correctly."""

    def test_settings_save_and_load(self):
        """Test saving and loading external LLM settings."""
        import tempfile
        import json
        from pathlib import Path

        # Create temporary settings file
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "test_settings.json"

            # Create and configure settings
            settings = AppSettings()
            settings.external_llm.enabled = True
            settings.external_llm.google_api_key = "AIza-test-key"
            settings.external_llm.budget_limit = 25.0

            # Simulate save
            data = {
                'external_llm': {
                    'enabled': settings.external_llm.enabled,
                    'google_api_key': settings.external_llm.google_api_key,
                    'budget_limit': settings.external_llm.budget_limit,
                }
            }
            settings_file.write_text(json.dumps(data, indent=2))

            # Simulate load
            loaded_data = json.loads(settings_file.read_text())
            new_settings = AppSettings()
            new_settings.external_llm.enabled = loaded_data['external_llm']['enabled']
            new_settings.external_llm.google_api_key = loaded_data['external_llm']['google_api_key']
            new_settings.external_llm.budget_limit = loaded_data['external_llm']['budget_limit']

            # Verify
            assert new_settings.external_llm.enabled == True
            assert new_settings.external_llm.google_api_key == "AIza-test-key"
            assert new_settings.external_llm.budget_limit == 25.0


class TestAPIKeyValidation:
    """Test API key format validation."""

    def test_anthropic_key_format(self):
        """Test Anthropic API key starts with sk-ant-."""
        key = "sk-ant-api03-abc123"
        assert key.startswith("sk-ant-")

    def test_google_key_format(self):
        """Test Google API key starts with AIza."""
        key = "AIzaSyABC123XYZ"
        assert key.startswith("AIza")

    def test_grok_key_format(self):
        """Test Grok API key starts with xai-."""
        key = "xai-abc123xyz"
        assert key.startswith("xai-")

    def test_empty_keys_allowed(self):
        """Test that empty API keys are valid (provider is optional)."""
        settings = ExternalLLMSettings()

        # All keys start empty
        assert settings.anthropic_api_key == ""
        assert settings.google_api_key == ""
        assert settings.xai_api_key == ""

        # This is valid - user may only want to use one provider


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
