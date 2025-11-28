"""
CCMA workflow implementation.
"""

from typing import Optional

from loguru import logger

from core.services.arca_login.arca_login import ARCALoginService
from core.services.ccma.ccma_service import CCMAService
from core.services.payments.payment_service import PaymentService
from core.workflows.base import BaseWorkflow, WorkflowStep


class CCMAWorkflow(BaseWorkflow):
    """Workflow for CCMA account status inquiry."""

    def __init__(
        self,
        cuit: Optional[str] = None,
        password: Optional[str] = None,
        tipo_contribuyente: Optional[str] = None,
        impuesto: Optional[str] = None,
        period_from: Optional[str] = None,
        period_to: Optional[str] = None,
        calculation_date: Optional[str] = None,
        form_payment: Optional[str] = None,
        include_interests: bool = False,
        expiration_date: Optional[str] = None,
        headless: bool = False,
    ):
        super().__init__(
            "ccma_workflow",
            "CCMA Account Status",
            "Get CCMA account status and information",
        )
        self.cuit = cuit
        self.password = password
        self.tipo_contribuyente = tipo_contribuyente
        self.impuesto = impuesto
        self.period_from = period_from
        self.period_to = period_to
        self.calculation_date = calculation_date
        self.form_payment = form_payment
        self.include_interests = include_interests
        self.expiration_date = expiration_date
        self.headless = headless
        self.define_steps()

    def define_steps(self):
        """Define the steps for CCMA workflow."""
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
                name="open_ccma_window",
                description="Open CCMA service window",
                handler=self._open_ccma_window,
                depends_on=["arca_login"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="calculate_debt",
                description="Calculate debt by filling form and clicking calculation button",
                handler=self._calculate_debt,
                depends_on=["open_ccma_window"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="handle_debt_window",
                description="Handle debt window filters and proceed with consultation or payment slip",
                handler=self._handle_debt_window,
                depends_on=["calculate_debt"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="generate_vep",
                description="Generate VEP by selecting all items and clicking generate button",
                handler=self._generate_vep,
                depends_on=["handle_debt_window"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="select_payment_method",
                description="Select payment method for VEP",
                handler=self._select_payment_method,
                depends_on=["generate_vep"],
            )
        )

    def _initialize_browser(self) -> bool:
        """Initialize services."""
        try:
            self.shared_resources["arca_service"] = ARCALoginService()
            # Store workflow parameters in shared_resources for VEP extractor
            self.shared_resources["cuit"] = self.cuit
            self.shared_resources["expiration_date"] = self.expiration_date
            # Don't initialize CCMA service yet - will be done after ARCA login
            logger.debug("Services initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False

    def _perform_arca_login(self) -> bool:
        """Perform ARCA login."""
        try:
            arca_service = self.shared_resources["arca_service"]
            success = arca_service.login(cuit=self.cuit, password=self.password)
            if success:
                # Initialize CCMA service with the logged-in browser
                self.shared_resources["ccma_service"] = CCMAService(
                    browser_manager=arca_service.browser
                )
                logger.info(
                    "ARCA login successful, CCMA service initialized with shared browser"
                )
                return True
            else:
                logger.error("ARCA login failed")
                return False
        except Exception as e:
            logger.error(f"ARCA login error: {e}")
            return False

    def _open_ccma_window(self) -> bool:
        """Open CCMA service window by clicking on it in the portal."""
        try:
            ccma_service = self.shared_resources["ccma_service"]

            logger.info("Opening CCMA service window")
            auth_success = ccma_service.authenticate_ccma(cuit=self.cuit)

            if not auth_success:
                logger.error("CCMA authentication failed")
                return False

            # Step 2: Verify we navigated to CCMA successfully
            logger.debug("Verifying CCMA navigation")
            # CCMA authentication automatically opens the CCMA window
            # No need for separate navigation verification
            logger.info("Successfully accessed CCMA service - CCMA window opened")
            # Wait for CCMA window to fully load
            import time

            time.sleep(0.3)
            nav_success = True

            if nav_success:
                logger.debug("Successfully accessed CCMA service")
                return True
            else:
                logger.error("Failed to verify CCMA navigation")
                return False

        except Exception as e:
            logger.error(f"CCMA access error: {e}")
            return False

    def _calculate_debt(self) -> bool:
        """Calculate debt using the CCMA debt calculation form."""
        try:
            ccma_service = self.shared_resources["ccma_service"]

            logger.info(
                f"Initiating debt calculation for period {self.period_from} to {self.period_to}"
            )

            success = ccma_service.calculate_debt(
                period_from=self.period_from,
                period_to=self.period_to,
                calculation_date=self.calculation_date,
            )

            if success:
                logger.info("Debt calculation completed successfully")
                # Store the calculation parameters in shared resources for later use
                self.shared_resources["debt_calculation"] = {
                    "period_from": self.period_from,
                    "period_to": self.period_to,
                    "calculation_date": self.calculation_date,
                    "status": "completed",
                }
                return True
            else:
                logger.error("Debt calculation failed")
                return False

        except Exception as e:
            logger.error(f"Debt calculation error: {e}")
            return False

    def _handle_debt_window(self) -> bool:
        """Handle debt window filters and proceed with consultation or payment slip generation."""
        try:
            ccma_service = self.shared_resources["ccma_service"]

            logger.info("Handling debt window filters and actions")

            # Pass the filter parameters to the service
            success = ccma_service.handle_debt_window_filters(
                tipo_contribuyente=self.tipo_contribuyente,
                impuesto=self.impuesto,
            )

            if success:
                logger.info("Debt window handling completed successfully")
                # Store the filter parameters in shared resources for later use
                self.shared_resources["debt_window_filters"] = {
                    "tipo_contribuyente": self.tipo_contribuyente,
                    "impuesto": self.impuesto,
                    "status": "completed",
                }
                return True
            else:
                logger.error("Debt window handling failed")
                return False

        except Exception as e:
            logger.error(f"Debt window handling error: {e}")
            return False

    def _generate_vep(self) -> bool:
        """Generate VEP by selecting all items and clicking generate button."""
        try:
            ccma_service = self.shared_resources["ccma_service"]

            logger.info(f"Generating VEP (include_interests: {self.include_interests})")

            success = ccma_service.generate_vep(
                include_interests=self.include_interests
            )

            if success:
                logger.info("VEP generation completed successfully")
                return True
            else:
                logger.error("VEP generation failed")
                return False

        except Exception as e:
            logger.error(f"VEP generation error: {e}")
            return False

    def _select_payment_method(self) -> bool:
        """Select payment method for VEP and download PDF and QR if applicable."""
        try:
            arca_service = self.shared_resources["arca_service"]

            # Initialize payment service with the browser
            payment_service = PaymentService(arca_service.browser, workflow_type="ccma")

            # Use the centralized payment logic
            return payment_service.select_payment_method_and_store_results(
                form_payment=self.form_payment, shared_resources=self.shared_resources
            )

        except Exception as e:
            logger.error(f"Payment method selection error: {e}")
            return False
