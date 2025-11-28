"""
Application service for workflow operations following SOLID principles.
Responsible for orchestrating workflow execution use cases.
"""

import asyncio
import uuid
from typing import TYPE_CHECKING, List, Optional

from loguru import logger

from api.exceptions import APITransactionCreationError, APIWorkflowStartupError
from api.models.business import (
    generate_ccma_entry_hash,
    generate_ccma_workflow_hash,
    generate_ddjj_entry_hash,
    generate_ddjj_workflow_hash,
    generate_transaction_hash,
)
from api.models.requests import CCMAWorkflowRequest
from api.models.requests.ddjj_entry import DDJJEntry
from api.utils.ttl_calculator import calculate_ttl_from_entry_expiration

if TYPE_CHECKING:
    from api.models.requests.ddjj_request import DDJJWorkflowRequest

from api.config.settings import settings
from api.models.responses import (
    CCMAWorkflowExecutionResponse,
    DDJJWorkflowExecutionResponse,
    WorkflowExecutionResponse,
    WorkflowStatusResponse,
)
from api.models.responses.ccma_entry_status import CCMAEntryStatus
from api.models.responses.ddjj_entry_status import DDJJEntryStatus
from core.exceptions.password_exceptions import (
    PasswordNotFoundError,
    PasswordServiceNotAvailableError,
)
from core.logging import clear_exchange_id, set_exchange_id
from core.observability import record_ccma_result, record_ddjj_result
from core.orchestrator import WorkflowOrchestrator
from core.services.system.password_service import PasswordService
from core.services.transaction_service import TransactionService
from core.utils.vep_results import process_vep_results
from core.workflows.base import WorkflowStatus


class DuplicateTransactionError(Exception):
    """Raised when a duplicate transaction is detected."""

    def __init__(self, existing_exchange_id: str):
        self.existing_exchange_id = existing_exchange_id
        super().__init__(f"Duplicate transaction found: {existing_exchange_id}")


class WorkflowNotFoundError(Exception):
    """Raised when workflow is not found."""

    pass


