"""
arca Login workflow implementation.
"""

from typing import Optional

from loguru import logger

from core.services.arca_login.arca_login import ARCALoginService
from core.workflows.base import BaseWorkflow, WorkflowStep


class ARCALoginWorkflow(BaseWorkflow):
    """Workflow for arca login only."""

    def __init__(self, cuit: Optional[str] = None):
        super().__init__("arca_login", "ARCA Login", "Login to ARCA system")
        self.cuit = cuit
        self.define_steps()

    def define_steps(self):
        """Define the steps for ARCA login workflow."""
        self.add_step(
            WorkflowStep(
                name="initialize_browser",
                description="Initialize browser session",
                handler=self._initialize_browser,
            )
        )

        self.add_step(
            WorkflowStep(
                name="arca_login",
                description="Login to ARCA",
                handler=self._perform_arca_login,
                depends_on=["initialize_browser"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="verify_login",
                description="Verify login success",
                handler=self._verify_login,
                depends_on=["arca_login"],
            )
        )

    def _initialize_browser(self) -> bool:
        """Initialize arca login service."""
        try:
            self.shared_resources["arca_service"] = ARCALoginService()
            logger.debug("Browser initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False

    def _perform_arca_login(self) -> bool:
        """Perform ARCA login."""
        try:
            arca_service = self.shared_resources["arca_service"]
            success = arca_service.login(cuit=self.cuit)
            if success:
                logger.info("ARCA login successful")
                return True
            else:
                logger.error("ARCA login failed")
                return False
        except Exception as e:
            logger.error(f"ARCA login error: {e}")
            return False

    def _verify_login(self) -> bool:
        """Verify login was successful."""
        try:
            arca_service = self.shared_resources["arca_service"]
            if arca_service.is_logged_in():
                logger.info("Login verification successful")
                return True
            else:
                logger.error("Login verification failed")
                return False
        except Exception as e:
            logger.error(f"Login verification error: {e}")
            return False
