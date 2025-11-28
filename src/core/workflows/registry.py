"""
Workflow registry for automatic workflow discovery and registration.
"""

from typing import Dict, Type

from loguru import logger

from core.workflows.arca_login import ARCALoginWorkflow
from core.workflows.base import BaseWorkflow
from core.workflows.ccma_workflow import CCMAWorkflow
from core.workflows.ddjj_workflow import DDJJWorkflow


class WorkflowRegistry:
    """Registry for managing available workflow classes."""

    def __init__(self):
        self._workflow_classes: Dict[str, Type[BaseWorkflow]] = {}
        self._register_built_in_workflows()

    def _register_built_in_workflows(self):
        """Register built-in workflow classes."""
        self.register_workflow_class(ARCALoginWorkflow)
        self.register_workflow_class(CCMAWorkflow)
        self.register_workflow_class(DDJJWorkflow)

    def register_workflow_class(self, workflow_class: Type[BaseWorkflow]):
        """Register a workflow class."""
        # Create a temporary instance to get the workflow_id
        temp_instance = workflow_class()
        workflow_id = temp_instance.workflow_id

        self._workflow_classes[workflow_id] = workflow_class
        logger.info(
            f"Workflow class registered: {workflow_id} -> {workflow_class.__name__}"
        )

    def create_workflow(self, workflow_id: str, **kwargs) -> BaseWorkflow:
        """Create a workflow instance by ID."""
        if workflow_id not in self._workflow_classes:
            raise ValueError(f"Unknown workflow ID: {workflow_id}")

        workflow_class = self._workflow_classes[workflow_id]
        return workflow_class(**kwargs)

    def list_available_workflows(self) -> Dict[str, Type[BaseWorkflow]]:
        """List all available workflow classes."""
        return self._workflow_classes.copy()

    def get_workflow_class(self, workflow_id: str) -> Type[BaseWorkflow]:
        """Get a workflow class by ID."""
        if workflow_id not in self._workflow_classes:
            raise ValueError(f"Unknown workflow ID: {workflow_id}")
        return self._workflow_classes[workflow_id]


# Global registry instance
workflow_registry = WorkflowRegistry()
