"""
Payment handler that consolidates all payment method handling.
Single source of truth for payment constants.
"""

import base64
import time
from pathlib import Path
from typing import Optional

from loguru import logger
from selenium.webdriver.common.by import By

from core.observability import record_file_operation, record_payment_by_type
from core.services.browser.browser import BrowserManager

# ARCA payment methods mapping - Single source of truth
PAYMENT_METHODS = {
    "qr": "0",
    "link": "1001",
    "pago_mis_cuentas": "1002",
    "inter_banking": "1003",
    "xn_group": "1005",
}

DEFAULT_PAYMENT_METHOD = "qr"


class PaymentHandler:
    """Unified payment handler for all payment methods."""

    def __init__(
        self, browser_manager: BrowserManager, workflow_type: Optional[str] = None
    ):
        self._browser = browser_manager
        self.workflow_type = workflow_type

    def select_payment_method(self, method: str) -> bool:
        """
        Select payment method for VEP.

        Args:
            method: Payment method name

        Returns:
            True if payment method was selected successfully
        """
        try:
            # Validate payment method
            if method not in PAYMENT_METHODS:
                logger.error(f"Invalid payment method: {method}")
                logger.debug(
                    f"Available payment methods: {list(PAYMENT_METHODS.keys())}"
                )
                return False

            payment_id = PAYMENT_METHODS[method]
            logger.info(f"Selecting payment method: {method} (ID: {payment_id})")

            # Find and click payment method element
            payment_element = self._browser.find_element_safe(
                By.ID, payment_id, timeout=10
            )

            if not payment_element:
                logger.error(
                    f"Payment method '{method}' element not found (ID: {payment_id})"
                )
                return False

            try:
                payment_element.click()
                logger.debug(
                    f"Payment method '{method}' clicked successfully (regular click)"
                )
                click_successful = True
            except Exception as e:
                logger.warning(f"Regular click failed for '{method}': {e}")
                click_successful = False

            # Accept confirmation modal
            if self._accept_confirmation():
                # Record payment method selection success metric
                record_payment_by_type(method, "success")
                logger.info(f"Payment confirmation accepted for '{method}'")
                return True
            else:
                # Record payment method selection failure metric
                record_payment_by_type(method, "failed")
                logger.error(f"Failed to accept '{method}' confirmation modal")
                return False

        except Exception as e:
            # Record payment method selection failure metric
            record_payment_by_type(method, "failed")
            logger.error(f"Failed to select payment method: {e}")
            return False

    def extract_payment_data(
        self, payment_method: str, base_filename: str
    ) -> Optional[str]:
        """
        Extract payment data (URL or QR code) based on payment method.

        Args:
            payment_method: The selected payment method
            base_filename: Base name for output files

        Returns:
            Filename of extracted data, or None if failed
        """
        try:
            if payment_method == "qr":
                return self._extract_qr_code(base_filename)
            elif payment_method in [
                "link",
                "pago_mis_cuentas",
                "inter_banking",
                "xn_group",
            ]:
                return self._extract_payment_url(payment_method, base_filename)
            else:
                logger.debug(
                    f"No specific data extraction for payment method: {payment_method}"
                )
                return None
        except Exception as e:
            logger.error(f"Failed to extract payment data: {e}")
            return None

    def _extract_qr_code(self, base_filename: str) -> Optional[str]:
        """Extract QR code image from the page."""
        try:
            logger.debug("Starting QR code image extraction")

            # Find the QR image element
            qr_element = self._find_qr_image_element()
            if not qr_element:
                logger.error("QR code image element not found")
                return None

            # Extract the base64 data from the src attribute
            src_attribute = qr_element.get_attribute("src")
            if not src_attribute or not src_attribute.startswith("data:image/"):
                logger.error("QR image src attribute is not a data URL")
                return None

            # Parse the base64 data
            try:
                # Format: data:image/png;base64,<base64_data>
                header, base64_data = src_attribute.split(",", 1)
                image_format = header.split(";")[0].split("/")[
                    1
                ]  # Extract 'png' from 'data:image/png'
            except (ValueError, IndexError) as e:
                logger.error(f"Failed to parse base64 data URL: {e}")
                return None

            # Generate filename
            qr_filename = f"{base_filename}_qr.{image_format}"

            # Ensure QR directory exists
            qr_dir = Path("resources/qr")
            qr_dir.mkdir(parents=True, exist_ok=True)

            # Decode and save the image
            qr_file_path = qr_dir / qr_filename
            try:
                image_data = base64.b64decode(base64_data)
                with open(qr_file_path, "wb") as f:
                    f.write(image_data)
                logger.info(f"QR code image saved: {qr_file_path}")
                return qr_filename
            except Exception as save_error:
                logger.error(f"Failed to save QR image: {save_error}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract QR code image: {e}")
            return None

    def _extract_payment_url(
        self, payment_method: str, base_filename: str
    ) -> Optional[str]:
        """Extract payment URL from the page."""
        try:
            logger.debug(f"Starting {payment_method} payment URL extraction")

            # Find the URL element
            url_element = self._find_payment_url_element(payment_method)
            if not url_element:
                logger.error("Payment URL element not found")
                return None

            # Extract the URL from the href attribute
            url_href = url_element.get_attribute("href")
            if not url_href:
                # Try to get the text content as fallback
                url_text = url_element.get_attribute("textContent") or url_element.text
                if url_text and url_text.startswith("http"):
                    url_href = url_text.strip()
                else:
                    logger.error("No valid URL found in the payment link element")
                    return None

            logger.debug(f"Found payment URL: {url_href}")

            # Return the URL directly (no file persistence needed for static URLs)
            logger.info(f"Payment URL extracted successfully")
            return url_href

        except Exception as e:
            logger.error(f"Failed to extract payment URL: {e}")
            return None

    def _find_qr_image_element(self):
        """Find the QR code image element on the page."""
        try:
            logger.debug("Looking for QR code image element")

            # Multiple strategies to find the QR image
            qr_selectors = [
                # Look for img with base64 PNG data
                (By.XPATH, "//img[starts-with(@src, 'data:image/png;base64,')]"),
                # Look for img with QR-related attributes or classes
                (
                    By.XPATH,
                    "//img[contains(@class, 'qr') or contains(@alt, 'QR') or contains(@title, 'QR')]",
                ),
                # Generic approach - any img with data: src
                (By.XPATH, "//img[starts-with(@src, 'data:image/')]"),
            ]

            for by, selector in qr_selectors:
                try:
                    elements = self._browser.find_elements_safe(by, selector, timeout=5)
                    if elements:
                        for element in elements:
                            src = element.get_attribute("src")
                            if src and "data:image/png;base64," in src:
                                logger.debug(
                                    f"Found QR image element with selector: {selector}"
                                )
                                return element
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.warning("QR code image element not found with any selector")
            return None

        except Exception as e:
            logger.error(f"Error finding QR image element: {e}")
            return None

    def _find_payment_url_element(self, payment_method: str):
        """Find the payment URL element on the page."""
        try:
            logger.debug(f"Looking for {payment_method} payment URL element")

            # Define selectors based on payment method
            if payment_method == "link":
                url_selectors = [
                    (By.XPATH, "//a[@href='https://redlink.com.ar/arca.html']"),
                    (By.XPATH, "//a[@title='RED LINK']"),
                    (By.XPATH, "//a[contains(@href, 'redlink.com.ar')]"),
                ]
            else:  # pago_mis_cuentas
                url_selectors = [
                    (By.XPATH, "//a[@href='https://web.pagomiscuentas.com/login']"),
                    (By.XPATH, "//a[@title='BANELCO']"),
                    (By.XPATH, "//a[contains(@href, 'pagomiscuentas.com')]"),
                ]

            for by, selector in url_selectors:
                try:
                    element = self._browser.find_element_safe(by, selector, timeout=5)
                    if element:
                        href = element.get_attribute("href")
                        text = element.get_attribute("textContent") or element.text
                        logger.debug(f"Found URL element with selector: {selector}")
                        logger.debug(f"Element href: {href}, text: {text}")
                        return element
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.warning("Payment URL element not found with any selector")
            return None

        except Exception as e:
            logger.error(f"Error finding payment URL element: {e}")
            return None

    def _accept_confirmation(self) -> bool:
        """Accept confirmation modal after payment method selection."""
        try:
            # Wait for modal to appear
            confirm_button = self._browser.find_element_safe(
                By.XPATH,
                "//button[contains(text(), 'Aceptar') or contains(text(), 'OK') or contains(text(), 'Confirm')]",
                timeout=5,
            )

            if confirm_button:
                # Try JavaScript click if regular click fails
                try:
                    confirm_button.click()
                    logger.debug("Confirmation modal accepted with regular click")
                except Exception as click_error:
                    logger.warning(
                        f"Regular click failed: {click_error}, trying JavaScript click"
                    )
                    self._browser.driver.execute_script(
                        "arguments[0].click();", confirm_button
                    )
                    logger.debug("Confirmation modal accepted with JavaScript click")

                # Wait for modal to close and page to stabilize
                logger.debug("Waiting for modal to close and page to stabilize...")
                time.sleep(2)

                # Wait for modal overlay to disappear
                modal_overlay_gone = False
                for i in range(5):
                    try:
                        modal_overlay = self._browser.driver.find_element(
                            By.XPATH,
                            "//div[contains(@class, 'modal') and contains(@class, 'show')]",
                        )
                        if modal_overlay:
                            logger.debug(
                                f"Modal overlay still present, waiting... ({i+1}/5)"
                            )
                            time.sleep(1)
                        else:
                            modal_overlay_gone = True
                            break
                    except:
                        # Modal overlay not found = good
                        modal_overlay_gone = True
                        break

                if modal_overlay_gone:
                    logger.debug("Modal overlay disappeared")
                else:
                    logger.warning("⚠️ Modal overlay still present after 5 seconds")

                # Add workflow-specific wait time for QR rendering
                if self.workflow_type == "ddjj":
                    logger.debug(
                        "DDJJ workflow detected - waiting 3 seconds for QR rendering"
                    )
                    time.sleep(3)
                else:
                    logger.debug(
                        "CCMA workflow or default - waiting 1 second for QR rendering"
                    )
                    time.sleep(1)

                return True
            else:
                logger.debug("No confirmation modal found, continuing")
                return True

        except Exception as e:
            logger.warning(f"Error accepting confirmation modal: {e}")
            return True  # Continue anyway

    def get_default_payment_method(self) -> str:
        """Get default payment method."""
        return DEFAULT_PAYMENT_METHOD

    def validate_payment_method(self, method: str) -> bool:
        """Validate if payment method is supported."""
        return method in PAYMENT_METHODS
