import locale
from datetime import datetime, timedelta

from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class VepPdfGenerator:
    """
    Genera un Volante Electrónico de Pago (VEP) en PDF similar al
    modelo de AFIP/ARCA, basado en los parámetros extraídos.
    """

    def __init__(
        self,
        nro_vep: str,
        cuit: str,
        periodo: str,
        items_pago: list[dict],
        organismo_recaudador: str,
        tipo_pago: str,
        concepto: tuple[str, str],
        subconcepto: tuple[str, str],
        descripcion_reducida: str,
        fecha_generacion: datetime = None,
        dias_para_expirar: int = 26,
    ):
        # Datos del VEP
        self.nro_vep = nro_vep
        self.cuit = cuit
        self.periodo = periodo
        self.items_pago = items_pago
        self.organismo_recaudador = organismo_recaudador
        self.tipo_pago = tipo_pago
        self.concepto_codigo, self.concepto_desc = concepto
        self.subconcepto_codigo, self.subconcepto_desc = subconcepto
        self.descripcion_reducida = descripcion_reducida

        # Campos calculados
        self.fecha_generacion = fecha_generacion or datetime.now()
        self.fecha_expiracion = self.fecha_generacion + timedelta(
            days=dias_para_expirar
        )
        self.dias_expiracion_str = f"{dias_para_expirar} día/s"
        self.importe_total = sum(item["importe"] for item in self.items_pago)

        # Configuración de estilos
        self.styles = self._setup_styles()

    def _setup_styles(self):
        """Define los ParagraphStyle para el documento."""
        styles = getSampleStyleSheet()

        # ARCA Header - Blue and bold
        styles.add(
            ParagraphStyle(
                name="ArcaHeader",
                fontSize=24,
                alignment=TA_LEFT,
                fontName="Helvetica-Bold",
                textColor=colors.Color(0.1, 0.1, 0.5),  # Dark blue
                spaceAfter=0,
            )
        )

        # VEP Header - Orange and bold
        styles.add(
            ParagraphStyle(
                name="VepHeader",
                fontSize=24,
                alignment=TA_RIGHT,
                fontName="Helvetica-Bold",
                textColor=colors.Color(1, 0.5, 0),  # Orange
                spaceAfter=0,
            )
        )

        # Subtitle for "Volante Electrónico de Pago"
        styles.add(
            ParagraphStyle(
                name="Subtitle",
                fontSize=11,
                alignment=TA_CENTER,
                spaceAfter=10,
                fontName="Helvetica",
            )
        )

        # Warning text in red
        styles.add(
            ParagraphStyle(
                name="Warning",
                fontSize=10,
                alignment=TA_CENTER,
                textColor=colors.red,
                spaceAfter=15,
                fontName="Helvetica",
            )
        )

        # Field labels
        styles.add(
            ParagraphStyle(
                name="FieldTitle",
                fontSize=9,
                fontName="Helvetica-Bold",
                alignment=TA_LEFT,
            )
        )

        # Field values
        styles.add(
            ParagraphStyle(
                name="FieldBody", fontSize=9, fontName="Helvetica", alignment=TA_LEFT
            )
        )

        # Amount headers
        styles.add(
            ParagraphStyle(
                name="AmountHeader",
                fontSize=9,
                fontName="Helvetica",
                alignment=TA_LEFT,
            )
        )

        # Amount values
        styles.add(
            ParagraphStyle(
                name="AmountValue",
                fontSize=9,
                fontName="Helvetica",
                alignment=TA_RIGHT,
            )
        )

        # Total amount label
        styles.add(
            ParagraphStyle(
                name="AmountTotal",
                fontSize=9,
                fontName="Helvetica-Bold",
                alignment=TA_LEFT,
            )
        )

        # Total amount value
        styles.add(
            ParagraphStyle(
                name="AmountTotalValue",
                fontSize=9,
                fontName="Helvetica-Bold",
                alignment=TA_RIGHT,
            )
        )
        return styles

    def _format_currency(self, value: float) -> str:
        """
        Formatea el valor flotante a la moneda en formato ARS ($ 1.080,00).
        """
        try:
            # Intenta usar la localización de Argentina
            locale.setlocale(locale.LC_ALL, "es_AR.UTF-8")
            formatted = locale.format_string("%.2f", value, grouping=True)
        except locale.Error:
            # Fallback manual si la localización falla
            formatted = (
                f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

        return f"${formatted}"

    def _create_horizontal_line(self, width: float = 16 * cm) -> Drawing:
        """Creates a horizontal line for section separation."""
        d = Drawing(width, 0.5 * cm)
        d.add(
            Line(
                0,
                0.25 * cm,
                width,
                0.25 * cm,
                strokeColor=colors.black,
                strokeWidth=0.5,
            )
        )
        return d

    def create_pdf(self, filename: str):
        """
        Método principal para construir y guardar el archivo PDF.
        """
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        story = []

        # --- Header with ARCA and VEP side by side ---
        header_data = [
            [
                Paragraph("ARCA", self.styles["ArcaHeader"]),
                Paragraph("VEP", self.styles["VepHeader"]),
            ]
        ]
        header_table = Table(header_data, colWidths=[8 * cm, 8 * cm])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5 * cm),
                ]
            )
        )
        story.append(header_table)
        story.append(self._create_horizontal_line())

        # Subtitle
        story.append(Paragraph("Volante Electrónico de Pago", self.styles["Subtitle"]))
        story.append(Spacer(1, 0.3 * cm))

        # --- Warning with horizontal line ---
        warning_text = f"Atención: este VEP esta pendiente de pago y expira en {self.dias_expiracion_str}"
        story.append(Paragraph(warning_text, self.styles["Warning"]))
        story.append(self._create_horizontal_line())
        story.append(Spacer(1, 0.3 * cm))

        # --- Main Data Table ---
        data = [
            [
                Paragraph("Nro. VEP:", self.styles["FieldTitle"]),
                Paragraph(self.nro_vep, self.styles["FieldBody"]),
            ],
            [
                Paragraph("Organismo Recaudador:", self.styles["FieldTitle"]),
                Paragraph(self.organismo_recaudador, self.styles["FieldBody"]),
            ],
            [
                Paragraph("Tipo de Pago:", self.styles["FieldTitle"]),
                Paragraph(self.tipo_pago, self.styles["FieldBody"]),
            ],
            [
                Paragraph("Descripción Reducida:", self.styles["FieldTitle"]),
                Paragraph(self.descripcion_reducida, self.styles["FieldBody"]),
            ],
            [
                Paragraph("CUIT:", self.styles["FieldTitle"]),
                Paragraph(self.cuit, self.styles["FieldBody"]),
            ],
            [
                Paragraph("Concepto:", self.styles["FieldTitle"]),
                Paragraph(
                    f"{self.concepto_codigo} {self.concepto_desc}",
                    self.styles["FieldBody"],
                ),
            ],
            [
                Paragraph("Subconcepto:", self.styles["FieldTitle"]),
                Paragraph(
                    f"{self.subconcepto_codigo} {self.subconcepto_desc}",
                    self.styles["FieldBody"],
                ),
            ],
            [
                Paragraph("Período:", self.styles["FieldTitle"]),
                Paragraph(self.periodo, self.styles["FieldBody"]),
            ],
        ]

        data_table = Table(data, colWidths=[4.5 * cm, 11.5 * cm])
        data_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(data_table)
        story.append(Spacer(1, 0.3 * cm))

        # --- Date Table ---
        date_data = [
            [
                Paragraph("Fecha Generación:", self.styles["FieldTitle"]),
                Paragraph(
                    self.fecha_generacion.strftime("%Y-%m-%d Hora: %H:%M:%S"),
                    self.styles["FieldBody"],
                ),
            ],
            [
                Paragraph("Día de Expiración:", self.styles["FieldTitle"]),
                Paragraph(
                    self.fecha_expiracion.strftime("%Y-%m-%d"), self.styles["FieldBody"]
                ),
            ],
        ]

        date_table = Table(date_data, colWidths=[4.5 * cm, 11.5 * cm])
        date_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(date_table)
        story.append(Spacer(1, 0.5 * cm))

        # --- Amount Table ---
        amount_data = []

        # Total row
        amount_data.append(
            [
                Paragraph("Importe total a pagar", self.styles["AmountTotal"]),
                Paragraph(
                    self._format_currency(self.importe_total),
                    self.styles["AmountTotalValue"],
                ),
            ]
        )

        amount_table = Table(amount_data, colWidths=[12 * cm, 4 * cm])
        amount_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(amount_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(self._create_horizontal_line())

        # Footer
        story.append(Spacer(1, 1 * cm))
        footer_text = "VEP Generated by 'ArcaAutoVep'"
        footer_style = ParagraphStyle(
            name="Footer",
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey,
            fontName="Helvetica-Oblique",
        )
        story.append(Paragraph(footer_text, footer_style))

        # Construir el PDF
        doc.build(story)
        print(f"PDF generado exitosamente: '{filename}'")
