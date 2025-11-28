"""
Workflow orchestrator for managing and executing RPA workflows.
Enhanced with async capabilities and transaction management.
"""

import asyncio
import time
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger

from core.events.workflow_events import WorkflowFinishedEvent
from core.logging import get_exchange_id, set_exchange_id
from core.messaging.kafka_producer import publish_workflow_finished_event
from core.observability import (
    end_workflow_timer,
    record_ccma_result,
    record_ddjj_result,
    record_workflow_step,
    start_workflow_timer,
)
from core.utils.vep_results import process_vep_results
from core.workflows.base import BaseWorkflow, StepStatus, WorkflowResult, WorkflowStatus
from core.workflows.registry import workflow_registry


class WorkflowOrchestrator:
    """Orchestrates the execution of RPA workflows with async capabilities."""

    def __init__(
        self,
        transaction_service: Optional[Any] = None,
        selenium_scaler: Optional[Any] = None,
    ):
        self.workflows: Dict[str, BaseWorkflow] = {}
        self.execution_history: List[WorkflowResult] = []
        self._running_workflows: Dict[UUID, asyncio.Task] = {}
        self._transaction_service = transaction_service
        self._selenium_scaler = selenium_scaler  # Auto-scaler for Selenium nodes

    def register_workflow(self, workflow: BaseWorkflow):
        """Register a workflow with the orchestrator."""
        self.workflows[workflow.workflow_id] = workflow
        logger.debug(f"Workflow registered: {workflow.workflow_id} - {workflow.name}")

    def unregister_workflow(self, workflow_id: str):
        """Unregister a workflow from the orchestrator."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            logger.debug(f"Workflow unregistered: {workflow_id}")

    def list_workflows(self) -> List[Dict[str, str]]:
        """List all registered workflows."""
        return [
            {
                "id": wf.workflow_id,
                "name": wf.name,
                "description": wf.description,
                "status": wf.status.value,
                "steps": len(wf.steps),
            }
            for wf in self.workflows.values()
        ]

    async def execute_workflow_async(
        self, workflow_type: str, workflow_params: Dict[str, Any], exchange_id: UUID
    ) -> bool:
        """Execute workflow asynchronously."""
        try:
            # Start workflow in background task
            task = asyncio.create_task(
                self._execute_workflow_task(workflow_type, workflow_params, exchange_id)
            )
            self._running_workflows[exchange_id] = task
            return True

        except Exception as e:
            logger.error(f"Failed to start workflow {exchange_id}: {e}")
            return False

    def create_workflow(self, workflow_type: str, **params) -> BaseWorkflow:
        """Create workflow instance with given parameters."""
        return workflow_registry.create_workflow(workflow_type, **params)

    async def _execute_workflow_task(
        self, workflow_type: str, workflow_params: Dict[str, Any], exchange_id: UUID
    ):
        """Execute workflow in background task."""
        exchange_id_str = str(exchange_id)
        previous_exchange_id = get_exchange_id()
        set_exchange_id(exchange_id_str)

        try:
            logger.info(f"Starting workflow execution {exchange_id_str}")

            # Scale up Selenium nodes if auto-scaler is enabled
            if self._selenium_scaler:
                logger.info("Ensuring Selenium capacity for workflow execution")
                self._selenium_scaler.ensure_capacity(sessions_needed=1)

            # Update transaction status to running
            if self._transaction_service:
                await self._transaction_service.update_status(
                    exchange_id_str, WorkflowStatus.RUNNING.value
                )

            # Execute workflow synchronously in thread pool
            loop = asyncio.get_event_loop()

            # Filter parameters based on workflow type
            filtered_params = self._filter_workflow_params(
                workflow_type, workflow_params
            )

            # Execute the workflow in a thread pool to avoid blocking
            result = await loop.run_in_executor(
                None,
                self._execute_workflow_sync,
                workflow_type,
                filtered_params,
                exchange_id_str,
            )

            logger.info(
                f"Workflow {exchange_id_str} completed with status: {result.status.value}"
            )

            # Update transaction with result
            if self._transaction_service:
                transaction_data = self._transaction_service.get_transaction(
                    exchange_id_str
                )
                if transaction_data:
                    request_data = transaction_data.get("request_data", {})
                    request_data["_workflow_result"] = result
                    await self._transaction_service.update_status(
                        exchange_id_str,
                        result.status.value,
                        {"workflow_result": result.__dict__},
                    )

        except Exception as e:
            logger.error(f"Workflow execution error {exchange_id_str}: {e}")
            await self._update_transaction_with_error(exchange_id, str(e))
        finally:
            # Clean up task reference
            if exchange_id in self._running_workflows:
                del self._running_workflows[exchange_id]
            set_exchange_id(previous_exchange_id)

    def _execute_workflow_sync(
        self,
        workflow_type: str,
        workflow_params: Dict[str, Any],
        exchange_id: Optional[str] = None,
    ) -> WorkflowResult:
        """Execute workflow synchronously."""
        workflow = self.create_workflow(workflow_type, **workflow_params)
        self.register_workflow(workflow)

        try:
            return self.execute_workflow(workflow.workflow_id, exchange_id=exchange_id)
        finally:
            self.unregister_workflow(workflow.workflow_id)

    def _filter_workflow_params(
        self, workflow_type: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter parameters based on workflow type."""
        if workflow_type == "ccma_workflow":
            # Only pass parameters that CCMAWorkflow constructor expects
            workflow_params = {}

            for key in [
                "cuit",
                "password",
                "headless",
                "form_payment",
                "tipo_contribuyente",
                "impuesto",
                "period_from",
                "period_to",
                "calculation_date",
                "expiration_date",
                "include_interest",
                "form_payment",
            ]:
                if key in params:
                    workflow_params[key] = params[key]

            return workflow_params
        elif workflow_type == "ddjj_workflow":
            # Only pass parameters that DDJJWorkflow constructor expects
            workflow_params = {}

            for key in [
                "cuit",
                "password",
                "headless",
            ]:
                if key in params:
                    workflow_params[key] = params[key]

            if "vep_data" in params:
                workflow_params["vep_data"] = params["vep_data"]

            return workflow_params
        else:
            # For other workflows, pass all parameters
            return params

    async def _update_transaction_with_error(self, exchange_id: UUID, error: str):
        """Update transaction with error status."""
        if self._transaction_service:
            try:
                transaction_data = self._transaction_service.get_transaction(
                    str(exchange_id)
                )
                if transaction_data:
                    request_data = transaction_data.get("request_data", {})
                    request_data["_workflow_error"] = error
                    await self._transaction_service.update_status(
                        str(exchange_id), WorkflowStatus.FAILED.value
                    )
                    logger.info(f"Transaction {exchange_id} updated with error status")
            except Exception as e:
                logger.error(f"Failed to update transaction with error: {e}")

    def execute_workflow(
        self, workflow_id: str, exchange_id: Optional[str] = None, **kwargs
    ) -> WorkflowResult:
        """Execute a specific workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = self.workflows[workflow_id]

        # Determine workflow type for metrics
        workflow_type = (
            "ccma"
            if "ccma" in workflow_id.lower()
            else "ddjj" if "ddjj" in workflow_id.lower() else "unknown"
        )

        # Reset workflow state before execution
        workflow.reset()
        workflow.status = WorkflowStatus.RUNNING
        exchange_id_str = str(exchange_id or workflow.workflow_id)
        previous_exchange_id = get_exchange_id()
        set_exchange_id(exchange_id_str)
        workflow.shared_resources["exchange_id"] = exchange_id_str

        result = WorkflowResult(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            steps_completed=0,
            steps_failed=0,
            total_steps=len(workflow.steps),
            started_at=datetime.now(),
        )

        logger.info(f"Starting workflow: {workflow.name}")

        start_workflow_timer(exchange_id or workflow_id, workflow_type)

        try:
            # Get execution order based on dependencies
            execution_order = workflow.get_step_execution_order()

            # Execute steps in order
            for step_name in execution_order:
                if step_name not in workflow.steps:
                    logger.error(f"Step not found in workflow: {step_name}")
                    continue

                step = workflow.steps[step_name]

                # Check if we should skip this step due to failed required dependencies
                if self._should_skip_step(workflow, step_name):
                    step.status = StepStatus.SKIPPED
                    logger.info(
                        f"Skipping step due to failed dependencies: {step_name}"
                    )
                    continue

                self._execute_step(workflow, step_name, result)

                # If this is a required step and it failed, stop execution
                if step.status == StepStatus.FAILED and step.required:
                    logger.error(
                        f"Required step failed, stopping workflow: {step_name}"
                    )
                    break

            # Determine final status
            failed_required_steps = sum(
                1
                for step in workflow.steps.values()
                if step.status == StepStatus.FAILED and step.required
            )

            if failed_required_steps > 0:
                result.status = WorkflowStatus.FAILED
                workflow.status = WorkflowStatus.FAILED
                # Record business metrics
                if workflow_type == "ccma":
                    record_ccma_result("failed")
                elif workflow_type == "ddjj":
                    record_ddjj_result("failed")
            else:
                result.status = WorkflowStatus.COMPLETED
                workflow.status = WorkflowStatus.COMPLETED
                # Record business metrics
                if workflow_type == "ccma":
                    record_ccma_result("success")
                elif workflow_type == "ddjj":
                    record_ddjj_result("success")

            result.completed_at = datetime.now()
            result.duration = (result.completed_at - result.started_at).total_seconds()

            # End workflow timer
            end_workflow_timer(exchange_id or workflow_id, workflow_type)

            # Collect only specific step results (errors are still included)
            for step_name, step in workflow.steps.items():
                if step.error is not None:
                    result.errors[step_name] = step.error

            # Add only specific shared resources to results (PDF, QR, and payment data)
            allowed_shared_keys = {
                "vep_pdf_filename",
                "vep_pdf_path",
                "vep_qr_filename",
                "vep_qr_path",
                "payment_url",
            }
            for key, value in workflow.shared_resources.items():
                if key in allowed_shared_keys:
                    result.results[key] = value

            logger.info(
                f"Workflow completed: {workflow.name} - Status: {result.status.value}"
            )

            # Publish workflow finished event to Kafka
            self._publish_workflow_finished_event(
                exchange_id or workflow_id, workflow_type, result
            )

        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            logger.error(traceback.format_exc())
            result.status = WorkflowStatus.FAILED
            workflow.status = WorkflowStatus.FAILED
            result.errors["orchestrator"] = str(e)

            # Publish workflow finished event to Kafka (for failures)
            self._publish_workflow_finished_event(
                exchange_id or workflow_id, workflow_type, result
            )

            # Record business metrics for failure
            if workflow_type == "ccma":
                record_ccma_result("failed")
            elif workflow_type == "ddjj":
                record_ddjj_result("failed")

        finally:
            # Cleanup resources
            workflow.cleanup()
            set_exchange_id(previous_exchange_id)

        self.execution_history.append(result)
        return result

    def _publish_workflow_finished_event(
        self, exchange_id: str, workflow_type: str, result: WorkflowResult
    ):
        """Publish workflow finished event to Kafka."""
        try:
            # Create event based on workflow result
            event = WorkflowFinishedEvent(
                exchange_id=exchange_id,
                workflow_type=workflow_type,
                timestamp=datetime.now(),
                success=(result.status == WorkflowStatus.COMPLETED),
            )

            if result.status == WorkflowStatus.COMPLETED:
                # Process VEP results with base64 encoded files using core utility
                processed_vep_results = process_vep_results(
                    result.results, exchange_id=exchange_id
                )

                # Success - include response data with processed VEP results
                event.response = {
                    "workflow_id": result.workflow_id,
                    "status": result.status.value,
                    "steps_completed": result.steps_completed,
                    "total_steps": result.total_steps,
                    "duration": result.duration,
                    "results": result.results,
                    "process_vep_results": processed_vep_results,
                    "started_at": (
                        result.started_at.isoformat() if result.started_at else None
                    ),
                    "completed_at": (
                        result.completed_at.isoformat() if result.completed_at else None
                    ),
                }
            else:
                # Failure - include error details
                error_details = []
                if result.errors:
                    error_details.extend(
                        [f"{k}: {v}" for k, v in result.errors.items()]
                    )
                event.error_details = (
                    "; ".join(error_details) if error_details else "Workflow failed"
                )

            # Add PDF content to event if PDF was generated
            pdf_path = result.results.get("vep_pdf_path")
            if pdf_path and result.status == WorkflowStatus.COMPLETED:
                logger.info(f"Adding PDF content to Kafka event from: {pdf_path}")
                if event.add_pdf_from_file(pdf_path):
                    logger.info("PDF content successfully added to workflow event")
                else:
                    logger.warning("Failed to add PDF content to workflow event")

            # Publish to Kafka
            success = publish_workflow_finished_event(event)
            if success:
                logger.info(
                    f"Workflow finished event published for exchange_id: {exchange_id}"
                )
            else:
                logger.warning(
                    f"Failed to publish workflow finished event for exchange_id: {exchange_id}"
                )

        except Exception as e:
            logger.error(f"Error publishing workflow finished event: {e}")

    def _should_skip_step(self, workflow: BaseWorkflow, step_name: str) -> bool:
        """Check if a step should be skipped due to failed dependencies."""
        step = workflow.steps[step_name]

        for dep_name in step.depends_on:
            if dep_name in workflow.steps:
                dep_step = workflow.steps[dep_name]
                # If a required dependency failed, skip this step
                if dep_step.status == StepStatus.FAILED and dep_step.required:
                    return True

        return False

    def _execute_step(
        self, workflow: BaseWorkflow, step_name: str, result: WorkflowResult
    ):
        """Execute a single workflow step."""
        step = workflow.steps[step_name]
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()

        # Determine workflow type for logging
        workflow_type = (
            "ccma"
            if "ccma" in workflow.workflow_id.lower()
            else "ddjj" if "ddjj" in workflow.workflow_id.lower() else "unknown"
        )

        logger.debug(f"Executing step: {step_name} - {step.description}")

        for attempt in range(step.retry_count):
            try:
                step_result = step.handler()

                if step_result:
                    step.status = StepStatus.COMPLETED
                    step.result = step_result
                    step.completed_at = datetime.now()
                    step_duration = (
                        step.completed_at - step.started_at
                    ).total_seconds()

                    # Record step metric
                    record_workflow_step(workflow_type, step_name, "success")
                    result.steps_completed += 1
                    logger.debug(f"Step completed: {step_name}")
                    break
                else:
                    if attempt < step.retry_count - 1:
                        logger.warning(
                            f"Step failed, retrying: {step_name} (attempt {attempt + 1})"
                        )
                        # Record retry metric
                        record_workflow_step(workflow_type, step_name, "retry")
                        time.sleep(0.5)  # Wait before retry
                    else:
                        step.status = StepStatus.FAILED
                        step.error = "Step handler returned False"
                        result.steps_failed += 1
                        step.completed_at = datetime.now()
                        step_duration = (
                            step.completed_at - step.started_at
                        ).total_seconds()

                        # Record step failure metric
                        record_workflow_step(workflow_type, step_name, "failed")
                        logger.error(
                            f"Step failed after {step.retry_count} attempts: {step_name}"
                        )

            except Exception as e:
                error_msg = f"Step execution error: {str(e)}\n{traceback.format_exc()}"

                if attempt < step.retry_count - 1:
                    logger.warning(f"Step error, retrying: {step_name} - {str(e)}")
                    # Record retry metric
                    record_workflow_step(workflow_type, step_name, "retry")
                    time.sleep(0.5)
                else:
                    step.status = StepStatus.FAILED
                    step.error = error_msg
                    step.original_exception = e
                    # Store the original exception
                    result.steps_failed += 1
                    step.completed_at = datetime.now()
                    step_duration = (
                        step.completed_at - step.started_at
                    ).total_seconds()

                    # Record step failure metric
                    record_workflow_step(workflow_type, step_name, "failed")
                    logger.error(f"Step failed with error: {step_name} - {str(e)}")

        step.completed_at = datetime.now()

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the status of a specific workflow."""
        if workflow_id not in self.workflows:
            return {"error": "Workflow not found"}

        workflow = self.workflows[workflow_id]

        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "steps": {
                step_name: {
                    "status": step.status.value,
                    "description": step.description,
                    "required": step.required,
                    "error": step.error,
                    "depends_on": step.depends_on,
                }
                for step_name, step in workflow.steps.items()
            },
        }

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the execution history."""
        history_slice = (
            self.execution_history[-limit:] if limit else self.execution_history
        )

        return [
            {
                "workflow_id": result.workflow_id,
                "status": result.status.value,
                "steps_completed": result.steps_completed,
                "steps_failed": result.steps_failed,
                "total_steps": result.total_steps,
                "duration": result.duration,
                "started_at": (
                    result.started_at.isoformat() if result.started_at else None
                ),
                "completed_at": (
                    result.completed_at.isoformat() if result.completed_at else None
                ),
            }
            for result in history_slice
        ]

    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        logger.debug("Execution history cleared")


# Factory function to create orchestrator instances
def create_orchestrator() -> WorkflowOrchestrator:
    """Create a new orchestrator instance."""
    return WorkflowOrchestrator()


# Global orchestrator instance
orchestrator = WorkflowOrchestrator()
