import random
import time
from typing import Optional

from loguru import logger
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.config import config
from core.observability import record_afip_login
from core.services.browser.browser import BrowserManager


class ARCALoginService:
    def __init__(self):
        self.browser = BrowserManager()

    def login(self, cuit: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Perform login to ARCA system.
        This is a two-step process:
        1. Input CUIT → Click "Ingresar" → Password field appears
        2. Input password → Click "Ingresar" → Complete login

        Args:
            cuit: CUIT number to use for login (serves as username, defaults to config value)
            password: Password for login (defaults to config value)0

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Use provided values or fallback to config
            login_cuit = cuit or config.arca.cuit
            login_password = password or config.arca.password

            if not login_cuit:
                logger.error("CUIT is required for login")
                return False

            logger.info(f"Starting arca login process for CUIT: {login_cuit}")

            # Start browser and navigate to login page
            self.browser.start_browser()
            self.browser.navigate_to(config.arca.login_url)

            # Step 1: Input CUIT and submit to proceed to password step
            if not self._input_cuit_and_submit(login_cuit):
                return False

            # Step 2: If password is provided, complete the login
            if login_password:
                if not self._input_password_and_submit(login_password):
                    return False

                # Verify login was successful
                if self.is_logged_in():
                    # Record AFIP login success metric
                    record_afip_login("success")
                    logger.info("Login completed successfully")
                    return True
                else:
                    # Record AFIP login failure metric
                    record_afip_login("failed")
                    logger.error("Login failed - not redirected to expected portal")
                    return False
            else:
                logger.info(
                    "CUIT submitted successfully. Manual password entry required."
                )
                return True

        except Exception as e:
            # Record AFIP login failure metric
            record_afip_login("failed")
            logger.error(f"Login failed: {e}")
            return False

    def _input_cuit_and_submit(self, cuit: str) -> bool:
        """Step 1: Input CUIT and submit to proceed to password step."""
        try:
            logger.debug("Step 1: entering CUIT and submitting")

            # Input CUIT
            if not self._input_cuit(cuit):
                return False

            # Submit CUIT to proceed to password step
            success = self._click_siguiente_button("CUIT submission")
            return success

        except Exception as e:
            logger.error(f"Failed to submit CUIT: {e}")
            return False

    def _input_password_and_submit(self, password: str) -> bool:
        """Step 2: Input password and submit to complete login."""
        try:
            logger.debug("Step 2: entering password and submitting")

            # Wait a moment for the password field to appear after CUIT submission
            time.sleep(0.3)

            # Input password
            if not self._input_password(password):
                return False

            # Submit password to complete login
            success = self._click_ingresar_button("password submission")
            return success

        except Exception as e:
            logger.error(f"Failed to submit password: {e}")
            return False

    def _input_cuit(self, cuit: str) -> bool:
        """Input CUIT into the username field (F1:username)."""
        try:
            logger.debug("Looking for CUIT input field")

            # Target the specific input field for CUIT
            cuit_input = self.browser.find_element_safe(By.ID, "F1:username")

            if not cuit_input:
                logger.error("CUIT input field not found")
                return False

            # Clear and input CUIT
            cuit_input.clear()
            cuit_input.send_keys(cuit)

            logger.debug(f"CUIT {cuit} entered successfully")
            time.sleep(0.2)  # Allow UI to update

            return True

        except Exception as e:
            logger.error(f"Failed to input CUIT: {e}")
            return False

    def _input_password(self, password: str) -> bool:
        """Input password into the password field (F1:password)."""
        try:
            logger.debug("Looking for password input field")

            # Target the specific password field
            password_input = self.browser.find_element_safe(
                By.ID, "F1:password", timeout=15
            )

            if not password_input:
                logger.error("Password input field not found")
                return False

            # Clear and input password
            password_input.clear()
            password_input.send_keys(password)

            logger.debug("Password entered successfully")
            time.sleep(0.2)  # Allow UI to update

            return True

        except Exception as e:
            logger.error(f"Failed to input password: {e}")
            return False

    def _click_siguiente_button(self, step_name: str) -> bool:
        """Click the F1:btnSiguiente button for CUIT submission."""
        try:
            logger.debug(f"Looking for Siguiente button for {step_name}")

            # Target the specific Siguiente button
            if self.browser.click_element_safe(By.ID, "F1:btnSiguiente", timeout=10):
                logger.debug(f"Siguiente button clicked for {step_name}")
                time.sleep(0.5)  # Wait for page response
                return True
            else:
                logger.error(f"Siguiente button not found for {step_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to click Siguiente button for {step_name}: {e}")
            return False

    def _click_ingresar_button(self, step_name: str) -> bool:
        """Click the F1:btnIngresar button for password submission."""
        try:
            logger.debug(f"Looking for Ingresar button for {step_name}")

            # Target the specific Ingresar button
            if self.browser.click_element_safe(By.ID, "F1:btnIngresar", timeout=10):
                logger.debug(f"Ingresar button clicked for {step_name}")
                time.sleep(0.5)  # Wait for page response
                return True
            else:
                logger.error(f"Ingresar button not found for {step_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to click Ingresar button for {step_name}: {e}")
            return False

    def is_logged_in(self) -> bool:
        """Check if successfully logged in by looking for the expected portal URL."""
        try:
            # Wait a moment for redirect to complete
            time.sleep(1)

            current_url = self.get_current_url()
            logger.debug(f"Current URL: {current_url}")

            # Check if we're on the expected portal URL
            expected_portal_url = "https://portalcf.cloud.afip.gob.ar/portal/app/"

            if expected_portal_url in current_url:
                logger.info("Login verification successful - redirected to portal")
                return True

            # Fallback: check for common dashboard elements if URL doesn't match
            success_indicators = [
                (By.XPATH, "//title[contains(text(), 'AFIP')]"),
                (By.XPATH, "//*[contains(text(), 'Bienvenido')]"),
                (By.XPATH, "//*[contains(text(), 'Panel')]"),
                (By.CLASS_NAME, "dashboard"),
                (By.ID, "menu-principal"),
                (By.XPATH, "//*[contains(@class, 'navbar')]"),
                (By.XPATH, "//*[contains(text(), 'Servicios')]"),
            ]

            for by, selector in success_indicators:
                if self.browser.find_element_safe(by, selector, timeout=5):
                    logger.debug(
                        "Login verification successful - found dashboard elements"
                    )
                    return True

            logger.warning(f"Login verification failed - current URL: {current_url}")
            return False

        except Exception as e:
            logger.error(f"Failed to verify login status: {e}")
            return False

    def close(self):
        """Close the browser session."""
        self.browser.close_browser()

    def get_current_url(self) -> str:
        """Get current URL for debugging purposes."""
        if self.browser.driver:
            return self.browser.driver.current_url
        return ""

    def take_screenshot(self, filename: str = "screenshot.png"):
        """Take a screenshot for debugging purposes."""
        if self.browser.driver:
            try:
                self.browser.driver.save_screenshot(filename)
                logger.info(f"Screenshot saved: {filename}")
            except Exception as e:
                logger.error(f"Failed to take screenshot: {e}")

    def _human_like_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0):
        """Add a human-like random delay to avoid detection."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        logger.debug(f"Applied human-like delay: {delay:.2f}s")
