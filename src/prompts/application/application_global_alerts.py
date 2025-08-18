from typing import List, Optional

from src.prompts import auto_register_prompt


class ApplicationGlobalAlertsPrompts:
    """Class containing application global alerts related prompts"""

    @auto_register_prompt
    @staticmethod
    def app_global_alerts_list(application_id: str, alert_ids: Optional[List[str]] = None) -> str:
        """List all global application alerts for a specific application"""
        alert_ids_str = ", ".join(alert_ids) if alert_ids else "None"
        return f"""
        List global application alerts with filters:
        - Application ID: {application_id}
        - Alert IDs: {alert_ids_str}
        """

    @auto_register_prompt
    @staticmethod
    def app_global_alert_config_enable(id: str) -> str:
        """Enable a Global Smart Alert Configuration by ID"""
        return f"Enable global alert configuration with ID: {id}"

    @auto_register_prompt
    @staticmethod
    def app_global_alert_config_restore(id: str, created: int) -> str:
        """Restore a deleted Global Smart Alert Configuration by ID and creation timestamp"""
        return f"""
        Restore global alert configuration:
        - ID: {id}
        - Created timestamp: {created}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('app_global_alerts_list', cls.app_global_alerts_list),
            ('app_global_alert_config_enable', cls.app_global_alert_config_enable),
            ('app_global_alert_config_restore', cls.app_global_alert_config_restore),
        ]

# Made with Bob
