"""
Workflow controller handling HTTP requests/responses only.
Following Single Responsibility Principle.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import Field

from api.application.workflow_application_service import (
    DuplicateTransactionError,
    WorkflowApplicationService,
    WorkflowNotFoundError,
)
from api.config.settings import settings
from api.exceptions import APITransactionCreationError, APIWorkflowStartupError
from api.models.business import generate_ddjj_workflow_hash, generate_transaction_hash
from api.models.requests import CCMAWorkflowRequest
from api.models.requests.ddjj_request import DDJJWorkflowRequest
from api.models.responses import DDJJWorkflowExecutionResponse, WorkflowStatusResponse
from api.models.responses.ccma_workflow_response import CCMAWorkflowExecutionResponse
from api.utils.error_utils import handle_duplicate_transaction_error
from core.orchestrator import WorkflowOrchestrator
from core.services.transaction_service import TransactionService

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)

# Simple direct instantiation using core services
transaction_service = TransactionService(
    redis_url=settings.redis_url, use_redis=settings.redis_enabled
)
workflow_orchestrator = WorkflowOrchestrator(transaction_service)
workflow_application_service = WorkflowApplicationService(
    transaction_service, workflow_orchestrator
)


# Helper to inject Selenium scaler from app state
def inject_selenium_scaler(request: Request):
    """
    Inject selenium scaler into orchestrator from app state.
    Called at the start of each workflow endpoint.
    """
    if hasattr(request.app.state, "selenium_scaler"):
        workflow_orchestrator._selenium_scaler = request.app.state.selenium_scaler


@router.post(
    "/ccma/execute",
    response_model=CCMAWorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute CCMA workflow",
    description="Start CCMA workflow execution with multiple VEP entries and return processing status. Handles duplicate detection and entry validation. Requires X-API-Token header for authentication.",
    responses={
        200: {
            "description": "Workflow execution started successfully",
            "model": CCMAWorkflowExecutionResponse,
        },
        401: {
            "description": "Authentication failed - Invalid or missing X-API-Token header"
        },
        422: {
            "description": "Validation error - Invalid request data or missing required fields"
        },
        500: {
            "description": "Internal server error - transaction creation or workflow startup failed"
        },
        503: {
            "description": "Service unavailable - API token not configured or service temporarily unavailable"
        },
    },
)
async def execute_ccma_workflow(
    ccma_request: CCMAWorkflowRequest,
    request: Request,
    headless: bool = Query(False, description="Run browser in headless mode"),
):
    """Execute CCMA workflow - simplified with direct exception handling."""
    try:
        # Inject selenium scaler from app state
        inject_selenium_scaler(request)

        result = await workflow_application_service.execute_ccma_workflow(
            ccma_request, headless
        )

        return result

    except DuplicateTransactionError as e:

        return handle_duplicate_transaction_error(
            generate_transaction_hash(ccma_request), e.existing_exchange_id
        )
    except APITransactionCreationError as e:

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create transaction"
        )
    except APIWorkflowStartupError as e:

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to start workflow"
        )
    except Exception as e:

        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post(
    "/ddjj/execute",
    response_model=DDJJWorkflowExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute DDJJ workflow",
    description="Start DDJJ workflow execution with multiple VEP entries and return processing status. Handles duplicate detection and entry validation. Requires X-API-Token header for authentication.",
    responses={
        200: {
            "description": "Workflow execution started successfully",
            "model": DDJJWorkflowExecutionResponse,
        },
        401: {
            "description": "Authentication failed - Invalid or missing X-API-Token header"
        },
        422: {
            "description": "Validation error - Invalid request data or missing required fields"
        },
        500: {
            "description": "Internal server error - transaction creation or workflow startup failed"
        },
        503: {
            "description": "Service unavailable - API token not configured or service temporarily unavailable"
        },
    },
)
async def execute_ddjj_workflow(
    ddjj_request: DDJJWorkflowRequest,
    request: Request,
    headless: bool = Query(False, description="Run browser in headless mode"),
):
    """Execute DDJJ workflow with credentials and multiple entries."""
    try:
        # Inject selenium scaler from app state
        inject_selenium_scaler(request)

        result = await workflow_application_service.execute_ddjj_workflow(
            ddjj_request, headless
        )

        return result

    except DuplicateTransactionError as e:

        return handle_duplicate_transaction_error(
            generate_ddjj_workflow_hash(ddjj_request), e.existing_exchange_id
        )
    except APITransactionCreationError as e:

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create transaction"
        )
    except APIWorkflowStartupError as e:

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to start workflow"
        )
    except Exception as e:

        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get(
    "/{exchange_id}/status",
    response_model=WorkflowStatusResponse,
    summary="Get workflow status",
    description="Get current status of workflow execution by exchange_id. Returns real-time status, timestamps, results or error details. Requires X-API-Token header for authentication.",
    responses={
        200: {
            "description": "Workflow status retrieved successfully",
            "model": WorkflowStatusResponse,
        },
        401: {
            "description": "Authentication failed - Invalid or missing X-API-Token header"
        },
        404: {"description": "Workflow not found for the given exchange_id"},
        422: {"description": "Validation error - Invalid exchange_id format"},
        503: {
            "description": "Service unavailable - API token not configured or service temporarily unavailable"
        },
    },
)
def get_workflow_status(exchange_id: uuid.UUID):
    """Get workflow status - simplified with direct exception handling."""
    try:

        result = workflow_application_service.get_workflow_status(exchange_id)

        return result

    except WorkflowNotFoundError:

        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
