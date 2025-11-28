"""
CCMA Service - Consolidated implementation without over-abstraction.
"""

import time
from datetime import datetime
from typing import Optional

from loguru import logger
from selenium.webdriver.common.by import By

from core.observability import record_afip_login, record_vep_operation
from core.services.browser.browser import BrowserManager


class CCMAService:
    """
    CCMA Service coordinator with all functionality consolidated.
    """

    def __init__(self, browser_manager=None):
        """
        Initialize CCMA service.

        Args:
            browser_manager: Browser manager instance (optional, will create if not provided)
        """
        # Initialize core dependencies
        if browser_manager:
            self.browser = browser_manager
        else:
            self.browser = BrowserManager()

        # Use browser manager directly
        self._browser = self.browser
        self._portal_url = "https://portalcf.cloud.afip.gob.ar/portal/app/"

    def authenticate_ccma(self, cuit: Optional[str] = None) -> bool:
        """
        Authenticate with CCMA service by clicking the CCMA element in the portal.

        Args:
            cuit: CUIT number (optional, not needed as browser is already logged in)

        Returns:
            True if authentication successful
        """
        try:
            logger.info("Authenticating CCMA by clicking service element")

            # Ensure we're on the portal main page
            if not self._ensure_on_portal():
                return False

            # Find and click the CCMA service element
            if not self._click_ccma_service():
                logger.error("Failed to click CCMA service")
                return False

            logger.debug("CCMA service clicked successfully")

            # Wait for the new window to open
            time.sleep(0.3)

            # Switch to the new CCMA window
            if self._browser.switch_to_new_window():
                logger.debug("Successfully switched to CCMA window")
                current_url = self._browser.get_current_url()
                logger.debug(f"CCMA window URL: {current_url}")

                # Verify we're on the expected CCMA page
                if "ccam" in current_url or "afip.gob.ar" in current_url:
                    # Record AFIP login success metric
                    record_afip_login("success")
                    logger.info("CCMA authentication completed - on correct page")
                    return True
                else:
                    logger.warning(
                        f"Unexpected URL after CCMA authentication: {current_url}"
                    )
                    return True  # Still proceed as we switched windows
            else:
                logger.error("Failed to switch to CCMA window")
                return False

        except Exception as e:
            # Record AFIP login failure metric
            record_afip_login("failed")
            logger.error(f"CCMA authentication failed: {e}")
            return False

    def calculate_debt(
        self,
        period_from: str = None,
        period_to: str = None,
        calculation_date: str = None,
    ) -> bool:
        """
        Fill the debt calculation form and submit.

        Args:
            period_from: Period from in MM/YYYY format
            period_to: Period to in MM/YYYY format
            calculation_date: Calculation date in DD/MM/YYYY format

        Returns:
            True if form was filled and submitted successfully
        """
        try:
            # Calculate default dates if not provided
            current_date = datetime.now()
            period_from = period_from or f"01/{current_date.year - 2}"
            period_to = period_to or f"{current_date.month:02d}/{current_date.year}"
            calculation_date = calculation_date or current_date.strftime("%d/%m/%Y")

            logger.info(
                f"Filling debt calculation form: {period_from} to {period_to}, date: {calculation_date}"
            )

            # Fill form fields
            if not self._fill_field("perdesde2", period_from, "Period from"):
                return False

            if not self._fill_field("perhasta2", period_to, "Period to"):
                return False

            if not self._fill_field("feccalculo", calculation_date, "Calculation date"):
                return False

            # Submit the form
            success = self._submit_debt_calculation()
            if success:
                logger.info("Debt calculation completed successfully")
            else:
                logger.error("Debt calculation failed")
            return success

        except Exception as e:
            logger.error(f"Failed to calculate debt: {e}")
            return False

    def handle_debt_window_filters(
        self, tipo_contribuyente: Optional[str], impuesto: Optional[str]
    ) -> bool:
        """
        Apply filters in debt window.

        Args:
            tipo_contribuyente: Optional filter for contributor type
            impuesto: Optional filter for tax type

        Returns:
            True if filters were applied successfully
        """
        try:
            logger.info("Applying debt window filters")
            filters_applied = False

            if tipo_contribuyente:
                logger.debug(f"Applying contributor type filter: {tipo_contribuyente}")
                if self._select_dropdown_option(
                    "TipoContribuyente", tipo_contribuyente
                ):
                    filters_applied = True
                    logger.debug("Contributor type filter applied successfully")
                else:
                    logger.warning("Failed to apply contributor type filter")

            if impuesto:
                logger.debug(f"Applying tax type filter: {impuesto}")
                if self._select_dropdown_option("divComboImpuesto", impuesto):
                    filters_applied = True
                    logger.debug("Tax type filter applied successfully")
                else:
                    logger.warning("Failed to apply tax type filter")

            # If filters were applied, click "Consultar" button
            if filters_applied:
                if not self._click_consultar_button():
                    return False

            # After filters (or if no filters), click "Generar Comprobante de Pago"
            return self._click_volante_pago_button()

        except Exception as e:
            logger.error(f"Failed to apply filters: {e}")
            return False

    def generate_vep(self, include_interests: bool = False) -> bool:
        """
        Generate VEP by selecting items and clicking generate button.

        Args:
            include_interests: Whether to include interest items (MI) in VEP generation

        Returns:
            True if VEP generation was initiated successfully
        """
        try:
            logger.info(
                f"Starting VEP generation process (include_interests: {include_interests})"
            )

            # Verify we're on the correct page
            current_url = self._browser.get_current_url()
            logger.debug(f"Current URL: {current_url}")

            if "VolPag_ctacte.asp" not in current_url:
                if "P04_ctacte.asp" in current_url:
                    logger.error(
                        "Detected redirect to P04_ctacte.asp - this indicates a session/authentication issue"
                    )
                    logger.error("Cannot proceed with VEP generation from this page")
                    return False
                else:
                    logger.warning(
                        "Not on expected VEP page. Attempting to continue anyway..."
                    )

            # Step 1: Click on "Seleccionar todos" for MC
            if not self._select_all_mc():
                logger.warning("Failed to select all MC items")

            # Step 2: Conditionally click on "Seleccionar todos" for MI based on include_interests
            if include_interests:
                logger.info("Including interests (MI) in VEP generation")
                if not self._select_all_mi():
                    logger.warning("Failed to select all MI items")
            else:
                logger.info("Excluding interests (MI) from VEP generation")

            # Step 3: Click on "GENERAR VEP O QR" button
            success = self._click_generate_vep_button()
            if success:
                # Record VEP generation success metric
                record_vep_operation("generation", "success")
            else:
                # Record VEP generation failure metric
                record_vep_operation("generation", "failed")
            return success

        except Exception as e:
            # Record VEP generation exception metric
            record_vep_operation("generation", "failed")
            logger.error(f"Failed to generate VEP: {e}")
            return False

    # Private helper methods

    def _ensure_on_portal(self) -> bool:
        """Ensure we're on the portal main page."""
        current_url = self._browser.get_current_url()
        if self._portal_url not in current_url:
            logger.debug("Navigating to AFIP portal main page")
            if not self._browser.navigate_to(self._portal_url):
                logger.error("Failed to navigate to portal")
                return False
            time.sleep(0.3)
        return True

    def _click_ccma_service(self) -> bool:
        """Find and click the CCMA service element."""
        try:
            logger.debug("Looking for CCMA service element")

            # Multiple selectors to find the CCMA element
            ccma_selectors = [
                "//h3[contains(text(), 'CCMA - CUENTA CORRIENTE DE CONTRIBUYENTES')]",
                "//h3[contains(text(), 'CCMA')]",
                "//div[contains(@class, 'service') or contains(@class, 'servicio')]//h3[contains(text(), 'CCMA')]",
                "//*[contains(text(), 'CCMA')][@onclick or @href or ancestor::a or ancestor::button]",
                "//*[contains(text(), 'CUENTA CORRIENTE') and contains(text(), 'CONTRIBUYENTES')]",
                "//h3[contains(text(), 'CCMA')]/parent::*[@onclick or @href or ancestor::a]",
                "//h3[contains(text(), 'CCMA')]/ancestor::div[@onclick or @href or ancestor::a][1]",
            ]

            for selector in ccma_selectors:
                try:
                    elements = self._browser.find_elements_safe(
                        By.XPATH, selector, timeout=3
                    )
                    if elements:
                        for element in elements:
                            # Try to find a clickable parent or the element itself
                            clickable_element = self._find_clickable_element(element)
                            if clickable_element:
                                logger.debug(
                                    f"Found CCMA service element: {clickable_element.get_attribute('outerHTML')[:200]}..."
                                )
                                try:
                                    clickable_element.click()
                                    logger.debug("CCMA service element clicked")
                                    return True
                                except Exception as e:
                                    logger.error(
                                        f"Failed to click CCMA service element: {e}"
                                    )
                                    continue
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            logger.error("CCMA service element not found")
            return False

        except Exception as e:
            logger.error(f"Error clicking CCMA service: {e}")
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
                    parent = current.find_element(By.XPATH, "..")
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

    def _fill_field(self, field_name: str, value: str, field_description: str) -> bool:
        """Fill a form field with retry logic."""
        field_input = self._browser.find_element_safe(By.NAME, field_name, timeout=5)

        if not field_input:
            logger.error(f"{field_description} field not found")
            return False

        try:
            # Clear field multiple ways to ensure it's empty
            field_input.clear()
            field_input.send_keys("")
            time.sleep(0.1)

            # Input the value
            field_input.send_keys(value)
            time.sleep(0.1)

            # Verify the value was entered
            entered_value = field_input.get_attribute("value")
            logger.debug(
                f"{field_description} field - Expected: {value}, Actual: {entered_value}"
            )

            if entered_value != value:
                logger.warning(f"{field_description} value mismatch. Retrying...")
                field_input.clear()
                time.sleep(0.1)
                field_input.send_keys(value)
                entered_value = field_input.get_attribute("value")
                logger.debug(
                    f"{field_description} retry - Expected: {value}, Actual: {entered_value}"
                )

            logger.debug(f"{field_description} filled: {value}")
            return True

        except Exception as e:
            logger.error(f"Error filling {field_description} field: {e}")
            return False

    def _submit_debt_calculation(self) -> bool:
        """Submit the debt calculation form."""
        debt_calc_button = self._browser.find_element_safe(
            By.NAME, "CalDeud", timeout=5
        )

        if not debt_calc_button:
            logger.error("Debt calculation button not found")
            return False

        try:
            debt_calc_button.click()
            logger.debug("Debt calculation button clicked")
            time.sleep(0.2)  # Wait for calculation to process

            # Verify calculation was successful
            current_url = self._browser.get_current_url()
            if "ccam" in current_url:
                logger.info("Debt calculation completed successfully")
                return True
            else:
                logger.warning("Debt calculation may not have completed properly")
                return True  # Still return True as the action was performed

        except Exception as e:
            logger.error(f"Error submitting debt calculation: {e}")
            return False

    def _select_dropdown_option(self, container_id: str, target_value: str) -> bool:
        """Select an option from a dropdown by matching the value."""
        try:
            # Find the container div
            container = self._browser.find_element_safe(By.ID, container_id, timeout=5)
            if not container:
                logger.error(f"Container with ID '{container_id}' not found")
                return False

            # Look for select element within the container
            select_element = container.find_element(By.TAG_NAME, "select")
            if not select_element:
                logger.error(f"Select element not found in container '{container_id}'")
                return False

            # Get all option elements
            options = select_element.find_elements(By.TAG_NAME, "option")

            # Find matching option by value
            for option in options:
                option_value = option.get_attribute("value")
                if option_value and target_value.lower() in option_value.lower():
                    logger.debug(f"Found matching option: {option_value}")
                    try:
                        option.click()
                        logger.debug(f"Successfully clicked option: {option_value}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to click option: {e}")
                        return False

            # If no exact match, try matching by text content
            for option in options:
                option_text = option.text
                if option_text and target_value.lower() in option_text.lower():
                    logger.debug(f"Found matching option by text: {option_text}")
                    try:
                        option.click()
                        logger.debug(
                            f"Successfully clicked option by text: {option_text}"
                        )
                        return True
                    except Exception as e:
                        logger.error(f"Failed to click option by text: {e}")
                        return False

            logger.warning(f"No matching option found for value: {target_value}")
            return False

        except Exception as e:
            logger.error(f"Error selecting dropdown option: {e}")
            return False

    def _click_consultar_button(self) -> bool:
        """Click the Consultar button after applying filters."""
        logger.debug("Clicking 'Consultar' button")
        consultar_button = self._browser.find_element_safe(By.NAME, "Cons", timeout=5)

        if consultar_button:
            try:
                consultar_button.click()
                logger.debug("Consultar button clicked successfully")
                time.sleep(0.2)  # Wait for results to load
                return True
            except Exception as e:
                logger.error(f"Failed to click Consultar button: {e}")
                return False
        else:
            logger.error("Consultar button not found")
            return False

    def _click_volante_pago_button(self) -> bool:
        """Click the 'VOLANTE DE PAGO' button to navigate to VEP generation."""
        logger.info("Clicking 'VOLANTE DE PAGO' button")

        # First check if there are any debt results or "no debt" messages
        current_url = self._browser.get_current_url()
        logger.debug(f"Current URL before Generar Comprobante: {current_url}")

        # Multiple selectors for the payment slip generation button
        button_selectors = [
            "//input[@name='GENVOL' and @type='button']",
            "//input[@value='VOLANTE DE PAGO']",
            "//input[contains(@value, 'VOLANTE')]",
        ]

        for selector in button_selectors:
            try:
                button = self._browser.find_element_safe(By.XPATH, selector, timeout=3)
                if button:
                    logger.debug(
                        f"Found 'VOLANTE DE PAGO' button with selector: {selector}"
                    )
                    try:
                        button.click()
                        logger.debug("'VOLANTE DE PAGO' button clicked successfully")
                        time.sleep(0.3)  # Wait for navigation

                        # Check if we navigated to the VEP generation page
                        current_url = self._browser.get_current_url()
                        if "VolPag_ctacte.asp" in current_url:
                            logger.info("Successfully navigated to VEP generation page")
                            return True
                        else:
                            logger.warning(
                                f"Unexpected URL after clicking button: {current_url}"
                            )
                            # Continue trying other selectors
                            continue

                    except Exception as e:
                        logger.warning(
                            f"Failed to click button with selector {selector}: {e}"
                        )
                        continue
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        logger.error("'VOLANTE DE PAGO' button not found or click failed")
        logger.warning("This may indicate no debt was found for the specified period")
        return False

    def _select_all_mc(self) -> bool:
        """Select all MC items."""
        logger.debug("Clicking 'Seleccionar todos' for MC")
        select_mc_link = self._browser.find_element_safe(
            By.XPATH,
            "//a[@href=\"javascript:select_todos('MC');\"]/b[contains(text(), 'Seleccionar todos')]",
            timeout=5,
        )

        if select_mc_link:
            try:
                select_mc_link.click()
                success = True
                logger.debug("MC 'Seleccionar todos' link clicked successfully")
            except Exception as e:
                logger.error(f"Failed to click MC 'Seleccionar todos' link: {e}")
                success = False
            if success:
                logger.debug("MC 'Seleccionar todos' clicked successfully")
                time.sleep(0.2)
            return success
        else:
            logger.warning("MC 'Seleccionar todos' link not found")
            return False

    def _select_all_mi(self) -> bool:
        """Select all MI items."""
        logger.debug("Clicking 'Seleccionar todos' for MI")
        select_mi_link = self._browser.find_element_safe(
            By.XPATH,
            "//a[@href=\"javascript:select_todos('MI');\"]/b[contains(text(), 'Seleccionar todos')]",
            timeout=5,
        )

        if select_mi_link:
            try:
                select_mi_link.click()
                success = True
                logger.debug("MI 'Seleccionar todos' link clicked successfully")
            except Exception as e:
                logger.error(f"Failed to click MI 'Seleccionar todos' link: {e}")
                success = False
            if success:
                logger.debug("MI 'Seleccionar todos' clicked successfully")
                time.sleep(0.2)
            return success
        else:
            logger.warning("MI 'Seleccionar todos' link not found")
            return False

    def _click_generate_vep_button(self) -> bool:
        """Click the GENERAR VEP O QR button."""
        logger.info("Clicking 'GENERAR VEP O QR' button")
        generar_vep_button = self._browser.find_element_safe(
            By.ID, "GenerarVEP", timeout=5
        )

        if not generar_vep_button:
            # Try alternative selector
            generar_vep_button = self._browser.find_element_safe(
                By.NAME, "GenerarVEP", timeout=5
            )

        if generar_vep_button:
            try:
                generar_vep_button.click()
                success = True
                logger.debug("'GENERAR VEP O QR' button clicked successfully")
            except Exception as e:
                logger.error(f"Failed to click 'GENERAR VEP O QR' button: {e}")
                success = False
            if success:
                logger.debug("'GENERAR VEP O QR' button clicked successfully")

                # Wait for and switch to new window
                time.sleep(0.5)
                if self._browser.switch_to_new_window():
                    current_url = self._browser.get_current_url()
                    logger.debug(
                        f"Successfully switched to new window. URL: {current_url}"
                    )
                    return True
                else:
                    logger.error("Failed to switch to new window")
                    return False
            return success
        else:
            logger.error("'GENERAR VEP O QR' button not found")
            return False

    def close(self):
        """Close the browser session."""
        if self.browser:
            self.browser.close_browser()