class WorkflowApplicationService:
    """
    Application service orchestrating workflow use cases.

    Responsibilities:
    - Coordinate workflow execution
    - Handle business logic for workflow operations
    - Manage workflow monitoring
    """

    def __init__(
        self,
        transaction_service: TransactionService,
        workflow_orchestrator: WorkflowOrchestrator,
    ):
        self._transaction_service = transaction_service
        self._workflow_orchestrator = workflow_orchestrator
        # Initialize password service if FERNET_KEY is available
        self._password_service = None
        if settings.fernet_key:
            try:
                self._password_service = PasswordService(settings.fernet_key)
                logger.info("PasswordService initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize PasswordService: {e}")
        else:
            logger.warning(
                "FERNET_KEY not configured, password lookup will be disabled"
            )

    def _resolve_password(self, cuit: str, provided_password: str = None) -> str:
        """
        Resolve password for a CUIT. If password is provided, use it.
        Otherwise, try to retrieve from password service.

        Args:
            cuit: CUIT to resolve password for
            provided_password: Password provided in request (optional)

        Returns:
            Resolved password

        Raises:
            PasswordServiceNotAvailableError: If password service is not available and no password provided
            PasswordNotFoundError: If CUIT not found in password file and no password provided
        """
        # If password is provided, use it
        if provided_password and provided_password.strip():
            logger.debug(f"Using provided password for CUIT: {cuit}")
            return provided_password.strip()

        # Try to get password from service
        if not self._password_service:
            logger.error(
                f"No password provided and password service not available for CUIT: {cuit}"
            )
            raise PasswordServiceNotAvailableError()

        try:
            password = self._password_service.get_password(cuit)
            logger.info(f"Password retrieved from service for CUIT: {cuit}")
            return password
        except PasswordNotFoundError:
            logger.error(f"Password not found in service for CUIT: {cuit}")
            raise

    def _get_existing_workflow_uuid(
        self, entry_hash: str, current_exchange_id: str
    ) -> Optional[uuid.UUID]:
        """Retrieve the workflow UUID from stored transaction data for duplicate entries."""
        if not entry_hash:
            return None

        transaction_data = self._transaction_service.get_transaction(entry_hash)
        if transaction_data and "request_data" in transaction_data:
            stored_workflow_id = transaction_data["request_data"].get(
                "workflow_exchange_id"
            )
            if stored_workflow_id:
                return uuid.UUID(stored_workflow_id)

        # Fallback: use current workflow UUID if no stored workflow ID found
        return uuid.UUID(current_exchange_id)

    async def execute_ccma_workflow(
        self, request: CCMAWorkflowRequest, headless: bool = False
    ) -> CCMAWorkflowExecutionResponse:
        """Execute CCMA workflow with credentials and multiple entries."""
        # Check for workflow-level duplicate (including form_payment)
        workflow_transaction_hash = generate_ccma_workflow_hash(request)
        existing_workflow_id = await self._transaction_service.check_duplicate(
            workflow_transaction_hash
        )
        if existing_workflow_id:
            raise DuplicateTransactionError(existing_workflow_id)

        # Extract entries and credentials from request
        ccma_entries = request.entries
        cuit = request.credentials.cuit

        # Resolve password (from request or password service)
        password = self._resolve_password(cuit, request.credentials.password)

        # Generate exchange_id early for use in duplicate checking
        exchange_id = str(uuid.uuid4())

        processed_entries = []
        duplicate_entries = []

        # Process each entry for duplicates
        for entry in ccma_entries:
            transaction_hash = generate_ccma_entry_hash(entry)

            # Check for duplicate
            existing_exchange_id = await self._transaction_service.check_duplicate(
                transaction_hash
            )

            # For duplicates, retrieve the workflow UUID from the stored transaction data
            existing_workflow_id = self._get_existing_workflow_uuid(
                existing_exchange_id, exchange_id
            )

            entry_status = CCMAEntryStatus(
                period_from=entry.period_from,
                period_to=entry.period_to,
                calculation_date=entry.calculation_date,
                taxpayer_type=entry.taxpayer_type,
                tax_type=entry.tax_type,
                transaction_hash=transaction_hash,
                status="duplicate" if existing_exchange_id else "new",
                existing_exchange_id=existing_workflow_id,
            )

            if existing_exchange_id:
                duplicate_entries.append(entry_status)
            else:
                processed_entries.append(entry_status)

        # If no new entries to process, return response with duplicates only
        if not processed_entries:
            return CCMAWorkflowExecutionResponse(
                exchange_id=None,
                processed_entries=processed_entries,
                duplicate_entries=duplicate_entries,
                vep_file_path=None,
                total_entries=len(ccma_entries),
                processed_count=0,
                duplicate_count=len(duplicate_entries),
            )

        # Create workflow for new entries
        # exchange_id already created above for duplicate checking

        # Create individual transactions for each new entry with their specific TTL
        new_entries = [
            entry
            for entry, status in zip(ccma_entries, processed_entries)
            if status.status == "new"
        ]

        for entry in new_entries:
            entry_ttl = calculate_ttl_from_entry_expiration(entry.expiration_date)
            entry_hash = generate_ccma_entry_hash(entry)

            success = await self._transaction_service.create_transaction(
                exchange_id=entry_hash,  # Use entry hash as unique storage key
                transaction_hash=entry_hash,
                request_data={
                    "entry": entry.dict(),
                    "workflow_exchange_id": exchange_id,  # Store workflow UUID as metadata
                },
                ttl_seconds=entry_ttl,
            )

            if not success:
                raise APITransactionCreationError(
                    message=f"Failed to create transaction for entry",
                    details={
                        "workflow_type": "ccma_workflow",
                        "entry_hash": entry_hash,
                        "entry_data": entry.dict(),
                    },
                )

        # new_entries already extracted above

        # Use workflow hash for monitoring
        primary_transaction_hash = workflow_transaction_hash

        # Process each entry individually with separate workflow instances
        workflow_started_count = 0

        for entry in new_entries:
            # Create workflow params for this specific entry
            workflow_params = {
                "cuit": cuit,
                "password": password,
                "headless": headless,
                "tipo_contribuyente": entry.taxpayer_type,
                "impuesto": entry.tax_type,
                "period_from": entry.period_from,
                "period_to": entry.period_to,
                "calculation_date": entry.calculation_date,
                "form_payment": entry.form_payment,
                "include_interests": entry.include_interests,
                "expiration_date": entry.expiration_date,
            }

            # Start workflow for this entry
            workflow_started = await self._workflow_orchestrator.execute_workflow_async(
                workflow_type="ccma_workflow",
                workflow_params=workflow_params,
                exchange_id=uuid.UUID(exchange_id),
            )

            if workflow_started:
                workflow_started_count += 1
                logger.info(
                    f"Started CCMA workflow for entry {entry.period_from}-{entry.period_to}"
                )
            else:
                logger.error(
                    f"Failed to start CCMA workflow for entry {entry.period_from}-{entry.period_to}"
                )

        # Check if at least one workflow started successfully
        if workflow_started_count == 0:
            await self._transaction_service.set_workflow_status(
                exchange_id, WorkflowStatus.FAILED
            )
            raise APIWorkflowStartupError(
                message="Failed to start any workflows",
                details={
                    "workflow_type": "ccma_workflow",
                    "exchange_id": exchange_id,
                    "total_entries": len(new_entries),
                },
            )

        logger.info(
            f"Started {workflow_started_count}/{len(new_entries)} CCMA workflows successfully"
        )

        # Update status to running
        await self._transaction_service.set_workflow_status(
            exchange_id, WorkflowStatus.RUNNING
        )

        # Start monitoring
        asyncio.create_task(
            self._monitor_workflow_completion(exchange_id, primary_transaction_hash)
        )

        return CCMAWorkflowExecutionResponse(
            exchange_id=uuid.UUID(exchange_id),
            processed_entries=processed_entries,
            duplicate_entries=duplicate_entries,
            vep_file_path=None,  # Will be populated when workflow completes
            total_entries=len(ccma_entries),
            processed_count=len(processed_entries),
            duplicate_count=len(duplicate_entries),
        )

    async def execute_ddjj_workflow(
        self, request: "DDJJWorkflowRequest", headless: bool = False
    ) -> DDJJWorkflowExecutionResponse:
        """Execute DDJJ workflow with credentials and multiple entries."""
        # Check for workflow-level duplicate (including form_payment)
        workflow_transaction_hash = generate_ddjj_workflow_hash(request)
        existing_workflow_id = await self._transaction_service.check_duplicate(
            workflow_transaction_hash
        )
        if existing_workflow_id:
            raise DuplicateTransactionError(existing_workflow_id)

        # Extract entries and credentials from request
        ddjj_entries = request.entries
        cuit = request.credentials.cuit

        # Resolve password (from request or password service)
        password = self._resolve_password(cuit, request.credentials.password)

        # Generate exchange_id early for use in duplicate checking
        exchange_id = str(uuid.uuid4())

        processed_entries = []
        duplicate_entries = []

        # Process each entry for duplicates
        for entry in ddjj_entries:
            transaction_hash = generate_ddjj_entry_hash(entry)

            # Check for duplicate
            existing_exchange_id = await self._transaction_service.check_duplicate(
                transaction_hash
            )

            # For duplicates, retrieve the workflow UUID from the stored transaction data
            existing_workflow_id = self._get_existing_workflow_uuid(
                existing_exchange_id, exchange_id
            )

            entry_status = DDJJEntryStatus(
                cuit=entry.cuit,
                transaction_hash=transaction_hash,
                status="duplicate" if existing_exchange_id else "new",
                existing_exchange_id=existing_workflow_id,
            )

            if existing_exchange_id:
                duplicate_entries.append(entry_status)
            else:
                processed_entries.append(entry_status)

        # If no new entries to process, return response with duplicates only
        if not processed_entries:
            return DDJJWorkflowExecutionResponse(
                exchange_id=None,
                processed_entries=processed_entries,
                duplicate_entries=duplicate_entries,
                vep_file_path=None,
                total_entries=len(ddjj_entries),
                processed_count=0,
                duplicate_count=len(duplicate_entries),
            )

        # Create workflow for new entries
        # exchange_id already created above for duplicate checking

        # Create individual transactions for each new entry with their specific TTL
        new_entries = [
            entry
            for entry, status in zip(ddjj_entries, processed_entries)
            if status.status == "new"
        ]

        for entry in new_entries:
            entry_ttl = calculate_ttl_from_entry_expiration(entry.expiration_date)
            entry_hash = generate_ddjj_entry_hash(entry)

            success = await self._transaction_service.create_transaction(
                exchange_id=entry_hash,  # Use entry hash as unique storage key
                transaction_hash=entry_hash,
                request_data={
                    "entry": entry.dict(),
                    "workflow_exchange_id": exchange_id,  # Store workflow UUID as metadata
                },
                ttl_seconds=entry_ttl,
            )

            if not success:
                raise APITransactionCreationError(
                    message=f"Failed to create transaction for entry",
                    details={
                        "workflow_type": "ddjj_workflow",
                        "entry_hash": entry_hash,
                        "entry_data": entry.dict(),
                    },
                )

        # new_entries already extracted above

        # Use workflow hash for monitoring
        primary_transaction_hash = workflow_transaction_hash

        # Convert to workflow params directly
        workflow_params = {
            "vep_data": new_entries,
            "headless": headless,
            "cuit": cuit,
            "password": password,
        }

        # Start workflow
        workflow_started = await self._workflow_orchestrator.execute_workflow_async(
            workflow_type="ddjj_workflow",
            workflow_params=workflow_params,
            exchange_id=uuid.UUID(exchange_id),
        )

        if not workflow_started:
            await self._transaction_service.set_workflow_status(
                exchange_id, WorkflowStatus.FAILED
            )
            raise APIWorkflowStartupError(
                message="Failed to start workflow",
                details={"workflow_type": "ddjj_workflow", "exchange_id": exchange_id},
            )

        # Update status to running
        await self._transaction_service.set_workflow_status(
            exchange_id, WorkflowStatus.RUNNING
        )

        # Start monitoring
        asyncio.create_task(
            self._monitor_workflow_completion(exchange_id, primary_transaction_hash)
        )

        return DDJJWorkflowExecutionResponse(
            exchange_id=uuid.UUID(exchange_id),
            processed_entries=processed_entries,
            duplicate_entries=duplicate_entries,
            vep_file_path=None,  # Will be populated when workflow completes
            total_entries=len(ddjj_entries),
            processed_count=len(processed_entries),
            duplicate_count=len(duplicate_entries),
        )

    def get_workflow_status(self, exchange_id: uuid.UUID) -> WorkflowStatusResponse:
        """Get workflow status use case. Raises exceptions on errors."""
        exchange_str = str(exchange_id)
        transaction_data = self._transaction_service.get_transaction(exchange_str)
        if not transaction_data:
            raise WorkflowNotFoundError(f"Workflow not found: {exchange_id}")

        # Status is now consistently stored in transaction data
        status_value = transaction_data.get("status", WorkflowStatus.CREATED.value)

        # Get results and ensure VEP processing is applied if needed
        results = transaction_data.get("results")
        if results:
            # Check if results contain nested workflow_result structure
            workflow_results = results.get("workflow_result", {}).get("results")
            if (
                workflow_results
                and "vep_pdf_path" in workflow_results
                and not any(key in workflow_results for key in ["pdf", "png"])
            ):
                # Process nested workflow results and merge directly into workflow results
                processed_vep = process_vep_results(
                    workflow_results, exchange_id=exchange_str
                )

                # Remove redundant file path fields and exchange_id (already in top level)
                workflow_results.pop("vep_pdf_filename", None)
                workflow_results.pop("vep_pdf_path", None)
                workflow_results.pop("vep_qr_filename", None)
                workflow_results.pop("vep_qr_path", None)
                processed_vep.pop("exchange_id", None)

                # Add processed data directly to workflow results
                workflow_results.update(processed_vep)
            # Also check top-level results for backward compatibility
            elif "vep_pdf_path" in results and not any(
                key in results for key in ["pdf", "png"]
            ):
                results = process_vep_results(results, exchange_id=exchange_str)

        return WorkflowStatusResponse(
            exchange_id=exchange_id,
            status=status_value,
            started_at=transaction_data.get("started_at"),
            completed_at=transaction_data.get("completed_at"),
            results=results,
            errors=transaction_data.get("errors"),
        )

    async def _monitor_workflow_completion(
        self, exchange_id: str, transaction_hash: str
    ):
        """Monitor workflow completion and update results."""
        set_exchange_id(exchange_id)
        try:

            # Wait for completion - check status instead of separate running state
            while True:
                transaction_data = self._transaction_service.get_transaction(
                    exchange_id
                )
                if not transaction_data:
                    break

                current_status = transaction_data.get("status", "")
                if WorkflowStatus.is_terminal(current_status):
                    break

                await asyncio.sleep(1)

            # Get final transaction data
            transaction_data = self._transaction_service.get_transaction(exchange_id)
            if not transaction_data:
                return

            request_data = transaction_data.get("request_data", {})

            # Determine workflow type for business metrics
            workflow_type = (
                "ccma"
                if "cuit" in request_data and "period_from" in request_data
                else "ddjj"
            )

            # Process completion
            if "_workflow_result" in request_data:
                workflow_result = request_data["_workflow_result"]

                if workflow_result.status.value == "COMPLETED":
                    # Record final business outcome success
                    if workflow_type == "ccma":
                        record_ccma_result("success")
                    else:
                        record_ddjj_result("success")

                    processed_results = process_vep_results(
                        workflow_result.results,
                        exchange_id=exchange_id,
                        transaction_hash=transaction_hash,
                    )

                    await self._transaction_service.update_status(
                        exchange_id=exchange_id,
                        status=WorkflowStatus.COMPLETED.value,
                        results=processed_results,
                    )
                else:
                    # Record final business outcome failure
                    if workflow_type == "ccma":
                        record_ccma_result("failed")
                    else:
                        record_ddjj_result("failed")

                    await self._transaction_service.update_status(
                        exchange_id=exchange_id,
                        status=WorkflowStatus.FAILED.value,
                        results={"errors": workflow_result.errors},
                    )
            elif "_workflow_error" in request_data:
                await self._transaction_service.update_status(
                    exchange_id=exchange_id,
                    status=WorkflowStatus.FAILED.value,
                    results={
                        "errors": {"workflow_error": request_data["_workflow_error"]}
                    },
                )

        except Exception as e:
            logger.error(f"Error monitoring workflow {exchange_id}: {e}")
            # Mark as failed if monitoring fails
            try:
                await self._transaction_service.update_status(
                    exchange_id=exchange_id,
                    status=WorkflowStatus.FAILED.value,
                    results={"errors": {"monitoring_error": str(e)}},
                )
            except:
                pass  # Best effort
        finally:
            clear_exchange_id()
