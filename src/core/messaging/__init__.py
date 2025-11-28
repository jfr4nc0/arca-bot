"""
Messaging module for Kafka integration.
"""

from core.messaging.kafka_producer import (
    WorkflowKafkaProducer,
    get_kafka_producer,
    publish_workflow_finished_event,
)

__all__ = [
    "WorkflowKafkaProducer",
    "get_kafka_producer",
    "publish_workflow_finished_event",
]
