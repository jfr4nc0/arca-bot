"""
Payment service for handling payment method selection and result processing.
Encapsulates common payment logic used across different workflows.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from loguru import logger
from selenium.webdriver.common.by import By

from core.config import config
from core.observability import record_payment_by_type
from core.services.google_drive.drive_service import GoogleDriveService
from core.services.payments.payment_handler import PaymentHandler
from core.services.vep.vep_data_extractor import VEPDataExtractor
from core.services.vep.vep_pdf_generator import VepPdfGenerator


class PaymentService:
    """
    Service for handling payment method selection and result processing.

    Provides a unified interface for payment operations across different workflows
    and handles the common logic for processing payment results and file storage.
    """

    def __init__(self, browser_manager, workflow_type: Optional[str] = None):
        """
        Initialize payment service with browser manager.

        Args:
            browser_manager: Browser manager instance for payment operations
            workflow_type: Type of workflow (ccma, ddjj) for timing-specific behavior
        """
        self.payment_handler = PaymentHandler(browser_manager, workflow_type)
        self._browser = browser_manager
        self.workflow_type = workflow_type or "workflow"
        drive_config = config.google_drive
        self._drive_upload_active = drive_config.enabled
        self._drive_service: Optional[GoogleDriveService] = None

        if self._drive_upload_active:
            try:
                drive_service = GoogleDriveService(
                    credentials_path=drive_config.credentials_path,
                    token_path=drive_config.token_path,
                )
                if drive_service.is_available():
                    self._drive_service = drive_service
                else:
                    logger.warning("Google Drive service unavailable; uploads disabled")
                    self._drive_upload_active = False
            except Exception as exc:
                logger.error(f"Failed to initialize Google Drive service: {exc}")
                self._drive_upload_active = False

    def select_payment_method_and_store_results(
        self, form_payment: Optional[str], shared_resources: Dict[str, Any]
    ) -> bool:
        """
        Complete payment flow: select method, download PDF, extract QR/URLs, and store results.

        Args:
            form_payment: Payment method to select (qr, link, etc.)
            shared_resources: Dictionary to store result files and paths

        Returns:
            True if payment method selection and file processing succeeded, False otherwise
        """
        try:
            logger.info(
                "Starting complete payment method selection and file processing"
            )

            # Use default payment method if none specified
            if not form_payment:
                form_payment = self.payment_handler.get_default_payment_method()
                logger.debug(
                    f"No payment method specified, using default: {form_payment}"
                )

            # Step 1: Select payment method
            if not self.payment_handler.select_payment_method(method=form_payment):
                # Record payment method selection failure metric
                record_payment_by_type(form_payment, "failed")
                logger.error("Payment method selection failed")
                return False

            # Record payment method selection success metric
            record_payment_by_type(form_payment, "success")
            logger.info("Payment method selected successfully")

            # Step 2: Generate PDF and extract additional data
            file_info = self._generate_pdf_and_extract_data(
                form_payment, shared_resources
            )
            if file_info:
                logger.debug(f"Payment process completed with results: {file_info}")
                return self._process_payment_result(file_info, shared_resources)
            else:
                logger.warning(
                    "No file data could be extracted, but payment method was selected"
                )
                return True

        except Exception as e:
            logger.error(f"Payment method selection and processing error: {e}")
            return False

    def _process_payment_result(
        self, result: Union[str, dict, bool], shared_resources: Dict[str, Any]
    ) -> bool:
        """
        Process payment method selection result and store files in shared resources.

        Args:
            result: Result from payment method selection
            shared_resources: Dictionary to store result files and paths

        Returns:
            True if result processing succeeded
        """
        if isinstance(result, str):
            # Result is a PDF filename (legacy format)
            logger.info(
                f"Payment method selection and PDF download completed successfully: {result}"
            )
            self._store_pdf_result(result, shared_resources)
            return True

        elif isinstance(result, dict):
            # Result is a dict with file information (new format)
            logger.info(
                "Payment method selection and file downloads completed successfully"
            )
            self._store_dict_result(result, shared_resources)
            return True

        else:
            # Result is True (success but no files downloaded)
            logger.debug("Payment method selection completed successfully")
            return True

    def _store_pdf_result(
        self, pdf_filename: str, shared_resources: Dict[str, Any]
    ) -> None:
        """
        Store PDF result in shared resources (legacy format).

        Args:
            pdf_filename: Name of the PDF file
            shared_resources: Dictionary to store the result
        """
        shared_resources["vep_pdf_filename"] = pdf_filename
        shared_resources["vep_pdf_path"] = f"resources/pdf/{pdf_filename}"
        self._upload_generated_file(
            shared_resources.get("vep_pdf_path"), "pdf", shared_resources
        )

    def _store_dict_result(
        self, result: dict, shared_resources: Dict[str, Any]
    ) -> None:
        """
        Store dictionary result in shared resources (new format).

        Args:
            result: Dictionary containing file information
            shared_resources: Dictionary to store the results
        """
        # Store PDF filename and path if available
        if "pdf_filename" in result:
            shared_resources["vep_pdf_filename"] = result["pdf_filename"]
            shared_resources["vep_pdf_path"] = f"resources/pdf/{result['pdf_filename']}"
            self._upload_generated_file(
                shared_resources.get("vep_pdf_path"), "pdf", shared_resources
            )

        # Store QR filename and path if available
        if "qr_filename" in result:
            shared_resources["vep_qr_filename"] = result["qr_filename"]
            shared_resources["vep_qr_path"] = f"resources/qr/{result['qr_filename']}"
            self._upload_generated_file(
                shared_resources.get("vep_qr_path"), "qr", shared_resources
            )

        # Store payment URL if available (no file persistence for URLs)
        if "payment_url" in result:
            shared_resources["payment_url"] = result["payment_url"]

    def _upload_generated_file(
        self, file_path: Optional[str], file_type: str, shared_resources: Dict[str, Any]
    ) -> None:
        """
        Upload generated artifacts to Google Drive when enabled.

        Args:
            file_path: Local file path.
            file_type: Logical type (pdf, qr, etc.).
            shared_resources: Workflow shared resources for exchange metadata.
        """
        if not self._drive_upload_active or not file_path or not self._drive_service:
            return

        path_obj = Path(file_path)
        if not path_obj.exists():
            logger.warning(f"Drive upload skipped: file not found ({file_path})")
            return

        exchange_id = shared_resources.get("exchange_id")
        if not exchange_id:
            raise RuntimeError(
                "exchange_id missing from shared_resources; it must be set by the orchestrator"
            )
        workflow_type = self.workflow_type or "workflow"

        try:
            file_id = self._drive_service.upload_workflow_file(
                file_path=str(path_obj),
                workflow_type=workflow_type,
                exchange_id=exchange_id,
                file_type=file_type,
                custom_name=path_obj.name,
            )
            if file_id:
                logger.info(
                    f"Uploaded {path_obj.name} to Google Drive "
                    f"(workflow={workflow_type}, exchange_id={exchange_id})"
                )
        except Exception as exc:
            logger.error(f"Failed to upload {path_obj} to Google Drive: {exc}")

    def validate_payment_method(self, method: Optional[str]) -> bool:
        """
        Validate if the payment method is supported.

        Args:
            method: Payment method to validate

        Returns:
            True if method is valid, False otherwise
        """
        return self.payment_handler.validate_payment_method(method)

    def get_default_payment_method(self) -> str:
        """
        Get the default payment method.

        Returns:
            Default payment method string
        """
        return self.payment_handler.get_default_payment_method()

    def _generate_pdf_and_extract_data(
        self, payment_method: str, shared_resources: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """
        Generate VEP PDF using VEP data and extract additional data based on payment method.

        Args:
            payment_method: The selected payment method
            shared_resources: Shared resources containing VEP data

        Returns:
            Dict with filenames of generated/extracted files, or None if failed
        """
        try:
            logger.info(
                f"Starting VEP PDF generation and data extraction for {payment_method}"
            )

            # Generate base filename from current timestamp for correlation
            timestamp = int(time.time())
            base_filename = f"arca_vep_{timestamp}"

            # Step 1: Extract data based on payment method (QR/URLs)
            qr_filename = None
            payment_url = None
            # Define URL-based payment methods
            url_payment_methods = [
                "link",
                "pago_mis_cuentas",
                "inter_banking",
                "xn_group",
            ]

            if payment_method in ["qr"] + url_payment_methods:
                logger.debug(f"Extracting {payment_method} data")
                extracted_data = self.payment_handler.extract_payment_data(
                    payment_method, base_filename
                )
                if extracted_data:
                    logger.debug(f"{payment_method} data extracted: {extracted_data}")
                    # Store QR filename if this is a QR payment method
                    if payment_method == "qr":
                        qr_filename = extracted_data
                    # Store payment URL if this is a URL-based payment method
                    elif payment_method in url_payment_methods:
                        payment_url = extracted_data
                else:
                    logger.warning(f"{payment_method} data extraction failed")

            # Step 2: Generate PDF using VEP data
            pdf_filename = self._generate_vep_pdf(shared_resources, base_filename)

            # Step 3: Build result dictionary with available data
            result = {}

            # Add PDF filename if generation succeeded
            if pdf_filename:
                result["pdf_filename"] = pdf_filename
                logger.info(f"✅ PDF generation completed: {pdf_filename}")
            else:
                logger.error("❌ PDF generation failed")

            # Add QR filename if extraction succeeded
            if qr_filename:
                result["qr_filename"] = qr_filename
                logger.info(f"✅ QR extraction completed: {qr_filename}")

            # Add payment URL if extraction succeeded
            if payment_url:
                result["payment_url"] = payment_url
                logger.info("✅ Payment URL extraction completed")

            # Return partial results even if PDF generation failed
            if result:
                logger.debug(f"Returning available results: {result}")
                return result
            else:
                logger.error(
                    "❌ No data could be extracted (PDF, QR, and URL all failed)"
                )
                return None

        except Exception as e:
            logger.error(f"Error during PDF generation and data extraction: {e}")
            return None

    def _generate_vep_pdf(
        self, shared_resources: Dict[str, Any], base_filename: str
    ) -> Optional[str]:
        """
        Generate VEP PDF using available VEP data.

        Args:
            shared_resources: Shared resources containing VEP data
            base_filename: Base filename for the PDF

        Returns:
            PDF filename if generated successfully, None otherwise
        """
        try:
            logger.info("Generating VEP PDF from available data")

            # Initialize VEP data extractor
            vep_extractor = VEPDataExtractor(shared_resources)
            vep_data = None

            # Strategy 1: Try to extract from VEP file (DDJJ workflow)
            vep_file_path = shared_resources.get("vep_file_path")
            if vep_file_path:
                logger.debug(f"Extracting VEP data from file: {vep_file_path}")
                vep_entries = vep_extractor.extract_from_vep_file(vep_file_path)
                if vep_entries:
                    # Use the first entry for PDF generation
                    vep_data = vep_entries[0]
                    logger.debug("Successfully extracted VEP data from file")

            # Strategy 2: Try to extract from web page (CCMA workflow)
            if not vep_data:
                logger.debug("Attempting to extract VEP data from web page")
                vep_data = vep_extractor.extract_from_web_page(self._browser)
                if vep_data:
                    logger.debug("Successfully extracted VEP data from web page")

            if not vep_data:
                logger.error("Could not obtain VEP data for PDF generation")
                return None

            # Ensure PDF directory exists
            pdf_dir = Path("resources/pdf")
            pdf_dir.mkdir(parents=True, exist_ok=True)

            # Generate PDF filename
            pdf_filename = f"{base_filename}.pdf"
            pdf_path = pdf_dir / pdf_filename

            # Generate PDF using VepPdfGenerator
            pdf_generator = VepPdfGenerator(
                nro_vep=getattr(vep_data, "nro_formulario", "1571"),
                cuit=getattr(vep_data, "cuit", "00000000000"),
                periodo=getattr(vep_data, "periodo_fiscal", "202412"),
                items_pago=[
                    {
                        "descripcion": f"CONCEPTO {getattr(vep_data, 'concepto', '19')}",
                        "importe": getattr(vep_data, "importe", 0.0),
                    }
                ],
                organismo_recaudador="ARCA",
                tipo_pago="Monotributo - Pago Mensual",
                concepto=(
                    getattr(vep_data, "concepto", "19"),
                    "",
                ),
                subconcepto=(
                    getattr(vep_data, "sub_concepto", "19"),
                    "",
                ),
                descripcion_reducida=f"VEP-{getattr(vep_data, 'periodo_fiscal', '202412')}",
            )

            # Generate the PDF
            pdf_generator.create_pdf(str(pdf_path))

            if pdf_path.exists():
                logger.info(f"VEP PDF generated successfully: {pdf_filename}")
                return pdf_filename
            else:
                logger.error("PDF file was not created")
                return None

        except Exception as e:
            logger.error(f"Error generating VEP PDF: {e}")
            return None
