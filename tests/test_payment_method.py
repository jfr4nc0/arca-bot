#!/usr/bin/env python3
"""
Test script to verify the new payment method selection step
"""

import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflows.ccma_workflow import CCMAWorkflow


def main():
    print("Testing CCMA workflow with payment method selection...")

    # Create a workflow instance with form_payment parameter
    workflow = CCMAWorkflow(form_payment="Pago con QR")

    # List all steps
    print("\nWorkflow Steps:")
    for step_name, step in workflow.steps.items():
        print(f"  - {step_name}: {step.description}")
        if step.depends_on:
            print(f"    Depends on: {', '.join(step.depends_on)}")

    # Check execution order
    execution_order = workflow.get_step_execution_order()
    print("\nExecution Order:")
    for i, step_name in enumerate(execution_order, 1):
        print(f"  {i}. {step_name}")

    # Verify our new step is included
    if "select_payment_method" in workflow.steps:
        print("\n✓ New 'select_payment_method' step found in workflow")
    else:
        print("\n✗ New 'select_payment_method' step NOT found in workflow")
        return False

    # Verify dependencies
    select_payment_step = workflow.steps["select_payment_method"]
    if "generate_vep" in select_payment_step.depends_on:
        print("✓ 'select_payment_method' correctly depends on 'generate_vep'")
    else:
        print("✗ 'select_payment_method' does not depend on 'generate_vep'")
        return False

    # Verify position in execution order
    if execution_order[-1] == "select_payment_method":
        print("✓ 'select_payment_method' is correctly positioned as the last step")
    else:
        print("✗ 'select_payment_method' is not the last step in execution order")
        return False

    print("\nAll checks passed! ✓")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
