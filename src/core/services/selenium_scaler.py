"""
Selenium auto-scaler service - manages dynamic scaling of Selenium Grid nodes.
"""

import os
import subprocess
import time
from typing import Optional

import requests
from loguru import logger


class SeleniumScaler:
    """
    Manages auto-scaling of Selenium Grid chrome-node containers.

    Scales nodes up when workflows need capacity and down when idle.
    """

    def __init__(
        self,
        min_nodes: int = 0,
        max_nodes: int = 3,
        sessions_per_node: int = 2,
        hub_url: str = "http://localhost:4444",
    ):
        """
        Initialize the Selenium scaler.

        Args:
            min_nodes: Minimum number of nodes to keep running (default 0)
            max_nodes: Maximum number of nodes to scale to (default 3)
            sessions_per_node: Browser sessions per node (default 2)
            hub_url: Selenium Grid Hub URL
        """
        self.min_nodes = min_nodes
        self.max_nodes = max_nodes
        self.sessions_per_node = sessions_per_node
        self.hub_url = hub_url
        self.current_nodes = 0
        self._project_dir = self._get_project_directory()

    def _get_project_directory(self) -> str:
        """Get the project root directory for docker-compose commands."""
        # Assuming this file is at src/core/services/selenium_scaler.py
        current_file = os.path.abspath(__file__)
        # Go up 3 levels: services -> core -> src -> root
        project_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        )
        return project_dir

    def scale_up(self, count: int = 1) -> bool:
        """
        Scale up chrome-node containers.

        Args:
            count: Number of nodes to add

        Returns:
            True if scaling succeeded, False otherwise
        """
        target = min(self.current_nodes + count, self.max_nodes)

        if target <= self.current_nodes:
            logger.debug(f"Already at {self.current_nodes} nodes, not scaling up")
            return True

        logger.info(f"Scaling Selenium nodes from {self.current_nodes} to {target}")

        try:
            # Use docker-compose scale command
            result = subprocess.run(
                [
                    "docker-compose",
                    "up",
                    "-d",
                    "--scale",
                    f"chrome-node={target}",
                    "--no-recreate",
                ],
                cwd=self._project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.current_nodes = target
                logger.info(f"Successfully scaled to {target} nodes")

                # Wait for nodes to register with hub
                self._wait_for_nodes_ready(target, timeout=30)
                return True
            else:
                logger.error(f"Failed to scale nodes: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Docker-compose scale command timed out")
            return False
        except Exception as e:
            logger.error(f"Error scaling nodes: {e}")
            return False

    def scale_down(self, count: int = 1) -> bool:
        """
        Scale down chrome-node containers.

        Args:
            count: Number of nodes to remove

        Returns:
            True if scaling succeeded, False otherwise
        """
        target = max(self.current_nodes - count, self.min_nodes)

        if target >= self.current_nodes:
            logger.debug(f"Already at {self.current_nodes} nodes, not scaling down")
            return True

        logger.info(f"Scaling Selenium nodes from {self.current_nodes} to {target}")

        try:
            result = subprocess.run(
                [
                    "docker-compose",
                    "up",
                    "-d",
                    "--scale",
                    f"chrome-node={target}",
                    "--no-recreate",
                ],
                cwd=self._project_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.current_nodes = target
                logger.info(f"Successfully scaled down to {target} nodes")
                return True
            else:
                logger.error(f"Failed to scale down nodes: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error scaling down nodes: {e}")
            return False

    def ensure_capacity(self, sessions_needed: int) -> bool:
        """
        Ensure enough node capacity for the requested number of sessions.

        Args:
            sessions_needed: Number of concurrent browser sessions needed

        Returns:
            True if capacity is available, False otherwise
        """
        # Calculate nodes needed (round up)
        nodes_needed = (
            sessions_needed + self.sessions_per_node - 1
        ) // self.sessions_per_node
        nodes_needed = min(nodes_needed, self.max_nodes)

        if nodes_needed > self.current_nodes:
            logger.info(
                f"Need {sessions_needed} sessions, scaling from {self.current_nodes} to {nodes_needed} nodes"
            )
            return self.scale_up(nodes_needed - self.current_nodes)

        logger.debug(
            f"Current capacity sufficient: {self.current_nodes} nodes for {sessions_needed} sessions"
        )
        return True

    def _wait_for_nodes_ready(self, expected_nodes: int, timeout: int = 30) -> bool:
        """
        Wait for nodes to register with the Selenium Hub.

        Args:
            expected_nodes: Number of nodes expected to be ready
            timeout: Maximum time to wait in seconds

        Returns:
            True if nodes are ready, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Query hub status
                response = requests.get(f"{self.hub_url}/status", timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    nodes = data.get("value", {}).get("nodes", [])
                    ready_nodes = len(
                        [n for n in nodes if n.get("availability") != "DOWN"]
                    )

                    if ready_nodes >= expected_nodes:
                        logger.info(f"{ready_nodes}/{expected_nodes} nodes ready")
                        return True

                    logger.debug(
                        f"Waiting for nodes: {ready_nodes}/{expected_nodes} ready"
                    )

            except Exception as e:
                logger.debug(f"Error checking hub status: {e}")

            time.sleep(2)

        logger.warning(f"Timeout waiting for {expected_nodes} nodes to be ready")
        return False

    def get_hub_status(self) -> Optional[dict]:
        """
        Get current Selenium Hub status.

        Returns:
            Hub status dictionary or None if error
        """
        try:
            response = requests.get(f"{self.hub_url}/status", timeout=5)

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Error getting hub status: {e}")

        return None

    def get_active_sessions_count(self) -> int:
        """
        Get number of active browser sessions from hub.

        Returns:
            Number of active sessions, or 0 if error
        """
        status = self.get_hub_status()

        if status:
            # Check if hub is ready (no active sessions means ready=true)
            ready = status.get("value", {}).get("ready", True)

            if not ready:
                # Hub not ready means sessions are active
                # Count sessions from nodes
                nodes = status.get("value", {}).get("nodes", [])
                total_sessions = sum(
                    len(node.get("slots", []))
                    for node in nodes
                    if node.get("availability") != "DOWN"
                )
                return total_sessions

        return 0
