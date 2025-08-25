"""
Tests for the prompts functionality using existing prompt classes.
"""

import pytest

from src.prompts.application.application_alerts import ApplicationAlertsPrompts
from src.prompts.application.application_catalog import ApplicationCatalogPrompts
from src.prompts.application.application_metrics import ApplicationMetricsPrompts
from src.prompts.application.application_resources import ApplicationResourcesPrompts
from src.prompts.application.application_settings import ApplicationSettingsPrompts
from src.prompts.application.application_topology import ApplicationTopologyPrompts
from src.prompts.infrastructure.infrastructure_analyze import (
    InfrastructureAnalyzePrompts,
)
from src.prompts.infrastructure.infrastructure_catalog import (
    InfrastructureCatalogPrompts,
)
from src.prompts.infrastructure.infrastructure_metrics import (
    InfrastructureMetricsPrompts,
)
from src.prompts.infrastructure.infrastructure_resources import (
    InfrastructureResourcesPrompts,
)
from src.prompts.infrastructure.infrastructure_topology import (
    InfrastructureTopologyPrompts,
)


class TestPromptsFunctionality:
    """Test cases for prompts functionality."""

    def test_application_alerts_prompts(self):
        """Test that application alerts prompts are available."""
        prompts = ApplicationAlertsPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        # Check that each prompt has a name and function
        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')
            assert hasattr(prompt_func, 'description')

    def test_application_catalog_prompts(self):
        """Test that application catalog prompts are available."""
        prompts = ApplicationCatalogPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_application_metrics_prompts(self):
        """Test that application metrics prompts are available."""
        prompts = ApplicationMetricsPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_application_resources_prompts(self):
        """Test that application resources prompts are available."""
        prompts = ApplicationResourcesPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_application_settings_prompts(self):
        """Test that application settings prompts are available."""
        prompts = ApplicationSettingsPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_application_topology_prompts(self):
        """Test that application topology prompts are available."""
        prompts = ApplicationTopologyPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_infrastructure_catalog_prompts(self):
        """Test that infrastructure catalog prompts are available."""
        prompts = InfrastructureCatalogPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_infrastructure_metrics_prompts(self):
        """Test that infrastructure metrics prompts are available."""
        prompts = InfrastructureMetricsPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_infrastructure_resources_prompts(self):
        """Test that infrastructure resources prompts are available."""
        prompts = InfrastructureResourcesPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_infrastructure_topology_prompts(self):
        """Test that infrastructure topology prompts are available."""
        prompts = InfrastructureTopologyPrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_infrastructure_analyze_prompts(self):
        """Test that infrastructure analysis prompts are available."""
        prompts = InfrastructureAnalyzePrompts.get_prompts()

        assert isinstance(prompts, list)
        assert len(prompts) > 0

        for prompt_name, prompt_func in prompts:
            assert isinstance(prompt_name, str)
            assert hasattr(prompt_func, 'name')

    def test_all_prompt_categories(self):
        """Test that all prompt categories are available."""
        categories = [
            ApplicationAlertsPrompts,
            ApplicationCatalogPrompts,
            ApplicationMetricsPrompts,
            ApplicationResourcesPrompts,
            ApplicationSettingsPrompts,
            ApplicationTopologyPrompts,
            InfrastructureCatalogPrompts,
            InfrastructureMetricsPrompts,
            InfrastructureResourcesPrompts,
            InfrastructureTopologyPrompts,
            InfrastructureAnalyzePrompts
        ]

        for category in categories:
            prompts = category.get_prompts()
            assert isinstance(prompts, list)
            assert len(prompts) > 0

    def test_prompt_function_descriptions(self):
        """Test that prompt functions have descriptions."""
        # Test a few specific prompts
        alerts_prompts = ApplicationAlertsPrompts.get_prompts()
        for _prompt_name, prompt_func in alerts_prompts:
            # Check that the function has a description
            assert prompt_func.description is not None
            assert len(prompt_func.description.strip()) > 0

    def test_prompt_function_names(self):
        """Test that prompt functions have meaningful names."""
        alerts_prompts = ApplicationAlertsPrompts.get_prompts()
        for _prompt_name, prompt_func in alerts_prompts:
            # Check that the function name is descriptive
            assert len(prompt_func.name) > 0
            assert '_' in prompt_func.name  # Should have descriptive naming
