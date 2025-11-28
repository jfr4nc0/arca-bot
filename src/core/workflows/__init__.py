"""
Workflows package for ArcaAutoVep RPA system.
Contains workflow definitions and orchestration components.
"""

from core.workflows.arca_login import ARCALoginWorkflow
from core.workflows.base import BaseWorkflow, WorkflowResult, WorkflowStep
from core.workflows.ccma_workflow import CCMAWorkflow
from core.workflows.registry import workflow_registry

__all__ = [
    "ARCALoginWorkflow",
    "BaseWorkflow",
    "CCMAWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "workflow_registry",
]
