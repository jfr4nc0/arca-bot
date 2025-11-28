"""
User agent rotation utility for avoiding detection and CAPTCHA triggers.
Provides realistic browser user agents for automation.
"""

import random
from typing import List


class UserAgentRotator:
    """Manages rotation of realistic user agents to avoid detection."""

    def __init__(self):
        self._user_agents = self._get_realistic_user_agents()

    def get_random_user_agent(self) -> str:
        """Get a random user agent from the pool."""
        return random.choice(self._user_agents)

    def _get_realistic_user_agents(self) -> List[str]:
        """Return a list of realistic, current user agents."""
        return [
            # Chrome on Windows 10/11
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            # Chrome on Linux (for variety)
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ]

    def get_user_agents(self) -> List[str]:
        """Get all available user agents."""
        return self._user_agents.copy()

    def add_custom_user_agent(self, user_agent: str) -> None:
        """Add a custom user agent to the pool."""
        if user_agent not in self._user_agents:
            self._user_agents.append(user_agent)

    def get_chrome_user_agents(self) -> List[str]:
        """Get only Chrome user agents."""
        return [ua for ua in self._user_agents if "Chrome/" in ua and "Edg/" not in ua]

    def get_firefox_user_agents(self) -> List[str]:
        """Get only Firefox user agents."""
        return [ua for ua in self._user_agents if "Firefox/" in ua]


# Global instance for easy access
user_agent_rotator = UserAgentRotator()
