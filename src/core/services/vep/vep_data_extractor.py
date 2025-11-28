"""
VEP Data Extractor Service - Extracts VEP data from files and web pages.

This service extracts VEP data from:
1. Generated VEP .txt files (DDJJ workflow)
2. Web page DOM elements (CCMA workflow)
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from selenium.webdriver.common.by import By

from core.models.vep_data import VEPData


class VEPDataExtractor:
    """
    VEP Data Extractor Service.

    Extracts VEP data from various sources for PDF generation.
    """

    def __init__(self, shared_resources: Optional[Dict[str, Any]] = None):
        """Initialize VEP data extractor.

        Args:
            shared_resources: Dictionary containing workflow data (periods, calculation date, etc.)
        """
        self.shared_resources = shared_resources or {}

    def extract_from_vep_file(self, vep_file_path: str) -> List[VEPData]:
        """
        Extract VEP data from a generated VEP .txt file.

        Args:
            vep_file_path: Path to the VEP .txt file

        Returns:
            List of VEPData entries extracted from the file
        """
        try:
            logger.info(f"Extracting VEP data from file: {vep_file_path}")

            file_path = Path(vep_file_path)
            if not file_path.exists():
                logger.error(f"VEP file not found: {vep_file_path}")
                return []

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                logger.error(f"VEP file is empty: {vep_file_path}")
                return []

            # Parse VEP file content
            vep_entries = self._parse_vep_file_content(content)

            logger.info(f"Extracted {len(vep_entries)} VEP entries from file")
            return vep_entries

        except Exception as e:
            logger.error(f"Error extracting VEP data from file {vep_file_path}: {e}")
            return []

    def extract_from_web_page(
        self, browser_manager, payment_method: str = "qr"
    ) -> Optional[VEPData]:
        """
        Extract VEP data from the current web page.

        Args:
            browser_manager: Browser manager instance
            payment_method: Selected payment method for context

        Returns:
            VEPData instance with extracted data, or None if extraction failed
        """
        try:
            logger.info("Extracting VEP data from web page")

            # Extract VEP data from web page elements
            vep_data = self._extract_vep_from_dom(browser_manager)

            if vep_data:
                logger.info("Successfully extracted VEP data from web page")
                return vep_data
            else:
                logger.error("Failed to extract VEP data from web page")
                return None

        except Exception as e:
            logger.error(f"Error extracting VEP data from web page: {e}")
            return None

    def _parse_vep_file_content(self, content: str) -> List[VEPData]:
        """
        Parse VEP file content and extract VEP entries.

        Format: 02<VEP fechaExpiracion="..." ... ><Obligacion ... /></VEP>

        Args:
            content: Raw VEP file content

        Returns:
            List of VEPData entries
        """
        vep_entries = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()

            # Skip header lines (start with "01")
            if line.startswith("01"):
                continue

            # Process VEP lines (start with "02")
            if line.startswith("02"):
                vep_data = self._parse_vep_line(line)
                if vep_data:
                    vep_entries.append(vep_data)

        return vep_entries

    def _parse_vep_line(self, line: str) -> Optional[VEPData]:
        """
        Parse a single VEP line and extract data.

        Args:
            line: VEP line content

        Returns:
            VEPData instance or None if parsing failed
        """
        try:
            # Remove "02" prefix
            xml_content = line[2:]

            # Extract VEP attributes using regex
            vep_data = {}

            # Extract main VEP attributes
            patterns = {
                "fecha_expiracion": r'fechaExpiracion="([^"]*)"',
                "nro_formulario": r'nroFormulario="([^"]*)"',
                "cod_tipo_pago": r'codTipoPago="([^"]*)"',
                "cuit": r'contribuyenteCUIT="([^"]*)"',
                "concepto": r'concepto="([^"]*)"',
                "sub_concepto": r'subConcepto="([^"]*)"',
                "periodo_fiscal": r'periodoFiscal="([^"]*)"',
                "importe": r'importe="([^"]*)"',
            }

            for field, pattern in patterns.items():
                match = re.search(pattern, xml_content)
                if match:
                    value = match.group(1)
                    if field == "importe":
                        vep_data[field] = float(value)
                    else:
                        vep_data[field] = value

            # Extract impuesto from Obligacion tag
            impuesto_match = re.search(r'<Obligacion impuesto="([^"]*)"', xml_content)
            if impuesto_match:
                vep_data["impuesto"] = impuesto_match.group(1)

            # Validate required fields
            required_fields = [
                "fecha_expiracion",
                "nro_formulario",
                "cod_tipo_pago",
                "cuit",
                "concepto",
                "sub_concepto",
                "periodo_fiscal",
                "importe",
                "impuesto",
            ]

            if all(field in vep_data for field in required_fields):
                return VEPData(**vep_data)
            else:
                missing = [f for f in required_fields if f not in vep_data]
                logger.warning(f"Missing required fields in VEP line: {missing}")
                return None

        except Exception as e:
            logger.error(f"Error parsing VEP line: {e}")
            return None

    def _extract_vep_from_dom(self, browser_manager) -> Optional[VEPData]:
        """
        Extract VEP data from DOM elements on the current page.

        Args:
            browser_manager: Browser manager instance

        Returns:
            VEPData instance or None if extraction failed
        """
        try:
            # Extract VEP data using specific element IDs for CCMA
            vep_data = {}

            # Extract VEP number from element with ID containing "td-nroVEP"
            try:
                vep_element = browser_manager.find_element_safe(
                    By.XPATH, "//*[contains(@id, 'td-nroVEP')]", timeout=10
                )
                if vep_element and vep_element.text.strip():
                    vep_text = vep_element.text.strip()
                    # Extract numeric VEP number
                    vep_match = re.search(r"\d+", vep_text)
                    if vep_match:
                        vep_data["nro_vep"] = vep_match.group()
                        logger.info(f"Extracted VEP number: {vep_data['nro_vep']}")
            except Exception as e:
                logger.warning(
                    f"Could not extract VEP number from element containing 'td-nroVEP': {e}"
                )

            # Extract description from element with ID containing "td-pagoDesc"
            try:
                desc_element = browser_manager.find_element_safe(
                    By.XPATH, "//*[contains(@id, 'td-pagoDesc')]", timeout=5
                )
                if desc_element and desc_element.text.strip():
                    vep_data["descripcion"] = desc_element.text.strip()
                    logger.info(f"Extracted description: {vep_data['descripcion']}")
            except Exception as e:
                logger.warning(
                    f"Could not extract description from element containing 'td-pagoDesc': {e}"
                )

            # Extract amount from element with ID containing "td-importe"
            try:
                amount_element = browser_manager.find_element_safe(
                    By.XPATH, "//*[contains(@id, 'td-importe')]", timeout=5
                )
                if amount_element and amount_element.text.strip():
                    amount_text = amount_element.text.strip()
                    # Extract numeric amount (handle Argentine format: $ 255.404,12)
                    # Pattern matches: optional $, spaces, digits with . as thousands separator and , as decimal separator
                    amount_match = re.search(
                        r"[\$]?\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)",
                        amount_text,
                    )
                    if amount_match:
                        amount_str = amount_match.group(1)
                        # Convert Argentine format to standard float format
                        # Replace thousands separator (.) with empty string
                        amount_str = amount_str.replace(".", "")
                        # Replace decimal separator (,) with dot
                        amount_str = amount_str.replace(",", ".")
                        try:
                            vep_data["importe"] = float(amount_str)
                            logger.info(
                                f"Extracted amount: {vep_data['importe']} from text: {amount_text}"
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Could not parse amount '{amount_str}' from text '{amount_text}': {e}"
                            )
            except Exception as e:
                logger.warning(
                    f"Could not extract amount from element containing 'td-importe': {e}"
                )

            # Get period and calculation data from shared_resources
            debt_calculation = self.shared_resources.get("debt_calculation", {})

            # Extract period information from shared_resources
            periodo_desde = debt_calculation.get("period_from")
            periodo_hasta = debt_calculation.get("period_to")
            fecha_calculo = debt_calculation.get("calculation_date")
            fecha_expiracion = self.shared_resources.get("expiration_date", "")

            if periodo_desde:
                vep_data["periodo_desde"] = periodo_desde
                logger.info(f"Extracted period from: {periodo_desde}")
            if periodo_hasta:
                vep_data["periodo_hasta"] = periodo_hasta
                logger.info(f"Extracted period to: {periodo_hasta}")
            if fecha_calculo:
                vep_data["fecha_calculo"] = fecha_calculo
                logger.info(f"Extracted calculation date: {fecha_calculo}")

            # Extract CUIT from existing workflow context (if available)
            cuit = self.shared_resources.get("cuit", "00000000000")
            vep_data["cuit"] = cuit
            logger.info(f"Using CUIT: {cuit}")

            # Set default values for required fields if not found
            current_date = datetime.now()

            # Create VEPData with extracted or default values
            try:
                return VEPData(
                    fecha_expiracion=fecha_expiracion,
                    nro_formulario=vep_data.get("nro_vep", "1571"),
                    cod_tipo_pago="33",
                    cuit=vep_data.get("cuit", "00000000000"),
                    concepto="19",
                    sub_concepto="OBLIGACION MENSUAL/ANUAL",
                    periodo_fiscal=current_date.strftime("%Y%m"),
                    importe=vep_data.get("importe", 0.0),
                    impuesto="24",
                    periodo_desde=vep_data.get("periodo_desde"),
                    periodo_hasta=vep_data.get("periodo_hasta"),
                    fecha_calculo=vep_data.get("fecha_calculo"),
                    descripcion=vep_data.get("descripcion"),
                )
            except Exception as e:
                logger.error(f"Error creating VEPData from extracted data: {e}")
                return None

        except Exception as e:
            logger.error(f"Error extracting VEP data from DOM: {e}")
            return None
