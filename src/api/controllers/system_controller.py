"""
System information controller following Single Responsibility Principle.
"""

from fastapi import APIRouter, HTTPException, status

from api.models.responses import WorkflowListResponse
from api.models.responses.system_responses import RetryResponse

router = APIRouter(tags=["system"])


@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="List available workflows",
    description="Get list of all available workflow types",
)
def list_workflows():
    """List available workflows."""
    from core.workflows.registry import workflow_registry

    workflows = []
    available = workflow_registry.list_available_workflows()

    for workflow_id, workflow_class in available.items():
        temp_workflow = workflow_class()
        workflows.append(
            {
                "id": temp_workflow.workflow_id,
                "name": temp_workflow.name,
                "description": temp_workflow.description,
                "status": "ready",
                "steps": str(len(temp_workflow.steps)),
            }
        )

    return WorkflowListResponse(workflows=workflows, count=len(workflows))


@router.post(
    "/retry",
    response_model=RetryResponse,
    summary="Retry failed transactions",
    description="Retry transactions that failed due to retryable errors",
)
async def retry_failed_transactions(max_retries: int = 3):
    """Retry failed transactions with retryable errors."""
    try:
        # Import here to avoid circular imports
        from api.controllers.workflow_controller import (
            transaction_service,
            workflow_orchestrator,
        )
        from core.services.retry_service import RetryService

        # Initialize retry service
        retry_service = RetryService(transaction_service, workflow_orchestrator)

        # Process retryable transactions
        stats = await retry_service.process_retryable_transactions(max_retries)

        return RetryResponse(
            message=f"Processed {stats['total_found']} retryable transactions, "
            f"{stats['retry_initiated']} retried successfully",
            total_found=stats["total_found"],
            retry_initiated=stats["retry_initiated"],
            retry_failed=stats["retry_failed"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing retryable transactions: {str(e)}",
        )
