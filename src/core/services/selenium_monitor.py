"""
Selenium monitor - background task for auto-scaling idle nodes down.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from core.services.selenium_scaler import SeleniumScaler


class SeleniumMonitor:
    """
    Monitors Selenium Grid nodes and scales down when idle.

    Runs as a background task in the FastAPI application.
    """

    def __init__(
        self,
        scaler: Optional[SeleniumScaler] = None,
        idle_timeout: int = 600,
        check_interval: int = 60,
    ):
        """
        Initialize the Selenium monitor.

        Args:
            scaler: SeleniumScaler instance (creates default if None)
            idle_timeout: Seconds of inactivity before scaling down (default 600 = 10min)
            check_interval: Seconds between idle checks (default 60)
        """
        self.scaler = scaler or SeleniumScaler()
        self.idle_timeout = idle_timeout
        self.check_interval = check_interval
        self.last_activity_time = datetime.now()
        self._running = False

    async def start_monitoring(self):
        """Start the monitoring loop."""
        self._running = True
        logger.info(
            f"Starting Selenium auto-scaler monitor "
            f"(idle_timeout={self.idle_timeout}s, check_interval={self.check_interval}s)"
        )

        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_and_scale_down()

            except asyncio.CancelledError:
                logger.info("Selenium monitor cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Selenium monitor: {e}")
                # Continue monitoring despite errors

    async def _check_and_scale_down(self):
        """Check for idle nodes and scale down if necessary."""
        try:
            # Get current active sessions
            active_sessions = self.scaler.get_active_sessions_count()

            if active_sessions > 0:
                # Activity detected, update last activity time
                self.last_activity_time = datetime.now()
                logger.debug(f"Selenium active: {active_sessions} sessions")
                return

            # No active sessions - check idle time
            idle_time = (datetime.now() - self.last_activity_time).total_seconds()

            logger.debug(
                f"Selenium idle for {int(idle_time)}s "
                f"(threshold: {self.idle_timeout}s, nodes: {self.scaler.current_nodes})"
            )

            if idle_time >= self.idle_timeout and self.scaler.current_nodes > 0:
                logger.info(
                    f"Selenium idle for {int(idle_time)}s - scaling down "
                    f"from {self.scaler.current_nodes} nodes"
                )

                # Scale down by 1 node at a time
                success = self.scaler.scale_down(1)

                if success:
                    logger.info(f"Scaled down to {self.scaler.current_nodes} nodes")
                    # Reset activity time to avoid immediate next scale-down
                    self.last_activity_time = datetime.now()
                else:
                    logger.warning("Failed to scale down nodes")

        except Exception as e:
            logger.error(f"Error checking idle status: {e}")

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Stopping Selenium monitor")

    def mark_activity(self):
        """
        Mark current time as last activity.

        Call this when a workflow starts to reset the idle timer.
        """
        self.last_activity_time = datetime.now()
        logger.debug("Selenium activity marked")

    def get_idle_time(self) -> float:
        """
        Get current idle time in seconds.

        Returns:
            Seconds since last activity
        """
        return (datetime.now() - self.last_activity_time).total_seconds()
