"""
Base workflow classes and data structures.
"""

import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class WorkflowStatus(Enum):
    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if status is terminal (workflow finished)."""
        return status in [cls.COMPLETED.value, cls.FAILED.value, cls.CANCELLED.value]

    @classmethod
    def is_active(cls, status: str) -> bool:
        """Check if status indicates an active workflow."""
        return status == cls.RUNNING.value


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""

    name: str
    description: str
    handler: Callable
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 3
    timeout: int = 300  # seconds
    required: bool = True
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    original_exception: Optional[Exception] = None  # Store original exception
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowResult:
    """Results of workflow execution."""

    workflow_id: str
    status: WorkflowStatus
    steps_completed: int
    steps_failed: int
    total_steps: int
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None


class BaseWorkflow(ABC):
    """Base class for all workflows."""

    def __init__(self, workflow_id: str, name: str, description: str):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = WorkflowStatus.PENDING
        self.shared_resources: Dict[str, Any] = {}

    @abstractmethod
    def define_steps(self):
        """Define the workflow steps. Must be implemented by subclasses."""
        pass

    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps[step.name] = step

    def get_step_dependencies(self, step_name: str) -> List[str]:
        """Get dependencies for a specific step."""
        if step_name in self.steps:
            return self.steps[step_name].depends_on
        return []

    def get_step_execution_order(self) -> List[str]:
        """Get the execution order of steps based on dependencies."""
        executed = set()
        execution_order = []

        while len(executed) < len(self.steps):
            progress_made = False

            for step_name, step in self.steps.items():
                if step_name in executed:
                    continue

                # Check if all dependencies are satisfied
                deps_satisfied = all(dep in executed for dep in step.depends_on)

                if deps_satisfied:
                    execution_order.append(step_name)
                    executed.add(step_name)
                    progress_made = True

            if not progress_made:
                raise ValueError("Circular dependency detected in workflow steps")

        return execution_order

    def reset(self):
        """Reset workflow to initial state."""
        self.status = WorkflowStatus.PENDING
        self.shared_resources.clear()

        for step in self.steps.values():
            step.status = StepStatus.PENDING
            step.result = None
            step.error = None
            step.started_at = None
            step.completed_at = None

    def cleanup(self):
        """Clean up workflow resources. Override in subclasses if needed."""
        try:
            # Close browser sessions if present
            if "arca_service" in self.shared_resources:
                arca_service = self.shared_resources["arca_service"]
                if hasattr(arca_service, "close"):
                    arca_service.close()

            if "ccma_service" in self.shared_resources:
                ccma_service = self.shared_resources["ccma_service"]
                if hasattr(ccma_service, "close"):
                    ccma_service.close()

            logger.debug(f"Workflow {self.workflow_id} resources cleaned up")

        except Exception as e:
            logger.error(f"Error during workflow cleanup: {e}")

    def __str__(self) -> str:
        return f"Workflow({self.workflow_id}: {self.name})"

    def __repr__(self) -> str:
        return self.__str__()
