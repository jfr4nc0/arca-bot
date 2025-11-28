"""
Prometheus metrics for ArcaAutoVep RPA system.
Focus on business metrics and Golden Signals.
"""

import time
from typing import Dict, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Create a custom registry for our metrics
metrics_registry = CollectorRegistry()

# ====== BUSINESS METRICS ======

# CCMA Workflow Results
ccma_workflows_total = Counter(
    "ccma_workflows_total",
    "Total CCMA workflows by result",
    ["status"],  # success, failed
    registry=metrics_registry,
)

# DDJJ Workflow Results
ddjj_workflows_total = Counter(
    "ddjj_workflows_total",
    "Total DDJJ workflows by result",
    ["status"],  # success, failed
    registry=metrics_registry,
)

# Payment Method Usage
payments_by_type_total = Counter(
    "payments_by_type_total",
    "Payment processing by payment method",
    ["payment_method", "status"],  # qr, link, pago_mis_cuentas, etc. + success/failed
    registry=metrics_registry,
)

# AFIP Authentication Results
afip_login_attempts_total = Counter(
    "afip_login_attempts_total",
    "Total AFIP authentication attempts",
    ["status"],  # success, failed
    registry=metrics_registry,
)

# Browser Operations
browser_operations_total = Counter(
    "browser_operations_total",
    "Total browser operations",
    [
        "operation_type",
        "status",
    ],  # navigation, element_click, window_switch + success/failed
    registry=metrics_registry,
)

# VEP Operations
vep_operations_total = Counter(
    "vep_operations_total",
    "Total VEP operations",
    ["operation_type", "status"],  # generation, upload, download + success/failed
    registry=metrics_registry,
)

# File Operations
file_operations_total = Counter(
    "file_operations_total",
    "Total file operations",
    ["operation_type", "status"],  # pdf_download, qr_extraction + success/failed
    registry=metrics_registry,
)

# Transaction Operations
transaction_operations_total = Counter(
    "transaction_operations_total",
    "Total transaction operations",
    [
        "operation_type",
        "status",
    ],  # creation, duplicate_check + success/failed/duplicate
    registry=metrics_registry,
)

# Workflow Step Results
workflow_steps_total = Counter(
    "workflow_steps_total",
    "Total workflow steps executed",
    [
        "workflow_type",
        "step_name",
        "status",
    ],  # ccma/ddjj + step_name + success/failed/retry
    registry=metrics_registry,
)

# ====== GOLDEN SIGNALS ======

# 1. TRAFFIC - Request rate
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=metrics_registry,
)

# 2. LATENCY - Response time distribution
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=metrics_registry,
)

workflow_duration_seconds = Histogram(
    "workflow_duration_seconds",
    "Workflow execution duration",
    ["workflow_type"],  # ccma, ddjj
    buckets=[10, 30, 60, 120, 300, 600],
    registry=metrics_registry,
)

# 3. ERRORS - Error rate by HTTP status class
http_requests_2xx_total = Counter(
    "http_requests_2xx_total",
    "Total 2xx HTTP responses",
    ["method", "endpoint"],
    registry=metrics_registry,
)

http_requests_4xx_total = Counter(
    "http_requests_4xx_total",
    "Total 4xx HTTP responses",
    ["method", "endpoint"],
    registry=metrics_registry,
)

http_requests_5xx_total = Counter(
    "http_requests_5xx_total",
    "Total 5xx HTTP responses",
    ["method", "endpoint"],
    registry=metrics_registry,
)

# 4. SATURATION - Resource utilization
active_workflows_gauge = Gauge(
    "active_workflows_current",
    "Number of currently running workflows",
    registry=metrics_registry,
)

# Workflow timing trackers
_workflow_start_times: Dict[str, float] = {}

# ====== BUSINESS METRIC FUNCTIONS ======


def record_ccma_result(status: str) -> None:
    """Record CCMA workflow result (success/failed)."""
    ccma_workflows_total.labels(status=status).inc()


def record_ddjj_result(status: str) -> None:
    """Record DDJJ workflow result (success/failed)."""
    ddjj_workflows_total.labels(status=status).inc()


def record_payment_by_type(payment_method: str, status: str) -> None:
    """Record payment processing by method and result."""
    payments_by_type_total.labels(payment_method=payment_method, status=status).inc()


def record_afip_login(status: str) -> None:
    """Record AFIP authentication attempt (success/failed)."""
    afip_login_attempts_total.labels(status=status).inc()


def record_browser_operation(operation_type: str, status: str) -> None:
    """Record browser operation (navigation, element_click, etc.)."""
    browser_operations_total.labels(operation_type=operation_type, status=status).inc()


def record_vep_operation(operation_type: str, status: str) -> None:
    """Record VEP operation (generation, upload, download)."""
    vep_operations_total.labels(operation_type=operation_type, status=status).inc()


def record_file_operation(operation_type: str, status: str) -> None:
    """Record file operation (pdf_download, qr_extraction)."""
    file_operations_total.labels(operation_type=operation_type, status=status).inc()


def record_transaction_operation(operation_type: str, status: str) -> None:
    """Record transaction operation (creation, duplicate_check)."""
    transaction_operations_total.labels(
        operation_type=operation_type, status=status
    ).inc()


def record_workflow_step(workflow_type: str, step_name: str, status: str) -> None:
    """Record workflow step execution result."""
    workflow_steps_total.labels(
        workflow_type=workflow_type, step_name=step_name, status=status
    ).inc()


# ====== GOLDEN SIGNALS FUNCTIONS ======


def record_http_request(
    method: str, endpoint: str, status_code: int, duration: float
) -> None:
    """Record HTTP request metrics with golden signals."""
    # Traffic
    http_requests_total.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()

    # Latency
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )

    # Errors by status code class
    if 200 <= status_code < 300:
        http_requests_2xx_total.labels(method=method, endpoint=endpoint).inc()
    elif 400 <= status_code < 500:
        http_requests_4xx_total.labels(method=method, endpoint=endpoint).inc()
    elif 500 <= status_code < 600:
        http_requests_5xx_total.labels(method=method, endpoint=endpoint).inc()


def start_workflow_timer(workflow_id: str, workflow_type: str) -> None:
    """Start timing a workflow."""
    _workflow_start_times[workflow_id] = time.time()
    active_workflows_gauge.inc()


def end_workflow_timer(workflow_id: str, workflow_type: str) -> None:
    """End timing a workflow and record duration."""
    start_time = _workflow_start_times.pop(workflow_id, None)
    if start_time:
        duration = time.time() - start_time
        workflow_duration_seconds.labels(workflow_type=workflow_type).observe(duration)

    active_workflows_gauge.dec()


def get_metrics_endpoint() -> tuple[str, str]:
    """Get metrics for Prometheus scraping."""
    return generate_latest(metrics_registry), CONTENT_TYPE_LATEST
