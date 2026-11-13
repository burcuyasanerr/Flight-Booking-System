"""
Flight Ticket Purchasing System - PDF Generator
ReportLab kullanarak profesyonel, modern ve güvenli Elektronik Uçuş Bileti / Biniş Kartı üretir.
"""

from decimal import Decimal
import io
import os
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Union
from xml.sax.saxutils import escape as xml_escape

import qrcode
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ticket_pdf.models import FlightTicket, TicketStatus, tr_upper


# --- FONT YAPILANDIRMASI (TÜRKÇE KARAKTER VE ÇAPRAZ PLATFORM DESTEĞİ) ---
def _setup_fonts() -> tuple[str, str]:
    """
    Madde 22: Windows, macOS ve Linux font yollarını arayarak
    Türkçe karakterleri kusursuz görüntüleyecek fontları ReportLab sistemine kaydeder.
    """
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"

    font_candidates = [
        # Windows
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        # macOS
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    for reg_path, bld_path in font_candidates:
        if os.path.exists(reg_path) and os.path.exists(bld_path):
            try:
                pdfmetrics.registerFont(TTFont("FlightCustomRegular", reg_path))
                pdfmetrics.registerFont(TTFont("FlightCustomBold", bld_path))
                regular_font = "FlightCustomRegular"
                bold_font = "FlightCustomBold"
                break
            except Exception:
                continue

    return regular_font, bold_font


FONT_REGULAR, FONT_BOLD = _setup_fonts()

# --- RENK PALETİ ---
PRIMARY_NAVY = colors.HexColor("#0B192C")      # Kurumsal Koyu Lacivert
SECONDARY_BLUE = colors.HexColor("#1E3E62")    # Vurgu Mavisi
ACCENT_ORANGE = colors.HexColor("#FF6500")     # Havacılık Turuncusu
LIGHT_BG = colors.HexColor("#F8F9FA")          # Açık Gri Kart Arka Planı
BORDER_GRAY = colors.HexColor("#E2E8F0")       # İnce Kenarlık Grisi
TEXT_DARK = colors.HexColor("#1E293B")         # Ana Metin Rengi
TEXT_MUTED = colors.HexColor("#64748B")        # İkincil / Açıklama Grisi
SUCCESS_GREEN = colors.HexColor("#059669")     # Onay Yeşili
DANGER_RED = colors.HexColor("#DC2626")        # İptal / Uyarı Kırmızısı


def _create_route_vector(width: float = 115, height: float = 18) -> Drawing:
    """
    Kalkış ve varış noktaları arasında vektörel uçuş rotası çizgisi çizer.
    """
    d = Drawing(width, height)
    mid_y = height / 2.0
    d.add(Circle(8, mid_y, 3, fillColor=ACCENT_ORANGE, strokeColor=None))
    line = Line(14, mid_y, width - 14, mid_y, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1.5, strokeDashArray=[4, 3])
    d.add(line)
    poly = Polygon(
        [width - 14, mid_y - 4, width - 4, mid_y, width - 14, mid_y + 4],
        fillColor=ACCENT_ORANGE,
        strokeColor=None,
    )
    d.add(poly)
    return d


def _create_qr_image(ticket: FlightTicket, size: int = 140) -> RLImage:
    """
    PNR ve bilet doğrulama verilerini içeren taranabilir QR kod üretir.
    """
    is_cancelled = (ticket.ticket.ticket_status == TicketStatus.CANCELLED)
    status_label = "CANCELLED" if is_cancelled else "CONFIRMED"

    qr_payload = (
        f"FLIGHT-TICKET|PNR:{ticket.ticket.pnr_code}|"
        f"FLIGHT:{ticket.flight.flight_number}|"
        f"PASSENGER:{ticket.passenger.full_name}|"
        f"SEAT:{ticket.ticket.seat_number}|"
        f"STATUS:{status_label}"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(qr_payload)
    qr.make(fit=True)

    fill_c = "#DC2626" if is_cancelled else "#0B192C"
    pil_img = qr.make_image(fill_color=fill_c, back_color="white")
    img_buffer = io.BytesIO()
    pil_img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    return RLImage(img_buffer, width=3.0 * cm, height=3.0 * cm)


def _create_barcode(ticket: FlightTicket) -> Drawing:
    """
    Madde 28: Dönüş tipi Drawing olarak düzeltilmiştir.
    """
    barcode_val = f"{ticket.ticket.pnr_code}{ticket.ticket.seat_number}".replace(" ", "")
    bar_fill = DANGER_RED if ticket.ticket.ticket_status == TicketStatus.CANCELLED else PRIMARY_NAVY
    return createBarcodeDrawing(
        "Code128",
        value=barcode_val,
        width=175,
        height=30,
        humanReadable=False,
        barFillColor=bar_fill,
    )


class TicketPDFBuilder:
    """
    Uçuş bileti PDF dokümanını parçalar halinde inşa eden yapılandırıcı sınıf.
    """

    def __init__(self, ticket: FlightTicket):
        self.ticket = ticket
        self.is_cancelled = (ticket.ticket.ticket_status == TicketStatus.CANCELLED)
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        """Metin stillerini tanımlar."""
        self.style_header_title = ParagraphStyle(
            "HeaderTitle",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=17,
            textColor=colors.white,
        )
        self.style_pnr_box = ParagraphStyle(
            "PNRBox",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=16,
            leading=20,
            alignment=2,  # Sağ
            textColor=ACCENT_ORANGE if not self.is_cancelled else DANGER_RED,
        )
        self.style_label = ParagraphStyle(
            "CardLabel",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9.5,
            textColor=TEXT_MUTED,
        )
        self.style_val_bold = ParagraphStyle(
            "CardValueBold",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=10.5,
            leading=13,
            textColor=TEXT_DARK,
        )
        self.style_val_huge = ParagraphStyle(
            "CardValueHuge",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=24,
            textColor=PRIMARY_NAVY if not self.is_cancelled else DANGER_RED,
        )
        self.style_route_arrow = ParagraphStyle(
            "RouteArrow",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=11,
            alignment=1,  # Orta
            textColor=PRIMARY_NAVY,
        )
        self.style_section_title = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=13,
            textColor=PRIMARY_NAVY if not self.is_cancelled else DANGER_RED,
        )
        self.style_info_text = ParagraphStyle(
            "InfoText",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_DARK,
        )
        self.style_info_text_right = ParagraphStyle(
            "InfoTextRight",
            parent=self.styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=6.5,
            leading=9.5,
            alignment=2,
            textColor=TEXT_MUTED,
        )
        self.style_cancelled_banner = ParagraphStyle(
            "CancelledBanner",
            parent=self.styles["Normal"],
            fontName=FONT_BOLD,
            fontSize=13,
            leading=16,
            alignment=1,  # Orta
            textColor=colors.white,
        )

    def build_header(self) -> Table:
        """Üst başlık ve PNR rozeti bloğu"""
        airline = xml_escape(tr_upper(self.ticket.flight.airline_name))
        pnr = xml_escape(self.ticket.ticket.pnr_code)

        if self.is_cancelled:
            status_text = "DURUM: İPTAL EDİLDİ (CANCELLED)"
            status_color = "#FCA5A5"
        else:
            status_text = "DURUM: ONAYLANDI (CONFIRMED)"
            status_color = "#4ADE80"

        col1 = Paragraph(
            f"<b>{airline}</b><br/>"
            f"<font size=8 color='#E2E8F0'>ELEKTRONİK UÇUŞ BİLETİ & BİNİŞ KARTI / E-TICKET & BOARDING PASS</font>",
            self.style_header_title,
        )
        col2 = Paragraph(
            f"<font size=8 color='#94A3B8'>REZERVASYON (PNR)</font><br/>"
            f"<b>{pnr}</b><br/>"
            f"<font size=7 color='{status_color}'><b>{status_text}</b></font>",
            self.style_pnr_box,
        )

        header_table = Table([[col1, col2]], colWidths=[11.5 * cm, 6.5 * cm])
        header_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ])
        )
        return header_table

    def build_cancelled_banner(self) -> Optional[Table]:
        """Madde 18: İptal edilen bilet için dikkat çekici kırmızı uyarı bandı"""
        if not self.is_cancelled:
            return None

        banner_text = Paragraph(
            "⚠️ DİKKAT: BU BİLET İPTAL EDİLMİŞTİR / THIS TICKET HAS BEEN CANCELLED ⚠️<br/>"
            "<font size=8>Bu seyahat belgesi uçuşa biniş veya geçerli bilet olarak kullanılamaz.</font>",
            self.style_cancelled_banner,
        )
        t = Table([[banner_text]], colWidths=[18.0 * cm])
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), DANGER_RED),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        return t

    def build_boarding_pass_card(self) -> Table:
        """
        Ana Biniş Kartı görsel kartı.
        Madde 5: Tüm metinler xml_escape() ile sarılmıştır.
        Madde 34: Şehir adları kesilmeden satıra sarılır.
        """
        f = self.ticket.flight
        p = self.ticket.passenger
        t = self.ticket.ticket

        dep_time_str = f.departure_datetime.strftime("%H:%M")
        dep_date_str = f.departure_datetime.strftime("%d.%m.%Y")
        arr_time_str = f.arrival_datetime.strftime("%H:%M")
        arr_date_str = f.arrival_datetime.strftime("%d.%m.%Y")
        boarding_time_str = f.boarding_time.strftime("%H:%M") if f.boarding_time else "--:--"

        gate_display = xml_escape(f.gate or "Havalimanında duyurulacaktır")
        terminal_display = xml_escape(f.terminal or "--")
        aircraft_display = xml_escape(f.aircraft_type or "Standart Uçak")

        route_vector = _create_route_vector(width=115, height=18)
        mid_column = [
            Paragraph(f"<font size=7.5 color='#64748B'>UÇUŞ:</font> <b>{xml_escape(f.flight_number)}</b>", self.style_route_arrow),
            Spacer(1, 1 * mm),
            route_vector,
            Spacer(1, 1 * mm),
            Paragraph(f"<font size=7 color='#0B192C'>Süre: <b>{f.duration_formatted}</b></font>", self.style_route_arrow),
        ]

        route_table_data = [
            [
                Paragraph(f"<font size=7 color='#64748B'>KALKIŞ / ORIGIN</font><br/>"
                          f"<b>{xml_escape(f.origin_code)}</b><br/>"
                          f"<font size=8><b>{dep_time_str}</b></font><br/>"
                          f"<font size=7 color='#64748B'>{dep_date_str}</font><br/>"
                          f"<font size=6.5 color='#475569'>{xml_escape(f.origin_name)}</font>", self.style_val_huge),
                mid_column,
                Paragraph(f"<font size=7 color='#64748B'>VARIŞ / DESTINATION</font><br/>"
                          f"<b>{xml_escape(f.destination_code)}</b><br/>"
                          f"<font size=8><b>{arr_time_str}</b></font><br/>"
                          f"<font size=7 color='#64748B'>{arr_date_str}</font><br/>"
                          f"<font size=6.5 color='#475569'>{xml_escape(f.destination_name)}</font>", self.style_val_huge),
            ]
        ]
        route_table = Table(route_table_data, colWidths=[3.7 * cm, 4.4 * cm, 3.7 * cm])
        route_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )

        row1_data = [
            [
                Paragraph("YOLCU ADI SOYADI / PASSENGER", self.style_label),
                Paragraph("KOLTUK / SEAT", self.style_label),
                Paragraph("KAPI / GATE", self.style_label),
                Paragraph("BİNİŞ SAATİ / BOARDING", self.style_label),
            ],
            [
                Paragraph(f"<b>{xml_escape(p.full_name)}</b>", self.style_val_bold),
                Paragraph(f"<b>{xml_escape(t.seat_number)}</b>", self.style_val_bold),
                Paragraph(f"<b>{gate_display}</b>", self.style_val_bold),
                Paragraph(f"<b>{boarding_time_str}</b>", self.style_val_bold),
            ],
        ]
        row1_table = Table(row1_data, colWidths=[4.7 * cm, 2.0 * cm, 3.1 * cm, 2.0 * cm])
        row1_table.setStyle(
            TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        row2_data = [
            [
                Paragraph("KABİN SINIFI / CLASS", self.style_label),
                Paragraph("BAGAJ HAKKI / BAGGAGE", self.style_label),
                Paragraph("TERMINAL", self.style_label),
                Paragraph("DURUM / STATUS", self.style_label),
            ],
            [
                Paragraph(f"<b>{t.cabin_class.display_name}</b>", self.style_val_bold),
                Paragraph(f"<b>{xml_escape(t.baggage_allowance)}</b>", self.style_val_bold),
                Paragraph(f"<b>{terminal_display}</b>", self.style_val_bold),
                Paragraph(f"<font color='{'#DC2626' if self.is_cancelled else '#059669'}'><b>{t.ticket_status.display_name}</b></font>", self.style_val_bold),
            ],
        ]
        row2_table = Table(row2_data, colWidths=[2.8 * cm, 4.3 * cm, 2.0 * cm, 2.7 * cm])
        row2_table.setStyle(
            TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LEFTPADDING", (0, 0), (-1, -1), 1),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        left_content = [
            route_table,
            Spacer(1, 3 * mm),
            HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=2, spaceAfter=4),
            row1_table,
            Spacer(1, 2 * mm),
            row2_table,
        ]

        # --- SAĞ TARAF: BİNİŞ KARTI KUPONU (STUB) & QR KOD & BARKOD ---
        qr_flowable = _create_qr_image(self.ticket)
        barcode_flowable = _create_barcode(self.ticket)

        stub_data = [
            [Paragraph("<font size=7 color='#64748B'>KUPON / PASSENGER STUB</font>", self.style_label)],
            [Paragraph(f"<b>{xml_escape(p.stub_name)}</b>", self.style_val_bold)],
            [Paragraph(f"<font size=7 color='#64748B'>UÇUŞ:</font> <b>{xml_escape(f.flight_number)}</b> &nbsp;&nbsp; "
                       f"<font size=7 color='#64748B'>PNR:</font> <b>{xml_escape(t.pnr_code)}</b>", self.style_info_text)],
            [Paragraph(f"<b>{xml_escape(f.origin_code)} &gt; {xml_escape(f.destination_code)}</b>", self.style_val_bold)],
            [Paragraph(f"<font size=7 color='#64748B'>KOLTUK:</font> <b>{xml_escape(t.seat_number)}</b>", self.style_info_text)],
            [qr_flowable],
            [barcode_flowable],
        ]
        stub_table = Table(stub_data, colWidths=[5.4 * cm])
        stub_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ])
        )

        main_card_table = Table(
            [[left_content, stub_table]],
            colWidths=[12.2 * cm, 5.8 * cm],
        )
        main_card_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GRAY),
                ("LINEBEFORE", (1, 0), (1, -1), 1, colors.HexColor("#CBD5E1"), 0, (2, 2)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return main_card_table

    def build_financial_table(self) -> Table:
        """
        Madde 18 ve Madde 21:
        - Gerçek veritabanı verisi gösterilir (uydurma %82/%18 vergi bölünmez).
        - İptal edilen bilette 'ÖDENDİ' ibaresi yer almaz.
        """
        t = self.ticket.ticket
        currency = xml_escape(t.currency)
        total_str = f"{t.total_price:,.2f} {currency}"
        booking_date_str = t.booking_date.strftime("%d.%m.%Y %H:%M")

        if self.is_cancelled:
            payment_status_text = "<font color='#DC2626'><b>İADE / İPTAL EDİLDİ</b></font>"
            note_text = "Bilet iptal edildiği için geçersizdir"
            header_amount_label = "<b>İPTAL EDİLEN TUTAR</b>"
        else:
            payment_status_text = "<font color='#059669'><b>ÖDENDİ</b></font>"
            note_text = "KDV ve tüm yasal harçlar dahildir"
            header_amount_label = "<b>TOPLAM TUTAR</b>"

        data = [
            [
                Paragraph("<b>ÜCRET KALEMİ / FARE DESCRIPTION</b>", self.style_section_title),
                Paragraph(header_amount_label, self.style_section_title),
                Paragraph("<b>ÖDEME BİLGİSİ / DETAILS</b>", self.style_section_title),
                Paragraph("<b>DURUM / NOT</b>", self.style_section_title),
            ],
            [
                Paragraph("Uçuş Bilet Bedeli", self.style_info_text),
                Paragraph(f"<b>{total_str}</b>", self.style_val_bold),
                Paragraph(f"Ödeme Yöntemi: <b>{xml_escape(t.payment_method)}</b>", self.style_info_text),
                Paragraph(note_text, self.style_info_text),
            ],
            [
                Paragraph("İşlem Tarihi", self.style_info_text),
                Paragraph(booking_date_str, self.style_info_text),
                Paragraph(f"Tahsilat Durumu: {payment_status_text}", self.style_info_text),
                Paragraph(f"Bilet Durumu: <b>{t.ticket_status.display_name}</b>", self.style_info_text),
            ],
        ]

        fin_table = Table(data, colWidths=[5.5 * cm, 3.5 * cm, 5.0 * cm, 4.0 * cm])
        fin_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ("LINEBELOW", (0, -1), (-1, -1), 1, PRIMARY_NAVY if not self.is_cancelled else DANGER_RED),
            ])
        )
        return fin_table

    def build_notices_section(self) -> Table:
        """Yolcu için kurallar paneli"""
        if self.is_cancelled:
            notices = [
                "• <b>İptal Bildirimi:</b> Bu rezervasyon iptal edilmiş olup havalimanında uçuşa kabul sağlanamaz.",
                "• <b>İade Süreci:</b> İade tutarları bankanızın prosedürüne bağlı olarak 3-7 iş günü içerisinde ödeme yapılan karta aktarılır.",
                "• <b>Destek:</b> İptal işlemiyle ilgili sorularınız için müşteri destek birimimizle iletişime geçebilirsiniz.",
            ]
        else:
            notices = [
                "• <b>Havalimanı Varış Zamanı:</b> İç hat uçuşlarında kalkıştan en az 2 saat, dış hat uçuşlarında en az 3 saat önce havalimanında bulunmanız önerilir.",
                "• <b>Biniş Kapısı:</b> Uçağa biniş kapıları (Gate) uçuş kalkış saatinden <b>20 dakika önce</b> kesin olarak kapatılır.",
                "• <b>Kimlik İbrazı:</b> Uçuşa kabul için fotoğraflı resmi T.C. Kimlik Kartı, Ehliyet veya Pasaport aslı ibraz edilmelidir.",
                "• <b>Bagaj Güvenliği:</b> El bagajınızda 100 ml üzeri sıvı, yanıcı ve kesici alet taşınması yasaktır.",
            ]

        title = "İPTAL BİLGİLENDİRMESİ" if self.is_cancelled else "ÖNEMLİ YOLCU BİLGİLENDİRMELERİ & KURALLAR"
        cell_content = [Paragraph(f"<b>{title}</b>", self.style_section_title)]
        for item in notices:
            cell_content.append(Spacer(1, 1.2 * mm))
            cell_content.append(Paragraph(item, self.style_info_text))

        bg_color = colors.HexColor("#FEF2F2") if self.is_cancelled else colors.HexColor("#FFFBEB")
        border_c = colors.HexColor("#FCA5A5") if self.is_cancelled else colors.HexColor("#FDE68A")

        table = Table([[cell_content]], colWidths=[18.0 * cm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 0.5, border_c),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return table

    def build_footer(self) -> Table:
        """
        Madde 23: Gerçeği yansıtmayan ifadeler ve sahte telefon kaldırıldı.
        """
        issue_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        doc_no = f"DOC-{self.ticket.ticket.pnr_code}-{self.ticket.ticket.seat_number}"

        left_text = Paragraph(
            f"<font size=6.5 color='#64748B'>"
            f"Düzenlenme Zamanı: {issue_time} | Belge No: {doc_no}<br/>"
            f"İletişim Destek: destek@flightbooking.com | Web: www.flightbooker-team19.com"
            f"</font>",
            self.style_info_text,
        )
        right_text = Paragraph(
            "Elektronik Seyahat Belgesi & Biniş Kartı Bilgi Fişi<br/>Sayfa 1 / 1",
            self.style_info_text_right,
        )

        footer_table = Table([[left_text, right_text]], colWidths=[12.0 * cm, 6.0 * cm])
        footer_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ])
        )
        return footer_table

    def generate(self, target: Union[str, Path, BinaryIO]):
        """PDF belgesini derler ve hedefe yazar."""
        doc = SimpleDocTemplate(
            target,
            pagesize=A4,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm,
        )

        story = [self.build_header()]

        cancelled_banner = self.build_cancelled_banner()
        if cancelled_banner:
            story.append(Spacer(1, 2 * mm))
            story.append(cancelled_banner)

        story.extend([
            Spacer(1, 4 * mm),
            self.build_boarding_pass_card(),
            Spacer(1, 5 * mm),
            Paragraph("<b>ÜCRET VE ÖDEME AYRINTILARI</b>", self.style_section_title),
            Spacer(1, 2 * mm),
            self.build_financial_table(),
            Spacer(1, 5 * mm),
            self.build_notices_section(),
            Spacer(1, 4 * mm),
            HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=2, spaceAfter=2),
            self.build_footer(),
        ])

        doc.build(story)


def generate_ticket_pdf(ticket: FlightTicket, output_path: Union[str, Path]) -> str:
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    builder = TicketPDFBuilder(ticket)
    builder.generate(str(path))
    return str(path)


def generate_ticket_pdf_bytes(ticket: FlightTicket) -> bytes:
    buffer = io.BytesIO()
    builder = TicketPDFBuilder(ticket)
    builder.generate(buffer)
    return buffer.getvalue()
