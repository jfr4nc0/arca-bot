"""
Kafka producer service for workflow events.
"""

import json
import os
from typing import Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError
from loguru import logger

from core.events.workflow_events import WorkflowFinishedEvent


class WorkflowKafkaProducer:
    """Kafka producer for workflow events."""

    def __init__(self, bootstrap_servers: str = None, topic: str = "workflow-events"):
        # Use environment variable for Docker, fallback to localhost for local development
        if bootstrap_servers is None:
            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")

        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self._producer: Optional[KafkaProducer] = None

    def _get_producer(self) -> KafkaProducer:
        """Get or create Kafka producer instance."""
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    retries=3,
                    retry_backoff_ms=100,
                )
                logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            except Exception as e:
                logger.error(f"Failed to create Kafka producer: {e}")
                raise
        return self._producer

    def publish_workflow_finished(self, event: WorkflowFinishedEvent) -> bool:
        """Publish workflow finished event to Kafka."""
        try:
            producer = self._get_producer()

            # Use exchange_id as message key for partitioning
            key = event.exchange_id
            value = event.to_dict()

            # Log PDF content size if present
            if event.pdf_content:
                pdf_size_kb = event.get_pdf_size_kb()
                logger.info(
                    f"Publishing workflow event with PDF content ({pdf_size_kb:.1f} KB)"
                )

            # Send message
            future = producer.send(self.topic, key=key, value=value)

            # Wait for acknowledgment (optional - for reliability)
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Workflow event published: exchange_id={event.exchange_id}, "
                f"topic={record_metadata.topic}, partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}"
            )
            return True

        except KafkaError as e:
            logger.error(f"Kafka error publishing workflow event: {e}")
            return False
        except Exception as e:
            logger.error(f"Error publishing workflow event: {e}")
            return False

    def close(self):
        """Close the Kafka producer."""
        if self._producer:
            try:
                self._producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
            finally:
                self._producer = None


# Global producer instance
_kafka_producer: Optional[WorkflowKafkaProducer] = None


def get_kafka_producer() -> WorkflowKafkaProducer:
    """Get the global Kafka producer instance."""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = WorkflowKafkaProducer()
    return _kafka_producer


def publish_workflow_finished_event(event: WorkflowFinishedEvent) -> bool:
    """Convenience function to publish workflow finished event."""
    try:
        producer = get_kafka_producer()
        return producer.publish_workflow_finished(event)
    except Exception as e:
        logger.error(f"Failed to publish workflow finished event: {e}")
        return False
