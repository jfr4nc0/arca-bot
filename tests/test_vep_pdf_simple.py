#!/usr/bin/env python3
"""
Simple test for VepPdfGenerator to see how PDFs are generated.
"""

import os
from datetime import datetime

from core.services.vep.vep_pdf_generator import VepPdfGenerator


def test_vep_pdf_generation():
    """Test VepPdfGenerator with all constructor values to see the final PDF."""

    # Create VepPdfGenerator with all values
    generator = VepPdfGenerator(
        nro_vep="12345678901234567890",
        cuit="20-12345678-9",
        periodo="2024-01",
        items_pago=[
            {"descripcion": "Impuesto a las Ganancias", "importe": 15000.50},
            {"descripcion": "Multa por presentación tardía", "importe": 2500.25},
        ],
        organismo_recaudador="ARCA - Buenos Aires",
        tipo_pago="Autoliquidacion",
        concepto=("001", "Impuesto a las Ganancias"),
        subconcepto=("001", "Régimen General"),
        descripcion_reducida="Pago mensual Ganancias",
        fecha_generacion=datetime(2024, 1, 15, 10, 30, 45),
        dias_para_expirar=30,
    )

    # Generate PDF in resources folder
    pdf_filename = "test_vep_sample.pdf"
    generator.create_pdf(pdf_filename)

    # Check if file was created
    if os.path.exists(pdf_filename):
        file_size = os.path.getsize(pdf_filename)
        print(f"✓ PDF generated successfully: {pdf_filename}")
        print(f"✓ File size: {file_size} bytes")
        print(f"✓ Total amount: ${generator.importe_total:,.2f}")
    else:
        print("✗ PDF generation failed")


if __name__ == "__main__":
    test_vep_pdf_generation()
