"""
DDJJ Service - Implementation for Declaraciones Juradas operations.
"""

from typing import Optional

from loguru import logger

from core.observability import record_afip_login, record_vep_operation
from core.services.browser.browser import BrowserManager


class DDJJService:
    """
    DDJJ Service coordinator for Declaraciones Juradas operations.
    """

    def __init__(self, browser_manager=None):
        """
        Initialize DDJJ service.

        Args:
            browser_manager: Browser manager instance (optional, will create if not provided)
        """
        # Initialize core dependencies
        if browser_manager:
            self.browser = browser_manager
        else:
            self.browser = BrowserManager()

        # Use browser manager directly
        self._browser_service = self.browser

    def authenticate_ddjj(self, cuit: Optional[str] = None) -> bool:
        """
        Authenticate with DDJJ service by clicking the DDJJ element in the portal.

        Args:
            cuit: CUIT number (optional, not needed as browser is already logged in)

        Returns:
            True if authentication successful
        """
        try:
            logger.info("Authenticating DDJJ by clicking service element")

            # Ensure we're on the portal main page
            if not self._ensure_on_portal():
                return False

            # Find and click the DDJJ service element
            if not self._click_ddjj_service():
                logger.error("Failed to click DDJJ service")
                return False

            logger.info("DDJJ service clicked successfully")

            # Wait for the new window to open
            import time

            time.sleep(0.2)

            # Switch to the new DDJJ window
            if self._browser_service.switch_to_new_window():
                logger.info("Successfully switched to DDJJ window")
                current_url = self._browser_service.get_current_url()
                logger.info(f"DDJJ window URL: {current_url}")

                # Verify we're on the expected DDJJ page
                expected_url = "https://seti.afip.gob.ar/setiweb/#/formulario-juramento"
                if expected_url in current_url:
                    # Record AFIP login success metric
                    record_afip_login("success")
                    logger.info("DDJJ authentication completed - on correct page")
                    return True
                else:
                    logger.warning(
                        f"Expected URL {expected_url}, but got: {current_url}"
                    )
                    # Still proceed as we switched windows
                    return True
            else:
                logger.error("Failed to switch to DDJJ window")
                return False

        except Exception as e:
            logger.error(f"DDJJ authentication failed: {e}")
            return False

    def _ensure_on_portal(self) -> bool:
        """Ensure we're on the portal main page."""
        portal_url = "https://portalcf.cloud.afip.gob.ar/portal/app/"
        current_url = self._browser_service.get_current_url()
        if portal_url not in current_url:
            logger.info("Navigating to AFIP portal main page")
            if not self._browser_service.navigate_to(portal_url):
                logger.error("Failed to navigate to portal")
                return False
            import time

            time.sleep(0.1)
        return True

    def _click_ddjj_service(self) -> bool:
        """Find and click the DDJJ service element."""
        try:
            logger.info("Looking for DDJJ service element")

            # Multiple selectors to find the DDJJ element
            ddjj_selectors = [
                "//h3[contains(text(), 'Presentación de DDJJ y Pagos')]",
                "//h3[contains(text(), 'DDJJ')]",
                "//div[contains(@class, 'service') or contains(@class, 'servicio')]//h3[contains(text(), 'DDJJ')]",
                "//*[contains(text(), 'DDJJ')][@onclick or @href or ancestor::a or ancestor::button]",
                "//*[contains(text(), 'Declaraciones Juradas')]",
                "//h3[contains(text(), 'DDJJ')]/parent::*[@onclick or @href or ancestor::a]",
                "//h3[contains(text(), 'DDJJ')]/ancestor::div[@onclick or @href or ancestor::a][1]",
            ]

            for selector in ddjj_selectors:
                try:
                    elements = self._browser_service.find_elements_safe(
                        "xpath", selector, timeout=2
                    )
                    if elements:
                        for element in elements:
                            # Try to find a clickable parent or the element itself
                            clickable_element = self._find_clickable_element(element)
                            if clickable_element:
                                logger.info(
                                    f"Found DDJJ service element: {clickable_element.get_attribute('outerHTML')[:200]}..."
                                )
                                try:
                                    clickable_element.click()
                                    logger.info("DDJJ service element clicked")
                                    return True
                                except Exception as e:
                                    logger.error(
                                        f"Failed to click DDJJ service element: {e}"
                                    )
                                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.error("DDJJ service element not found")
            return False

        except Exception as e:
            logger.error(f"Error clicking DDJJ service: {e}")
            return False

    def _find_clickable_element(self, element):
        """Find the clickable parent element of a given element."""
        try:
            # Check if the element itself is clickable
            if (
                element.get_attribute("onclick")
                or element.get_attribute("href")
                or element.tag_name in ["a", "button"]
            ):
                return element

            # Check parent elements up to 5 levels
            current = element
            for _ in range(5):
                try:
                    parent = current.find_element("xpath", "..")
                    if (
                        parent.get_attribute("onclick")
                        or parent.get_attribute("href")
                        or parent.tag_name in ["a", "button"]
                    ):
                        return parent
                    current = parent
                except:
                    break

            # If no clickable parent found, try to click the element anyway
            return element

        except Exception as e:
            logger.debug(f"Error finding clickable element: {e}")
            return element

    def click_accept_button(self) -> bool:
        """
        Click the accept button on the DDJJ page.

        Returns:
            True if button clicked successfully
        """
        try:
            logger.info("Looking for accept button")

            # Wait a moment for page to load
            import time

            time.sleep(0.2)

            # Find and click the accept button by property
            accept_button = self._browser_service.find_element_safe(
                "xpath", "//button[@property='aceptar']", timeout=3
            )

            if accept_button:
                try:
                    accept_button.click()
                    logger.info("Accept button clicked successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to click accept button: {e}")
                    return False
            else:
                logger.error("Accept button not found")
                return False

        except Exception as e:
            logger.error(f"Error clicking accept button: {e}")
            return False

    def click_vep_desde_archivo(self) -> bool:
        """
        Click on the 'VEP desde Archivo' menu item.

        Returns:
            True if menu item clicked successfully
        """
        try:
            logger.info("Looking for 'VEP desde Archivo' menu item")

            # Wait a moment for page to load
            import time

            time.sleep(0.2)

            # Find and click the menu item by span text
            menu_item = self._browser_service.find_element_safe(
                "xpath", "//span[text()='VEP desde Archivo']", timeout=3
            )

            if menu_item:
                try:
                    menu_item.click()
                    logger.info("'VEP desde Archivo' menu item clicked successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to click 'VEP desde Archivo' menu item: {e}")
                    return False
            else:
                logger.error("'VEP desde Archivo' menu item not found")
                return False

        except Exception as e:
            logger.error(f"Error clicking 'VEP desde Archivo' menu item: {e}")
            return False

    def upload_vep_file(self, file_path: str) -> bool:
        """
        Upload VEP file using the file input element.

        Args:
            file_path: Path to the VEP file to upload (can be relative or absolute)

        Returns:
            True if file uploaded successfully
        """
        try:
            # Convert to absolute path if needed
            import os

            abs_file_path = os.path.abspath(file_path)

            logger.info(f"Uploading VEP file: {abs_file_path}")

            # Verify file exists
            if not os.path.exists(abs_file_path):
                logger.error(f"VEP file does not exist: {abs_file_path}")
                return False

            # Wait a moment for page to load
            import time

            time.sleep(0.2)

            # Find the hidden file input element
            # Use a more robust selector that doesn't rely on changing IDs
            file_input_selectors = [
                "//input[@type='file' and contains(@accept, '.B64')]",
                "//input[@type='file' and contains(@id, '__EV__e-file__-input')]",
                "//input[@type='file' and contains(@class, 'd-none')]",
                "//input[@type='file']",
            ]

            file_input = None
            for selector in file_input_selectors:
                try:
                    file_input = self._browser_service.find_element_safe(
                        "xpath", selector, timeout=2
                    )
                    if file_input:
                        logger.info(f"Found file input with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not file_input:
                logger.error("File input element not found")
                return False

            # Upload the file by sending the absolute file path to the input element
            try:
                file_input.send_keys(abs_file_path)
                # Record VEP upload success metric
                record_vep_operation("upload", "success")
                logger.info("VEP file uploaded successfully using send_keys")

                # Wait a moment for the upload to be processed
                time.sleep(0.3)
                return True

            except Exception as e:
                # Record VEP upload failure metric
                record_vep_operation("upload", "failed")
                logger.error(f"Failed to upload file using send_keys: {e}")
                return False

        except Exception as e:
            # Record VEP upload failure metric
            record_vep_operation("upload", "failed")
            logger.error(f"Error uploading VEP file: {e}")
            return False

    def click_generate_vep_button(self) -> bool:
        """
        Click the 'Generar VEP' button to generate VEP from uploaded file.

        Returns:
            True if button clicked successfully
        """
        try:
            logger.info("Looking for 'Generar VEP' button")

            # Wait a moment for page to load after file upload
            import time

            time.sleep(0.2)

            # Find the generate VEP button using multiple selectors
            generate_button_selectors = [
                "//button[contains(text(), 'Generar VEP')]",
                "//button[@title='Generar Vep desde el archivo seleccionado']",
                "//button[contains(@id, '__EV__e-button__') and contains(@title, 'Generar')]",
                "//button[contains(@class, 'btn-primary') and contains(text(), 'Generar')]",
            ]

            for selector in generate_button_selectors:
                try:
                    button = self._browser_service.find_element_safe(
                        "xpath", selector, timeout=2
                    )
                    if button:
                        logger.info(
                            f"Found 'Generar VEP' button with selector: {selector}"
                        )
                        logger.info(
                            f"Button element: {button.get_attribute('outerHTML')[:200]}..."
                        )
                        button.click()
                        logger.info("'Generar VEP' button clicked successfully")
                        return True
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.error("'Generar VEP' button not found")
            return False

        except Exception as e:
            logger.error(f"Error clicking 'Generar VEP' button: {e}")
            return False

    def close(self):
        """Close the browser session."""
        if self.browser:
            self.browser.close_browser()
