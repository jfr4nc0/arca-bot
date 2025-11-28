"""
VEP File Generator Service - Generates VEP files based on specifications.

This service follows SOLID principles:
- Single Responsibility: Only handles VEP file generation
- Open/Closed: Designed to be extensible for different VEP formats
- Dependency Inversion: Depends on file handler abstraction
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from core.models.vep_data import VEPData
from core.observability import record_file_operation, record_vep_operation
from core.services.system.file_handler import FileHandler


class VEPFileGenerator:
    """
    VEP File Generator Service.

    This service generates VEP files based on the specifications from
    @docs/Instructivo-generacion-veps.pdf and saves them to resources/vep_files.
    """

    def __init__(self):
        """Initialize VEP file generator with file handler dependency."""
        self._file_handler = FileHandler()
        self._vep_directory = Path("resources/vep_files")

    def generate_vep_file(self, vep_entries: List[VEPData]) -> Optional[str]:
        """
        Generate a VEP file with multiple entries (one row per entry).

        Args:
            vep_entries: List of VEPData entries

        Returns:
            Path to generated VEP file, or None if generation failed
        """
        try:
            logger.info("Starting VEP file generation")

            # Validate entries list
            if not vep_entries or not isinstance(vep_entries, list):
                logger.error("Invalid VEP entries list provided")
                return None

            # Format VEP content with multiple entries (one row per entry)
            vep_content = self._format_vep_content(vep_entries)
            if not vep_content:
                logger.error("Failed to format VEP content")
                return None

            # Generate filename with timestamp
            filename = self._generate_filename(vep_entries)
            filepath = self._vep_directory / filename

            # Save VEP file
            if self._file_handler.save_text_file(vep_content, filepath):
                # Record VEP generation success metric
                record_vep_operation("generation", "success")
                # Record file operation success metric
                record_file_operation("vep_file_save", "success")
                logger.info(f"VEP file generated successfully: {filepath}")
                return str(filepath)
            else:
                # Record VEP generation failure metric
                record_vep_operation("generation", "failed")
                # Record file operation failure metric
                record_file_operation("vep_file_save", "failed")
                logger.error(f"Failed to save VEP file: {filepath}")
                return None

        except Exception as e:
            # Record VEP generation exception metric
            record_vep_operation("generation", "failed")
            logger.error(f"Error generating VEP file: {e}")
            return None

    def generate_multiple_vep_files(
        self, vep_data_list: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate multiple VEP files from a list of VEP data.

        Args:
            vep_data_list: List of dictionaries containing VEP data

        Returns:
            List of paths to generated VEP files
        """
        generated_files = []

        for i, vep_data in enumerate(vep_data_list):
            try:
                logger.info(f"Generating VEP file {i+1}/{len(vep_data_list)}")
                filepath = self.generate_vep_file(vep_data)
                if filepath:
                    generated_files.append(filepath)
            except Exception as e:
                logger.error(f"Error generating VEP file {i+1}: {e}")
                continue

        logger.info(
            f"Generated {len(generated_files)} out of {len(vep_data_list)} VEP files"
        )
        return generated_files

    def _format_vep_content(self, vep_entries: List[VEPData]) -> Optional[str]:
        """
        Format VEP content with header and multiple entries (one row per entry).

        Args:
            vep_entries: List of VEPData entries

        Returns:
            Formatted VEP content as string, or None if formatting failed
        """
        try:
            lines = []

            # Generate header: 01{cuit}2000100100003003{size of vep rows, in 4 digits}
            if vep_entries:
                first_cuit = vep_entries[0].cuit
                num_rows = len(vep_entries) + 1
                header = f"01{first_cuit}2000100100003003{num_rows:04d}"
                lines.append(header)

            # Generate one row per VEP entry in the specified format
            for entry in vep_entries:
                # Format: 02<VEP fechaExpiracion="..." ... ><Obligacion ... /></VEP>
                vep_line = (
                    f'02<VEP fechaExpiracion="{entry.fecha_expiracion}" '
                    f'nroFormulario="{entry.nro_formulario}" '
                    f'codTipoPago="{entry.cod_tipo_pago}" '
                    f'contribuyenteCUIT="{entry.cuit}" '
                    f'concepto="{entry.concepto}" '
                    f'subConcepto="{entry.sub_concepto}" '
                    f'periodoFiscal="{entry.periodo_fiscal}" '
                    f'importe="{entry.importe:.2f}" '
                    f'><Obligacion impuesto="{entry.impuesto}" '
                    f'importe="{entry.importe:.2f}" /></VEP>'
                )

                lines.append(vep_line)

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error formatting VEP content: {e}")
            return None

    def _generate_filename(self, vep_entries: List[VEPData]) -> str:
        """
        Generate filename for VEP file.

        Args:
            vep_entries: List of VEPData entries

        Returns:
            Generated filename in format F20001.cuit.{cuit}.fecha.{yymmdd}.txt
        """
        # Use first entry's CUIT for filename
        first_cuit = vep_entries[0].cuit if vep_entries else "00000000000"

        # Generate date in YYYYMMDD format
        date_str = datetime.now().strftime("%Y%m%d")

        return f"F20001.cuit.{first_cuit}.fecha.{date_str}.txt"

    def get_generated_vep_files(self) -> List[str]:
        """
        Get list of all generated VEP files.

        Returns:
            List of paths to VEP files
        """
        try:
            if not self._vep_directory.exists():
                return []

            vep_files = list(self._vep_directory.glob("*.txt"))
            return [str(f) for f in vep_files]
        except Exception as e:
            logger.error(f"Error getting VEP files: {e}")
            return []
