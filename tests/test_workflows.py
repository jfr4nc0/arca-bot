"""
Test suite for ArcaAutoVep Automatizations.
"""

import os
import sys

import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported without errors."""
    try:
        from core.services.ccma.payment_handler import PaymentHandler
        from core.services.ccma.vep_service import VEPService
        from core.services.system.file_handler import FileHandler
        from core.workflows.arca_login import ARCALoginWorkflow
        from core.workflows.ccma_workflow import CCMAWorkflow

        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


class TestWorkflowSteps:
    """Test workflow step definitions and execution order."""

    def test_ccma_workflow_steps(self):
        """Test that the CCMA workflow includes all expected steps."""
        from core.workflows.ccma_workflow import CCMAWorkflow

        workflow = CCMAWorkflow()

        # Check that all expected steps are present
        expected_steps = [
            "initialize_browser",
            "arca_login",
            "open_ccma_window",
            "calculate_debt",
            "handle_debt_window",
            "generate_vep",
            "select_payment_method",
        ]

        for step in expected_steps:
            assert step in workflow.steps, f"Step {step} not found in workflow"

        # Check dependencies
        assert (
            "handle_debt_window" in workflow.steps["generate_vep"].depends_on
        ), "generate_vep step should depend on handle_debt_window"

        assert (
            "generate_vep" in workflow.steps["select_payment_method"].depends_on
        ), "select_payment_method step should depend on generate_vep"

    def test_workflow_execution_order(self):
        """Test workflow execution order is correct."""
        from core.workflows.ccma_workflow import CCMAWorkflow

        workflow = CCMAWorkflow()
        execution_order = workflow.get_step_execution_order()

        # Check that generate_vep comes before select_payment_method
        generate_vep_index = execution_order.index("generate_vep")
        select_payment_index = execution_order.index("select_payment_method")

        assert (
            generate_vep_index < select_payment_index
        ), "generate_vep should come before select_payment_method in execution order"

    def test_arca_login_workflow(self):
        """Test ARCA login workflow steps."""
        from core.workflows.arca_login import ARCALoginWorkflow

        workflow = ARCALoginWorkflow()

        expected_steps = ["initialize_browser", "arca_login", "verify_login"]

        for step in expected_steps:
            assert (
                step in workflow.steps
            ), f"Step {step} not found in ARCA login workflow"
