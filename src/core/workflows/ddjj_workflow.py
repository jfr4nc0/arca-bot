"""
DDJJ workflow implementation.
"""

from typing import List, Optional

from loguru import logger

from api.models.requests.ddjj_entry import DDJJEntry
from core.models.vep_data import VEPData
from core.services.arca_login.arca_login import ARCALoginService
from core.services.ddjj.ddjj_service import DDJJService
from core.services.payments.payment_service import PaymentService
from core.services.vep.vep_file_generator import VEPFileGenerator
from core.workflows.base import BaseWorkflow, WorkflowStep


class DDJJWorkflow(BaseWorkflow):
    """Workflow for DDJJ (Declaraciones Juradas) operations."""

    def __init__(
        self,
        vep_data: Optional[List[DDJJEntry]] = None,
        headless: bool = False,
        cuit: Optional[str] = None,
        password: Optional[str] = None,
    ):
        super().__init__("ddjj_workflow", "DDJJ", "Declaraciones Juradas operations")
        self.cuit = cuit
        self.password = password
        self.vep_data = vep_data or []
        self.headless = headless
        self.define_steps()

    def define_steps(self):
        """Define the steps for DDJJ workflow."""
        self.add_step(
            WorkflowStep(
                name="generate_vep_file",
                description="Generate VEP file from provided data",
                handler=self._generate_vep_file,
            )
        )

        self.add_step(
            WorkflowStep(
                name="arca_authentication",
                description="Initialize browser and authenticate with ARCA",
                handler=self._perform_arca_authentication,
                depends_on=["generate_vep_file"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="open_ddjj_window",
                description="Open DDJJ service window",
                handler=self._open_ddjj_window,
                depends_on=["arca_authentication"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="navigate_to_vep_upload",
                description="Navigate to VEP file upload section",
                handler=self._navigate_to_vep_upload,
                depends_on=["open_ddjj_window"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="upload_vep_file",
                description="Upload the generated VEP file",
                handler=self._upload_vep_file,
                depends_on=["navigate_to_vep_upload"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="generate_vep_from_file",
                description="Generate VEP from the uploaded file",
                handler=self._generate_vep_from_file,
                depends_on=["upload_vep_file"],
            )
        )

        self.add_step(
            WorkflowStep(
                name="process_payments",
                description="Process payment for each VEP entry",
                handler=self._process_payments,
                depends_on=["generate_vep_from_file"],
            )
        )

    def _convert_entries_to_vep_data(self) -> list[VEPData]:
        """Convert entries from vep_data to VEPData instances."""
        vep_entries = []

        # Handle both formats: direct list or wrapped in "entries" key
        entries_list = None
        if isinstance(self.vep_data, list):
            # Direct list format: vep_data = [entry1, entry2, ...]
            entries_list = self.vep_data
        elif isinstance(self.vep_data, dict) and "entries" in self.vep_data:
            # Wrapped format: vep_data = {"entries": [entry1, entry2, ...]}
            entries_list = self.vep_data["entries"]

        if entries_list and isinstance(entries_list, list):
            for entry in entries_list:
                if hasattr(entry, "dict"):
                    # If it's a Pydantic model, convert to dict first
                    entry_dict = entry.dict()
                else:
                    entry_dict = entry

                # Map English field names to Spanish field names for VEPData
                vep_data_dict = {
                    "fecha_expiracion": entry_dict.get("expiration_date"),
                    "nro_formulario": entry_dict.get("form_number"),
                    "cod_tipo_pago": entry_dict.get("payment_type_code"),
                    "cuit": entry_dict.get("cuit"),
                    "concepto": entry_dict.get("concept"),
                    "sub_concepto": entry_dict.get("sub_concept"),
                    "periodo_fiscal": entry_dict.get("fiscal_period"),
                    "importe": entry_dict.get("amount"),
                    "impuesto": entry_dict.get("tax_code"),
                }

                # Create VEPData instance
                vep_data = VEPData(**vep_data_dict)
                vep_entries.append(vep_data)

        return vep_entries

    def _generate_vep_file(self) -> bool:
        """Generate VEP file from provided data."""
        try:
            logger.info("Generating VEP file")

            # Convert entries to VEPData list
            vep_entries = self._convert_entries_to_vep_data()

            if not vep_entries:
                logger.error("No valid VEP entries found")
                return False

            # Initialize VEP file generator
            vep_generator = VEPFileGenerator()

            # Generate VEP file with list of VEPData
            filepath = vep_generator.generate_vep_file(vep_entries)

            if filepath:
                # Store generated VEP file path in shared resources
                self.shared_resources["vep_file_path"] = filepath
                logger.info(f"VEP file generated successfully: {filepath}")
                return True
            else:
                logger.error("Failed to generate VEP file")
                return False

        except Exception as e:
            logger.error(f"VEP file generation error: {e}")
            return False

    def _perform_arca_authentication(self) -> bool:
        """Initialize browser, perform ARCA login, and verify authentication."""
        try:
            # Step 1: Initialize browser session
            logger.info("Initializing browser session")
            self.shared_resources["arca_service"] = ARCALoginService()
            logger.debug("Browser initialized successfully")

            # Step 2: Perform ARCA login
            logger.info("Performing ARCA login")
            arca_service = self.shared_resources["arca_service"]
            success = arca_service.login(cuit=self.cuit, password=self.password)

            if not success:
                logger.error("ARCA login failed")
                return False

            logger.info("ARCA login successful")

            # Step 3: Verify login was successful
            logger.debug("Verifying login status")
            if arca_service.is_logged_in():
                logger.info("ARCA authentication completed successfully")
                return True
            else:
                logger.error("Login verification failed")
                return False

        except Exception as e:
            logger.error(f"ARCA authentication error: {e}")
            return False

    def _open_ddjj_window(self) -> bool:
        """Open DDJJ service window by clicking on it in the portal."""
        try:
            arca_service = self.shared_resources["arca_service"]

            logger.info("Opening DDJJ service window")

            # Initialize DDJJ service with the logged-in browser
            self.shared_resources["ddjj_service"] = DDJJService(
                browser_manager=arca_service.browser
            )

            ddjj_service = self.shared_resources["ddjj_service"]
            auth_success = ddjj_service.authenticate_ddjj(cuit=self.cuit)

            if not auth_success:
                logger.error("DDJJ authentication failed")
                return False

            logger.info("Successfully accessed DDJJ service - DDJJ window opened")

            # Wait for DDJJ window to fully load
            import time

            time.sleep(0.1)

            logger.debug("Successfully accessed DDJJ service")
            return True

        except Exception as e:
            logger.error(f"DDJJ access error: {e}")
            return False

    def _navigate_to_vep_upload(self) -> bool:
        """Navigate to VEP file upload section by clicking accept button, validating URL, and clicking VEP desde Archivo."""
        try:
            ddjj_service = self.shared_resources["ddjj_service"]

            # Step 1: Click accept button on DDJJ page
            logger.debug("Clicking accept button on DDJJ page")
            success = ddjj_service.click_accept_button()
            if not success:
                logger.error("Failed to click accept button")
                return False
            logger.debug("Accept button clicked successfully")

            # Step 2: Click 'VEP desde Archivo' menu item
            logger.debug("Clicking 'VEP desde Archivo' menu item")
            success = ddjj_service.click_vep_desde_archivo()
            if not success:
                logger.error("Failed to click 'VEP desde Archivo' menu item")
                return False
            logger.debug("'VEP desde Archivo' menu item clicked successfully")

            logger.info("Successfully navigated to VEP file upload section")
            return True

        except Exception as e:
            logger.error(f"VEP upload navigation error: {e}")
            return False

    def _upload_vep_file(self) -> bool:
        """Upload the generated VEP file to the upload form."""
        try:
            ddjj_service = self.shared_resources["ddjj_service"]
            vep_file_path = self.shared_resources.get("vep_file_path")

            if not vep_file_path:
                logger.error("No VEP file path found in shared resources")
                return False

            logger.info(f"Uploading VEP file: {vep_file_path}")

            success = ddjj_service.upload_vep_file(vep_file_path)

            if success:
                logger.info("VEP file uploaded successfully")
                return True
            else:
                logger.error("VEP file upload failed")
                return False

        except Exception as e:
            logger.error(f"VEP file upload error: {e}")
            return False

    def _generate_vep_from_file(self) -> bool:
        """Generate VEP from the uploaded file by clicking the generate button."""
        try:
            ddjj_service = self.shared_resources["ddjj_service"]

            logger.info("Generating VEP from uploaded file")

            success = ddjj_service.click_generate_vep_button()

            if success:
                logger.info("VEP generated successfully from uploaded file")
                return True
            else:
                logger.error("Failed to generate VEP from uploaded file")
                return False

        except Exception as e:
            logger.error(f"VEP generation from file error: {e}")
            return False

    def _process_payments(self) -> bool:
        """Process payment for each VEP entry with its specific form_payment method."""
        try:
            arca_service = self.shared_resources["arca_service"]
            payment_service = PaymentService(arca_service.browser, workflow_type="ddjj")

            # Group entries by payment method to optimize processing
            payment_groups = {}
            for entry in self.vep_data:
                payment_method = entry.form_payment
                if payment_method not in payment_groups:
                    payment_groups[payment_method] = []
                payment_groups[payment_method].append(entry)

            # Process each payment method group
            all_success = True
            payment_results = {}

            for form_payment, entries in payment_groups.items():
                logger.info(
                    f"Processing payment method '{form_payment}' for {len(entries)} entries"
                )

                # Process payment for this group
                success = payment_service.select_payment_method_and_store_results(
                    form_payment=form_payment, shared_resources=self.shared_resources
                )

                if success:
                    payment_results[form_payment] = {
                        "status": "success",
                        "entries_count": len(entries),
                        "entry_hashes": [entry.dict() for entry in entries],
                    }
                    logger.info(
                        f"Payment method '{form_payment}' processed successfully"
                    )
                else:
                    payment_results[form_payment] = {
                        "status": "failed",
                        "entries_count": len(entries),
                        "entry_hashes": [entry.dict() for entry in entries],
                    }
                    logger.error(f"Payment method '{form_payment}' processing failed")
                    all_success = False

            # Store combined payment results
            self.shared_resources["payment_results"] = payment_results

            return all_success

        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            return False
