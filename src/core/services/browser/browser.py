import os
import random
import time
from typing import Optional

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchDriverException,
    SessionNotCreatedException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.config import config
from core.exceptions.infrastructure_exceptions import (
    BrowserSessionException,
    InfrastructureException,
)
from core.observability import record_browser_operation
from core.services.browser.user_agent_rotation import user_agent_rotator


class BrowserManager:
    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None
        self.wait: Optional[WebDriverWait] = None
        self.temp_user_data_dir: Optional[str] = None

    def start_browser(self) -> webdriver.Remote:
        """Initialize and start Chrome browser using Remote WebDriver (Selenium Grid)."""
        try:
            chrome_options = Options()

            # Basic Chrome options for automation
            if config.arca.headless:
                chrome_options.add_argument("--headless")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--disable-translate")
            chrome_options.add_argument("--hide-scrollbars")
            chrome_options.add_argument("--mute-audio")
            chrome_options.add_argument("--disable-background-mode")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-hang-monitor")
            chrome_options.add_argument("--disable-client-side-phishing-detection")
            chrome_options.add_argument("--disable-component-update")
            chrome_options.add_argument("--disable-domain-reliability")
            chrome_options.add_argument("--aggressive-cache-discard")

            # Use random user agent for each session
            random_user_agent = user_agent_rotator.get_random_user_agent()
            chrome_options.add_argument(f"--user-agent={random_user_agent}")
            logger.debug(f"Using user agent: {random_user_agent[:80]}...")

            # Configure default download preferences to force enable downloads
            # Use /tmp/downloads for Selenium Grid (mounted as ./resources on host)
            download_prefs = {
                "download.default_directory": "/tmp/downloads",
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True,
                "profile.default_content_settings.popups": 0,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.content_settings.exceptions.automatic_downloads": {
                    "*,*": {"setting": 1}
                },
                "download.extensions_to_open": "",
                "download.open_pdf_in_system_reader": False,
                "plugins.always_open_pdf_externally": False,
                "plugins.plugins_disabled": ["Chrome PDF Viewer"],
            }
            chrome_options.add_experimental_option("prefs", download_prefs)

            # Add anti-detection measures and enable Downloads API
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("detach", True)

            # Enable Chrome Downloads API explicitly
            chrome_options.add_argument("--enable-features=DownloadsUI")
            chrome_options.add_argument("--enable-chrome-downloads-api")
            chrome_options.add_experimental_option("useAutomationExtension", False)

            # Randomize window size slightly
            window_width = random.randint(1900, 1920)
            window_height = random.randint(1060, 1080)
            chrome_options.add_argument(f"--window-size={window_width},{window_height}")

            # Add download-specific Chrome arguments to enable download support
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-gpu")

            # Enable downloads in headless/remote Chrome
            chrome_options.add_argument("--enable-logging")
            chrome_options.add_argument("--log-level=0")
            chrome_options.add_argument(
                "--enable-features=NetworkService,NetworkServiceLogging"
            )
            chrome_options.add_argument("--remote-allow-origins=*")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            # Ensure file downloads work in Docker/Selenium environment
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--allow-file-access-from-files")
            chrome_options.add_argument("--enable-file-cookies")

            # Get Selenium Grid URL from environment
            selenium_url = os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")
            logger.debug(f"Connecting to Selenium Grid at: {selenium_url}")

            # Create Remote WebDriver connection
            self.driver = webdriver.Remote(
                command_executor=selenium_url, options=chrome_options
            )

            self.driver.implicitly_wait(config.arca.implicit_wait)
            self.driver.set_page_load_timeout(config.arca.page_load_timeout)

            self.wait = WebDriverWait(self.driver, config.arca.implicit_wait)

            # Store temp dir for cleanup (not needed for remote driver but keeping interface)
            self.temp_user_data_dir = None

            # Execute script to remove webdriver property and add stealth measures
            self._apply_stealth_measures()

            logger.info("Remote browser started successfully")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")

            # Determine the appropriate exception based on the actual exception type,
            # not by parsing the error message
            if isinstance(e, (TimeoutException)):
                raise InfrastructureException(
                    message=f"Browser startup timeout: {str(e)}",
                    error_type="timeout",
                    details={"original_error": str(e)},
                    original_exception=e,
                )
            elif isinstance(e, (ConnectionRefusedError, ConnectionResetError)):
                raise InfrastructureException(
                    message=f"Connection failed to Selenium Grid: {str(e)}",
                    error_type="connection_refused",
                    details={"original_error": str(e)},
                    original_exception=e,
                )
            elif isinstance(e, SessionNotCreatedException):
                raise BrowserSessionException(
                    message=f"Browser session creation failed: {str(e)}",
                    session_details={
                        "original_error": str(e),
                        "error_type": "session_not_created",
                    },
                    original_exception=e,
                )
            elif isinstance(e, (WebDriverException, NoSuchDriverException)):
                # Check if it's related to session pool exhaustion based on the actual exception
                # by looking at the exception attributes or specific subclasses
                if hasattr(e, "msg") and (
                    "session" in str(getattr(e, "msg", "")).lower()
                    or "pool" in str(getattr(e, "msg", "")).lower()
                ):
                    raise BrowserSessionException(
                        message=f"Browser session creation failed: {str(e)}",
                        session_details={
                            "original_error": str(e),
                            "error_type": "session_pool_exhausted",
                        },
                        original_exception=e,
                    )
                else:
                    raise InfrastructureException(
                        message=f"Browser startup failed due to infrastructure issue: {str(e)}",
                        error_type="web_driver_issue",
                        details={"original_error": str(e)},
                        original_exception=e,
                    )
            else:
                # For any other infrastructure-related issue, use InfrastructureException
                raise InfrastructureException(
                    message=f"Browser startup failed due to infrastructure issue: {str(e)}",
                    error_type="general_infrastructure",
                    details={"original_error": str(e)},
                    original_exception=e,
                )

    def _apply_stealth_measures(self):
        """Apply stealth measures to avoid detection."""
        try:
            # Remove navigator.webdriver property
            self.driver.execute_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                """
            )

            # Override plugins and languages for more realistic behavior
            self.driver.execute_script(
                """
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                """
            )

            # Add random delays to mimic human behavior
            time.sleep(random.uniform(0.5, 1.5))

            logger.debug("Stealth measures applied successfully")

        except Exception as e:
            logger.warning(f"Could not apply stealth measures: {e}")

    def close_browser(self):
        """Close the browser and clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.wait = None

        # Clean up temporary user data directory
        if self.temp_user_data_dir and os.path.exists(self.temp_user_data_dir):
            try:
                import shutil

                shutil.rmtree(self.temp_user_data_dir)
                logger.debug(
                    f"Cleaned up temp user data directory: {self.temp_user_data_dir}"
                )
            except Exception as e:
                logger.warning(f"Could not clean up temp user data directory: {e}")
            finally:
                self.temp_user_data_dir = None

    def set_download_directory(self, directory: str):
        """Change the download directory for the current browser session."""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        try:
            # Convert API container path to Selenium container path
            # /app/resources/pdf -> /tmp/downloads/pdf
            # /app/resources/qr -> /tmp/downloads/qr
            selenium_path = directory.replace("/app/resources", "/tmp/downloads")

            logger.debug(
                f"Setting download directory - API path: {directory}, Selenium path: {selenium_path}"
            )

            # Update Chrome download preferences
            self.driver.execute_cdp_cmd(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": selenium_path},
            )

            # Verify the setting by getting current download behavior
            try:
                # Execute a script to verify download settings
                download_prefs = self.driver.execute_script(
                    """
                    return {
                        defaultPath: window.chrome?.downloads?.defaultPath || 'unknown',
                        downloadPath: arguments[0]
                    };
                """,
                    selenium_path,
                )
                logger.debug(f"Download directory verification: {download_prefs}")
            except Exception as verify_error:
                logger.debug(f"Could not verify download directory: {verify_error}")

            logger.debug(f"Download directory set successfully: {selenium_path}")

        except Exception as e:
            logger.error(f"❌ Failed to set download directory: {e}")
            logger.error(
                f"Original directory: {directory}, Selenium path: {selenium_path}"
            )

    def navigate_to(self, url: str):
        """Navigate to a specific URL."""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        try:
            logger.debug(f"Navigating to: {url}")
            self.driver.get(url)
            time.sleep(0.2)  # Minimal wait for page initialization
            # Record navigation success metric
            record_browser_operation("navigation", "success")
        except Exception as e:
            # Record navigation failure metric
            record_browser_operation("navigation", "failed")
            logger.error(f"Failed to navigate to {url}: {e}")
            raise

    def find_element_safe(self, by: By, value: str, timeout: int = None):
        """Safely find an element with explicit wait."""
        if not self.wait:
            raise RuntimeError("Browser not properly initialized")

        try:
            wait_time = timeout or config.arca.implicit_wait
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Element not found: {by}={value}")
            return None

    def click_element_safe(self, by: By, value: str, timeout: int = None):
        """Safely click an element with explicit wait."""
        try:
            wait_time = timeout or config.arca.implicit_wait
            element = WebDriverWait(self.driver, wait_time).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            # Record element click success metric
            record_browser_operation("element_click", "success")
            logger.debug(f"Clicked element: {by}={value}")
            return True
        except TimeoutException:
            # Record element click failure metric
            record_browser_operation("element_click", "failed")
            logger.error(f"Element not clickable: {by}={value}")
            return False

    def find_elements_safe(self, by: By, value: str, timeout: int = None):
        """Safely find multiple elements with explicit wait."""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")

        try:
            wait_time = timeout or config.arca.implicit_wait
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
            elements = self.driver.find_elements(by, value)
            return elements
        except TimeoutException:
            logger.debug(f"Elements not found: {by}={value}")
            return []

    def input_text_safe(
        self, by: By, value: str, text: str, clear: bool = True, timeout: int = None
    ):
        """Safely input text into an element."""
        element = self.find_element_safe(by, value, timeout)
        if element:
            try:
                if clear:
                    element.clear()
                element.send_keys(text)
                logger.debug(f"Input text into {by}={value}: {text}")
                return True
            except Exception as e:
                logger.error(f"Failed to input text: {e}")
                return False
        return False

    def get_current_url(self) -> str:
        """Get the current URL of the browser."""
        if not self.driver:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        return self.driver.current_url

    def switch_to_new_window(self) -> bool:
        """Switch to the newest window/tab."""
        try:
            if not self.driver:
                logger.error("Browser not started")
                return False

            # Get all window handles
            all_windows = self.driver.window_handles

            # If there's only one window, nothing to switch to
            if len(all_windows) <= 1:
                logger.warning("No new window found to switch to")
                return False

            # Switch to the last (newest) window
            newest_window = all_windows[-1]
            self.driver.switch_to.window(newest_window)

            current_url = self.get_current_url()
            # Record window switch success metric
            record_browser_operation("window_switch", "success")
            logger.debug(f"Switched to new window. Current URL: {current_url}")
            return True

        except Exception as e:
            # Record window switch failure metric
            record_browser_operation("window_switch", "failed")
            logger.error(f"Failed to switch to new window: {e}")
            return False

    def get_window_count(self) -> int:
        """Get the number of open windows/tabs."""
        try:
            if self.driver:
                return len(self.driver.window_handles)
            return 0
        except Exception as e:
            logger.error(f"Failed to get window count: {e}")
            return 0
