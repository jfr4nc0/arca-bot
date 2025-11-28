"""
Observability module for ArcaAutoVep RPA system.
Provides metrics capabilities.
"""

from core.observability.metrics import (
    end_workflow_timer,
    get_metrics_endpoint,
    metrics_registry,
    record_afip_login,
    record_browser_operation,
    record_ccma_result,
    record_ddjj_result,
    record_file_operation,
    record_http_request,
    record_payment_by_type,
    record_transaction_operation,
    record_vep_operation,
    record_workflow_step,
    start_workflow_timer,
)

__all__ = [
    # Metrics
    "metrics_registry",
    "record_ccma_result",
    "record_ddjj_result",
    "record_payment_by_type",
    "record_afip_login",
    "record_browser_operation",
    "record_vep_operation",
    "record_file_operation",
    "record_transaction_operation",
    "record_workflow_step",
    "record_http_request",
    "start_workflow_timer",
    "end_workflow_timer",
    "get_metrics_endpoint",
]
