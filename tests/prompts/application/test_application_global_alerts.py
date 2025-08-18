"""Tests for the ApplicationGlobalAlertsPrompts class."""
import unittest

from src.prompts import PROMPT_REGISTRY
from src.prompts.application.application_global_alerts import (
    ApplicationGlobalAlertsPrompts,
)


class TestApplicationGlobalAlertsPrompts(unittest.TestCase):
    """Test cases for the ApplicationGlobalAlertsPrompts class."""

    def test_app_global_alerts_list_registered(self):
        """Test that app_global_alerts_list is registered in the prompt registry."""
        self.assertIn(ApplicationGlobalAlertsPrompts.app_global_alerts_list, PROMPT_REGISTRY)

    def test_app_global_alert_config_enable_registered(self):
        """Test that app_global_alert_config_enable is registered in the prompt registry."""
        self.assertIn(ApplicationGlobalAlertsPrompts.app_global_alert_config_enable, PROMPT_REGISTRY)

    def test_app_global_alert_config_restore_registered(self):
        """Test that app_global_alert_config_restore is registered in the prompt registry."""
        self.assertIn(ApplicationGlobalAlertsPrompts.app_global_alert_config_restore, PROMPT_REGISTRY)

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ApplicationGlobalAlertsPrompts.get_prompts()
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0][0], 'app_global_alerts_list')
        self.assertEqual(prompts[1][0], 'app_global_alert_config_enable')
        self.assertEqual(prompts[2][0], 'app_global_alert_config_restore')

    # We don't test the content of the prompts directly as they become FunctionPrompt objects
    # after being decorated with @auto_register_prompt


if __name__ == '__main__':
    unittest.main()

# Made with Bob
