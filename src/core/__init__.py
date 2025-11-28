"""
Core package for ArcaAutoVep RPA system.
Contains the fundamental components for workflow orchestration and configuration.
"""

import core.logging  # noqa: F401  Ensures logging is configured
from core.config import config
from core.orchestrator import orchestrator
from core.workflows.base import BaseWorkflow, WorkflowResult, WorkflowStep
from core.workflows.registry import workflow_registry

__all__ = [
    "config",
    "orchestrator",
    "BaseWorkflow",
    "WorkflowResult",
    "WorkflowStep",
    "workflow_registry",
]
